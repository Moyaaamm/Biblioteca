from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sqlite3

app = FastAPI(
    title="Servicio de Usuarios",
    description="Perfiles de lectores y validación de emails.",
    version="1.0.0",
)
DB = "usuarios.db"


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY AUTOINCREMENT,nombre TEXT NOT NULL,email TEXT UNIQUE NOT NULL,activo INTEGER DEFAULT 1)"
    )
    c.commit()
    return c


class UserIn(BaseModel):
    nombre: str = Field(
        ..., description="Nombre completo del lector", examples=["Ana López"]
    )
    email: str = Field(
        ...,
        description="Correo electrónico único del lector",
        examples=["ana@example.com"],
    )


class UserPatch(BaseModel):
    nombre: str | None = Field(
        None, description="Nuevo nombre del lector", examples=["Ana López"]
    )
    email: str | None = Field(
        None,
        description="Nuevo correo electrónico (mantiene unicidad)",
        examples=["ana@example.com"],
    )


def get(id):
    r = db().execute("SELECT * FROM usuarios WHERE id=? AND activo=1", (id,)).fetchone()
    if not r:
        raise HTTPException(404, "Usuario no encontrado")
    return dict(r)


@app.post("/usuarios", status_code=201, summary="Registrar usuario", tags=["Usuarios"])
def create(x: UserIn):
    c = db()
    try:
        cur = c.execute(
            "INSERT INTO usuarios(nombre,email) VALUES(?,?)", (x.nombre, x.email)
        )
        c.commit()
        return get(cur.lastrowid)
    except sqlite3.IntegrityError:
        raise HTTPException(400, "El email ya está registrado")


@app.get("/usuarios", summary="Listar usuarios", tags=["Usuarios"])
def all():
    return [
        dict(r)
        for r in db().execute("SELECT * FROM usuarios WHERE activo=1").fetchall()
    ]


@app.get("/usuarios/{id}", summary="Consultar usuario", tags=["Usuarios"])
def one(id: int):
    return get(id)


@app.patch("/usuarios/{id}", summary="Actualizar usuario", tags=["Usuarios"])
def patch(id: int, x: UserPatch):
    get(id)
    vals = x.model_dump(exclude_none=True)
    c = db()
    try:
        if vals:
            c.execute(
                "UPDATE usuarios SET "
                + ",".join(f"{k}=?" for k in vals)
                + " WHERE id=?",
                (*vals.values(), id),
            )
            c.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, "El email ya está registrado")
    return get(id)


@app.delete(
    "/usuarios/{id}", status_code=204, summary="Inactivar usuario", tags=["Usuarios"]
)
def delete(id: int):
    get(id)
    c = db()
    c.execute("UPDATE usuarios SET activo=0 WHERE id=?", (id,))
    c.commit()
