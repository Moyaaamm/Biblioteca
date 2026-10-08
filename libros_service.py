import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional


class LibroUpdate(BaseModel):
    titulo: Optional[str] = Field(None, description="Nuevo título del libro", json_schema_extra={"example": "El Quijote de la Mancha"})
    autor: Optional[str] = Field(None, description="Nuevo autor del libro", json_schema_extra={"example": "Miguel de Cervantes Saavedra"})

class LibroCreate(BaseModel):
    titulo: str = Field(..., description="Título del libro a registrar", json_schema_extra={"example": "El Quijote"})
    autor: str = Field(..., description="Autor del libro", json_schema_extra={"example": "Miguel de Cervantes"})

class DisponibilidadUpdate(BaseModel):
    disponible: bool = Field(..., description="Estado de disponibilidad del libro", json_schema_extra={"example": False})


def get_db():
    conn = sqlite3.connect("libros.db")
    conn.row_factory = sqlite3.Row
    return conn

@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS libros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                autor TEXT NOT NULL,
                disponible BOOLEAN NOT NULL DEFAULT 1
            )
        """)
    yield

app = FastAPI(
    title="Servicio de Libros", 
    description="Microservicio para la gestión del catálogo de libros e inventario",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/libros", status_code=status.HTTP_201_CREATED, tags=["Catálogo"], summary="Registra un nuevo libro")
def crear_libro(libro: LibroCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO libros (titulo, autor, disponible) VALUES (?, ?, 1)",
            (libro.titulo, libro.autor)
        )
        libro_id = cursor.lastrowid
        return {"id": libro_id, "titulo": libro.titulo, "autor": libro.autor, "disponible": True}

@app.get("/libros", status_code=status.HTTP_200_OK, tags=["Catálogo"], summary="Retorna el catálogo completo")
def obtener_libros():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM libros ORDER BY titulo").fetchall()
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existen libros registrados")
        return [dict(row) for row in rows]

@app.get("/libros/{libro_id}", tags=["Catálogo"], summary="Consulta el detalle de un libro")
def obtener_libro(libro_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM libros WHERE id = ?", (libro_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        return dict(row)

@app.patch("/libros/{libro_id}/disponibilidad", tags=["Inventario"], summary="Cambia el indicador de disponibilidad")
def actualizar_disponibilidad(libro_id: int, payload: DisponibilidadUpdate):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM libros WHERE id = ?", (libro_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        
        conn.execute(
            "UPDATE libros SET disponible = ? WHERE id = ?",
            (1 if payload.disponible else 0, libro_id)
        )
        return {"id": libro_id, "disponible": payload.disponible}

@app.patch("/libros/{libro_id}", tags=["Catálogo"], summary="Actualización parcial de título o autor")
def editar_libro(libro_id: int, payload: LibroUpdate):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM libros WHERE id = ?", (libro_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        
        libro_actual = dict(row)
        
        nuevo_titulo = payload.titulo if payload.titulo is not None else libro_actual["titulo"]
        nuevo_autor = payload.autor if payload.autor is not None else libro_actual["autor"]
        
        conn.execute(
            "UPDATE libros SET titulo = ?, autor = ? WHERE id = ?",
            (nuevo_titulo, nuevo_autor, libro_id)
        )
        
        return {**libro_actual, "titulo": nuevo_titulo, "autor": nuevo_autor}

@app.delete("/libros/{libro_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Catálogo"], summary="Elimina un libro del catálogo")
def eliminar_libro(libro_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM libros WHERE id = ?", (libro_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        
        if not row["disponible"]:
            raise HTTPException(
                status_code=400, 
                detail="No se puede eliminar un libro que está prestado actualmente."
            )
        
        conn.execute("DELETE FROM libros WHERE id = ?", (libro_id,))
    
    return None