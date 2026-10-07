from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sqlite3

app = FastAPI(
    title="Servicio de Reseñas",
    description="Calificaciones desacopladas del núcleo.",
    version="1.0.0",
)
DB = "resenas.db"


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE IF NOT EXISTS resenas(id INTEGER PRIMARY KEY AUTOINCREMENT,libro_id INTEGER,usuario_id INTEGER,calificacion INTEGER,comentario TEXT)"
    )
    c.commit()
    return c


class Review(BaseModel):
    libro_id: int = Field(..., description="ID del libro reseñado", examples=[1])
    usuario_id: int = Field(..., description="ID del usuario que reseña", examples=[1])
    calificacion: int = Field(
        ..., ge=1, le=5, description="Calificación de 1 a 5 estrellas", examples=[5]
    )
    comentario: str = Field(
        ..., description="Comentario de la reseña", examples=["Excelente"]
    )


@app.post("/resenas", status_code=201, summary="Crear reseña", tags=["Reseñas"])
def create(x: Review):
    c = db()
    cur = c.execute(
        "INSERT INTO resenas(libro_id,usuario_id,calificacion,comentario) VALUES(?,?,?,?)",
        tuple(x.model_dump().values()),
    )
    c.commit()
    return dict(
        c.execute("SELECT * FROM resenas WHERE id=?", (cur.lastrowid,)).fetchone()
    )


@app.get(
    "/resenas/libro/{libro_id}", summary="Listar reseñas y promedio", tags=["Reseñas"]
)
def list_reviews(libro_id: int):
    c = db()
    rows = [
        dict(r)
        for r in c.execute(
            "SELECT * FROM resenas WHERE libro_id=?", (libro_id,)
        ).fetchall()
    ]
    return {
        "libro_id": libro_id,
        "promedio": (
            round(sum(r["calificacion"] for r in rows) / len(rows), 2) if rows else 0
        ),
        "resenas": rows,
    }
