from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sqlite3, httpx, asyncio
from datetime import datetime

app = FastAPI(
    title="Servicio de Préstamos - Orquestador",
    description="Orquesta validaciones distribuidas y préstamos.",
    version="1.0.0",
)
DB = "prestamos.db"
U = "http://127.0.0.1:8002"
L = "http://127.0.0.1:8001"
M = "http://127.0.0.1:8005"
N = "http://127.0.0.1:8004"


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE IF NOT EXISTS prestamos(id INTEGER PRIMARY KEY AUTOINCREMENT,usuario_id INTEGER,libro_id INTEGER,fecha TEXT,activo INTEGER DEFAULT 1)"
    )
    c.commit()
    return c


class Loan(BaseModel):
    usuario_id: int = Field(
        ..., description="ID del usuario que solicita el préstamo", examples=[1]
    )
    libro_id: int = Field(..., description="ID del libro a prestar", examples=[1])


async def call(method, url, **kw):
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            return await c.request(method, url, **kw)
    except httpx.HTTPError:
        raise HTTPException(503, "Falla de comunicación inter-servicio")


@app.post(
    "/prestamos",
    status_code=201,
    summary="Crear préstamo orquestado",
    tags=["Préstamos"],
)
async def create(x: Loan):
    u = await call("GET", f"{U}/usuarios/{x.usuario_id}")
    if u.status_code == 404:
        raise HTTPException(404, "Usuario no encontrado")
    if u.status_code >= 500:
        raise HTTPException(503, "Servicio de usuarios no disponible")
    s = await call("GET", f"{M}/sanciones/usuario/{x.usuario_id}/estatus")
    if s.status_code >= 500:
        raise HTTPException(503, "Servicio de multas no disponible")
    if s.json().get("bloqueado"):
        raise HTTPException(400, "Usuario bloqueado por adeudos")
    c = db()
    active = c.execute(
        "SELECT COUNT(*) n FROM prestamos WHERE usuario_id=? AND activo=1",
        (x.usuario_id,),
    ).fetchone()["n"]
    if active >= 3:
        raise HTTPException(400, "El usuario alcanzó el límite de 3 préstamos activos")
    b = await call("GET", f"{L}/libros/{x.libro_id}")
    if b.status_code == 404:
        raise HTTPException(404, "Libro no encontrado")
    if not b.json().get("disponible"):
        raise HTTPException(400, "Libro no disponible")
    lock = await call(
        "PATCH", f"{L}/libros/{x.libro_id}/disponibilidad", json={"disponible": False}
    )
    if lock.status_code >= 400:
        raise HTTPException(400, "No se pudo reservar el libro")
    cur = c.execute(
        "INSERT INTO prestamos(usuario_id,libro_id,fecha) VALUES(?,?,?)",
        (x.usuario_id, x.libro_id, datetime.now().isoformat()),
    )
    c.commit()
    loan = dict(
        c.execute("SELECT * FROM prestamos WHERE id=?", (cur.lastrowid,)).fetchone()
    )
    asyncio.create_task(
        call(
            "POST",
            f"{N}/notificaciones/enviar",
            json={
                "destinatario": u.json()["email"],
                "asunto": "Préstamo confirmado",
                "mensaje": f"Libro {x.libro_id} prestado",
            },
        )
    )
    return loan


@app.patch("/prestamos/{id}/devolver", summary="Devolver préstamo", tags=["Préstamos"])
async def return_loan(id: int):
    c = db()
    r = c.execute("SELECT * FROM prestamos WHERE id=? AND activo=1", (id,)).fetchone()
    if not r:
        raise HTTPException(404, "Préstamo activo no encontrado")
    b = await call(
        "PATCH", f'{L}/libros/{r["libro_id"]}/disponibilidad', json={"disponible": True}
    )
    if b.status_code >= 400:
        raise HTTPException(503, "No se pudo liberar el libro")
    c.execute("UPDATE prestamos SET activo=0 WHERE id=?", (id,))
    c.commit()
    return dict(c.execute("SELECT * FROM prestamos WHERE id=?", (id,)).fetchone())


@app.get("/prestamos", summary="Listar préstamos activos", tags=["Préstamos"])
def all():
    return [
        dict(r)
        for r in db()
        .execute("SELECT * FROM prestamos WHERE activo=1 ORDER BY id")
        .fetchall()
    ]
