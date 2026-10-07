from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sqlite3

app = FastAPI(
    title="Servicio de Multas y Sanciones",
    description="Deudas y bloqueo de lectores.",
    version="1.0.0",
)
DB = "multas.db"


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE IF NOT EXISTS multas(id INTEGER PRIMARY KEY AUTOINCREMENT,usuario_id INTEGER,monto REAL,motivo TEXT,pagada INTEGER DEFAULT 0)"
    )
    c.commit()
    return c


class Fine(BaseModel):
    usuario_id: int = Field(..., description="ID del usuario sancionado", examples=[1])
    monto: float = Field(
        ..., gt=0, description="Monto adeudado de la multa", examples=[25.5]
    )
    motivo: str = Field(..., description="Motivo de la sanción", examples=["Retraso"])


@app.post("/multas", status_code=201, summary="Asignar multa", tags=["Multas"])
def create(x: Fine):
    c = db()
    cur = c.execute(
        "INSERT INTO multas(usuario_id,monto,motivo) VALUES(?,?,?)",
        (x.usuario_id, x.monto, x.motivo),
    )
    c.commit()
    return dict(
        c.execute("SELECT * FROM multas WHERE id=?", (cur.lastrowid,)).fetchone()
    )


@app.get(
    "/sanciones/usuario/{usuario_id}/estatus",
    summary="Consultar adeudo",
    tags=["Multas"],
)
def status_user(usuario_id: int):
    r = (
        db()
        .execute(
            "SELECT COALESCE(SUM(monto),0) total,COALESCE(SUM(CASE WHEN pagada=0 THEN monto ELSE 0 END),0) adeudado FROM multas WHERE usuario_id=?",
            (usuario_id,),
        )
        .fetchone()
    )
    return {
        "usuario_id": usuario_id,
        "monto_total": r["total"],
        "monto_adeudado": r["adeudado"],
        "bloqueado": r["adeudado"] > 0,
    }


@app.patch("/multas/{id}/pagar", summary="Pagar multa", tags=["Multas"])
def pay(id: int):
    c = db()
    r = c.execute("SELECT * FROM multas WHERE id=?", (id,)).fetchone()
    if not r:
        raise HTTPException(404, "Multa no encontrada")
    c.execute("UPDATE multas SET pagada=1 WHERE id=?", (id,))
    c.commit()
    return dict(c.execute("SELECT * FROM multas WHERE id=?", (id,)).fetchone())
