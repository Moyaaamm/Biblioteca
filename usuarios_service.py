import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional


class UsuarioCreate(BaseModel):
    nombre: str = Field(..., description="Nombre completo del lector", json_schema_extra={"example": "Ana Gómez"})
    email: str = Field(..., description="Correo electrónico único del usuario", json_schema_extra={"example": "ana.gomez@email.com"})

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, description="Nuevo nombre del usuario", json_schema_extra={"example": "Ana Gómez Pérez"})
    email: Optional[str] = Field(None, description="Nuevo correo electrónico", json_schema_extra={"example": "anag.perez@email.com"})

class UsuarioActivoUpdate(BaseModel):
    activo: bool = Field(..., description="Estado de la cuenta del usuario", json_schema_extra={"example": True})


def get_db():
    conn = sqlite3.connect("usuarios.db")
    conn.row_factory = sqlite3.Row
    return conn

@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                activo BOOLEAN NOT NULL DEFAULT 1
            )
        """)
    yield

app = FastAPI(
    title="Servicio de Usuarios", 
    description="Microservicio para la gestión de lectores de la biblioteca",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/usuarios", status_code=status.HTTP_201_CREATED, tags=["Gestión de Usuarios"], summary="Registra un nuevo usuario")
def crear_usuario(usuario: UsuarioCreate):
    with get_db() as conn:
        existente = conn.execute("SELECT id FROM usuarios WHERE email = ?", (usuario.email,)).fetchone()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya se encuentra registrado."
            )
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (nombre, email, activo) VALUES (?, ?, 1)",
            (usuario.nombre, usuario.email)
        )
        usuario_id = cursor.lastrowid
        return {
            "id": usuario_id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "activo": True
        }

@app.get("/usuarios", status_code=status.HTTP_200_OK, tags=["Gestión de Usuarios"], summary="Retorna el padrón de usuarios")
def obtener_usuarios():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM usuarios ORDER BY nombre").fetchall()
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="No existen usuarios registrados"
            )
        return [dict(row) for row in rows]

@app.get("/usuarios/{usuario_id}", status_code=status.HTTP_200_OK, tags=["Gestión de Usuarios"], summary="Consulta el perfil de un usuario específico")
def obtener_usuario(usuario_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        return dict(row)

@app.patch("/usuarios/{usuario_id}", tags=["Gestión de Usuarios"], summary="Actualización parcial de los datos del usuario")
def editar_usuario(usuario_id: int, payload: UsuarioUpdate):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        
        usuario_actual = dict(row)
        
        nuevo_nombre = payload.nombre if payload.nombre is not None else usuario_actual["nombre"]
        nuevo_email = payload.email if payload.email is not None else usuario_actual["email"]
        
        if payload.email is not None and payload.email != usuario_actual["email"]:
            existente = conn.execute("SELECT id FROM usuarios WHERE email = ? AND id != ?", (payload.email, usuario_id)).fetchone()
            if existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El correo electrónico ya está en uso por otro usuario."
                )

        conn.execute(
            "UPDATE usuarios SET nombre = ?, email = ? WHERE id = ?",
            (nuevo_nombre, nuevo_email, usuario_id)
        )
        
        return {**usuario_actual, "nombre": nuevo_nombre, "email": nuevo_email}

@app.patch("/usuarios/{usuario_id}/estado", tags=["Administración"], summary="Modifica el estatus activo/inactivo del usuario")
def actualizar_estado_usuario(usuario_id: int, payload: UsuarioActivoUpdate):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        
        conn.execute(
            "UPDATE usuarios SET activo = ? WHERE id = ?",
            (1 if payload.activo else 0, usuario_id)
        )
        return {"id": usuario_id, "activo": payload.activo}

@app.delete("/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Gestión de Usuarios"], summary="Elimina un perfil de usuario", description="Realiza la eliminación física de un usuario en la base de datos.")
def eliminar_usuario(usuario_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        
        conn.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    
    return None