import sqlite3
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

URL_LIBROS = "http://127.0.0.1:8001"
URL_USUARIOS = "http://127.0.0.1:8002"
URL_NOTIFICACIONES = "http://127.0.0.1:8004"
URL_MULTAS = "http://127.0.0.1:8005"

class PrestamoCreate(BaseModel):
    usuario_id: int = Field(..., description="ID del usuario que solicita el préstamo", json_schema_extra={"example": 1})
    libro_id: int = Field(..., description="ID del libro a prestar", json_schema_extra={"example": 1})

def get_db():
    conn = sqlite3.connect("prestamos.db")
    conn.row_factory = sqlite3.Row
    return conn

@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS prestamos (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, libro_id INTEGER, activo BOOLEAN DEFAULT 1)")
    yield

app = FastAPI(
    title="Servicio de Préstamos (Orquestador)", 
    description="Valida reglas cruzadas y orquesta el flujo completo de préstamos y devoluciones",
    version="1.0.0",
    lifespan=lifespan
)

async def enviar_notificacion_async(email: str, mensaje: str):
    async with httpx.AsyncClient() as client:
        await client.post(f"{URL_NOTIFICACIONES}/notificaciones/enviar", json={"destinatario": email, "asunto": "Préstamo Biblioteca", "mensaje": mensaje})

@app.post("/prestamos", status_code=status.HTTP_201_CREATED, tags=["Orquestador de Préstamos"], summary="Ejecuta el algoritmo de orquestación de préstamos", description="Valida usuario, adeudos, cuotas y disponibilidad en un flujo secuencial, luego delega la notificación asíncrona.")
async def crear_prestamo(payload: PrestamoCreate, bg_tasks: BackgroundTasks):
    async with httpx.AsyncClient() as client:
        res_usuario = await client.get(f"{URL_USUARIOS}/usuarios/{payload.usuario_id}")
        if res_usuario.status_code == 404:
            raise HTTPException(status_code=404, detail="Usuario no existe")
        usuario_email = res_usuario.json()["email"]

        res_multas = await client.get(f"{URL_MULTAS}/sanciones/usuario/{payload.usuario_id}/estatus")
        if res_multas.status_code == 200 and res_multas.json().get("bloqueado"):
            raise HTTPException(status_code=400, detail="Usuario bloqueado por multas")

        with get_db() as conn:
            activos = conn.execute("SELECT COUNT(*) FROM prestamos WHERE usuario_id = ? AND activo = 1", (payload.usuario_id,)).fetchone()[0]
            if activos >= 3:
                raise HTTPException(status_code=400, detail="Excede límite de 3 préstamos")

        res_libro = await client.get(f"{URL_LIBROS}/libros/{payload.libro_id}")
        if res_libro.status_code == 404 or not res_libro.json().get("disponible"):
            raise HTTPException(status_code=400, detail="Libro no disponible")

        await client.patch(f"{URL_LIBROS}/libros/{payload.libro_id}/disponibilidad", json={"disponible": False})

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO prestamos (usuario_id, libro_id) VALUES (?, ?)", (payload.usuario_id, payload.libro_id))
        p_id = cursor.lastrowid

    bg_tasks.add_task(enviar_notificacion_async, usuario_email, f"Se te ha prestado exitosamente el libro con ID {payload.libro_id}")

    return {"id": p_id, "status": "Prestamo exitoso"}

@app.patch("/prestamos/{id}/devolver", status_code=status.HTTP_200_OK, tags=["Orquestador de Préstamos"], summary="Registra la devolución de un libro", description="Marca el préstamo como inactivo y libera el libro en el inventario.")
async def devolver(id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM prestamos WHERE id = ?", (id,)).fetchone()
        if not row: raise HTTPException(status_code=404)
        conn.execute("UPDATE prestamos SET activo = 0 WHERE id = ?", (id,))
        libro_id = row["libro_id"]
    
    async with httpx.AsyncClient() as client:
        await client.patch(f"{URL_LIBROS}/libros/{libro_id}/disponibilidad", json={"disponible": True})
    
    return {"mensaje": "Devuelto correctamente"}