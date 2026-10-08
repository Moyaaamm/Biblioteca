import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

class MultaCreate(BaseModel):
    usuario_id: int = Field(..., description="ID del usuario sancionado", json_schema_extra={"example": 1})
    monto: float = Field(..., description="Monto económico de la multa", json_schema_extra={"example": 50.0})
    motivo: str = Field(..., description="Razón de la multa", json_schema_extra={"example": "Retraso en devolución"})

def get_db():
    conn = sqlite3.connect("multas.db")
    conn.row_factory = sqlite3.Row
    return conn

@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS multas (id INTEGER PRIMARY KEY, usuario_id INTEGER, monto REAL, motivo TEXT, pagada BOOLEAN DEFAULT 0)")
    yield

app = FastAPI(
    title="Servicio de Multas y Sanciones", 
    description="Control de deudas económicas y estado de bloqueo de usuarios",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/multas", status_code=status.HTTP_201_CREATED, tags=["Sanciones"], summary="Asigna una multa a un usuario")
def crear_multa(multa: MultaCreate):
    with get_db() as conn:
        conn.execute("INSERT INTO multas (usuario_id, monto, motivo) VALUES (?, ?, ?)", (multa.usuario_id, multa.monto, multa.motivo))
    return {"mensaje": "Multa registrada"}

@app.get("/sanciones/usuario/{usuario_id}/estatus", tags=["Sanciones"], summary="Consulta el estatus de adeudos y bloqueos")
def estatus_sanciones(usuario_id: int):
    with get_db() as conn:
        multas = conn.execute("SELECT SUM(monto) as total FROM multas WHERE usuario_id = ? AND pagada = 0", (usuario_id,)).fetchone()
        total = multas["total"] if multas["total"] else 0.0
        return {"usuario_id": usuario_id, "adeudo": total, "bloqueado": total > 0}

@app.patch("/multas/{id}/pagar", tags=["Sanciones"], summary="Marca una multa como pagada")
def pagar_multa(id: int):
    with get_db() as conn:
        conn.execute("UPDATE multas SET pagada = 1 WHERE id = ?", (id,))
    return {"mensaje": "Multa pagada"}