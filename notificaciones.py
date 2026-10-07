from fastapi import FastAPI
from pydantic import BaseModel, Field
from datetime import datetime

app = FastAPI(
    title="Servicio de Notificaciones",
    description="Simula correos y alertas transaccionales.",
    version="1.0.0",
)


class Notification(BaseModel):
    destinatario: str = Field(
        ...,
        description="Correo electrónico del destinatario",
        examples=["ana@example.com"],
    )
    asunto: str = Field(
        ..., description="Asunto del mensaje", examples=["Préstamo confirmado"]
    )
    mensaje: str = Field(
        ...,
        description="Cuerpo del mensaje a enviar",
        examples=["Tu préstamo fue registrado"],
    )


@app.post(
    "/notificaciones/enviar",
    status_code=201,
    summary="Enviar notificación",
    tags=["Notificaciones"],
)
def send(x: Notification):
    print(
        f"[{datetime.now().isoformat()}] NOTIFICACIÓN -> {x.destinatario}: {x.asunto}"
    )
    return {"enviado": True, "destinatario": x.destinatario, "asunto": x.asunto}
