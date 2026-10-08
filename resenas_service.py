import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

class ResenaCreate(BaseModel):
    libro_id: int = Field(..., description="ID del libro a evaluar", json_schema_extra={"example": 1})
    usuario_id: int = Field(..., description="ID del usuario que realiza la reseña", json_schema_extra={"example": 1})
    calificacion: int = Field(..., ge=1, le=5, description="Calificación de 1 a 5 estrellas", json_schema_extra={"example": 5})
    comentario: str = Field(..., description="Comentario sobre el libro", json_schema_extra={"example": "Excelente lectura, muy recomendada."})

def get_db():
    conn = sqlite3.connect("resenas.db")
    conn.row_factory = sqlite3.Row
    return conn

@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS resenas (id INTEGER PRIMARY KEY, libro_id INTEGER, usuario_id INTEGER, calificacion INTEGER, comentario TEXT)")
    yield

app = FastAPI(
    title="Servicio de Reseñas", 
    description="Comentarios y calificaciones desacoplados del núcleo",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/resenas", status_code=status.HTTP_201_CREATED, tags=["Reseñas"], summary="Crea una reseña para un libro")
def crear_resena(payload: ResenaCreate):
    with get_db() as conn:
        conn.execute("INSERT INTO resenas (libro_id, usuario_id, calificacion, comentario) VALUES (?, ?, ?, ?)", 
                     (payload.libro_id, payload.usuario_id, payload.calificacion, payload.comentario))
    return {"mensaje": "Reseña guardada"}

@app.get("/resenas/libro/{libro_id}", tags=["Reseñas"], summary="Retorna las reseñas de un libro y su promedio")
def obtener_resenas(libro_id: int):
    with get_db() as conn:
        filas = conn.execute("SELECT * FROM resenas WHERE libro_id = ?", (libro_id,)).fetchall()
        promedio = sum(r["calificacion"] for r in filas) / len(filas) if filas else 0
        return {"promedio": round(promedio, 2), "resenas": [dict(r) for r in filas]}