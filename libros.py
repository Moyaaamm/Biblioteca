from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import sqlite3

app = FastAPI(
    title="Servicio de Libros",
    description="Catálogo e inventario de ejemplares.",
    version="1.0.0",
)
DB = "libros.db"


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE IF NOT EXISTS libros(id INTEGER PRIMARY KEY AUTOINCREMENT,titulo TEXT NOT NULL,autor TEXT NOT NULL,disponible INTEGER NOT NULL DEFAULT 1,activo INTEGER NOT NULL DEFAULT 1)"
    )
    c.commit()
    return c


class LibroIn(BaseModel):
    titulo: str = Field(
        ..., description="Título del libro", examples=["Cien años de soledad"]
    )
    autor: str = Field(..., description="Autor", examples=["Gabriel García Márquez"])


class LibroPatch(BaseModel):
    titulo: str | None = Field(
        None, description="Nuevo título del libro", examples=["Cien años de soledad"]
    )
    autor: str | None = Field(
        None, description="Nuevo autor del libro", examples=["Gabriel García Márquez"]
    )


class Disp(BaseModel):
    disponible: bool = Field(
        ..., description="Disponibilidad del ejemplar", examples=[True]
    )


@app.post("/libros", status_code=201, summary="Registrar libro", tags=["Libros"])
def create(x: LibroIn):
    c = db()
    cur = c.execute("INSERT INTO libros(titulo,autor) VALUES(?,?)", (x.titulo, x.autor))
    c.commit()
    return dict(
        c.execute("SELECT * FROM libros WHERE id=?", (cur.lastrowid,)).fetchone()
    )


@app.get("/libros", summary="Listar catálogo", tags=["Libros"])
def all():
    return [
        dict(x)
        for x in db()
        .execute("SELECT * FROM libros WHERE activo=1 ORDER BY titulo")
        .fetchall()
    ]


@app.get("/libros/{id}", summary="Consultar libro", tags=["Libros"])
def one(id: int):
    r = db().execute("SELECT * FROM libros WHERE id=? AND activo=1", (id,)).fetchone()
    if not r:
        raise HTTPException(404, "Libro no encontrado")
    return dict(r)


@app.patch("/libros/{id}", summary="Actualizar libro", tags=["Libros"])
def patch(id: int, x: LibroPatch):
    one(id)
    vals = x.model_dump(exclude_none=True)
    if vals:
        db().execute(
            "UPDATE libros SET " + ",".join(f"{k}=?" for k in vals) + " WHERE id=?",
            (*vals.values(), id),
        )
        db().commit()
    return one(id)


@app.patch(
    "/libros/{id}/disponibilidad", summary="Cambiar disponibilidad", tags=["Libros"]
)
def availability(id: int, x: Disp):
    one(id)
    c = db()
    c.execute("UPDATE libros SET disponible=? WHERE id=?", (int(x.disponible), id))
    c.commit()
    return one(id)


@app.delete("/libros/{id}", status_code=204, summary="Inactivar libro", tags=["Libros"])
def delete(id: int):
    r = one(id)
    if not r["disponible"]:
        raise HTTPException(400, "No se puede inactivar un libro prestado")
    c = db()
    c.execute("UPDATE libros SET activo=0 WHERE id=?", (id,))
    c.commit()
