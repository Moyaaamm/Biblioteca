from fastapi import FastAPI, status
from pydantic import BaseModel, Field

class NotificacionRequest(BaseModel):
    destinatario: str = Field(..., description="Correo electrónico del destinatario", json_schema_extra={"example": "estudiante@test.com"})
    asunto: str = Field(..., description="Asunto del correo", json_schema_extra={"example": "Préstamo de libro"})
    mensaje: str = Field(..., description="Cuerpo del mensaje", json_schema_extra={"example": "Se prestó el libro 1 de manera exitosa."})

app = FastAPI(
    title="Servicio de Notificaciones",
    description="Simulación de emisión de correos y alertas transaccionales",
    version="1.0.0"
)

@app.post("/notificaciones/enviar", status_code=status.HTTP_200_OK, tags=["Notificaciones"], summary="Simula el envío de un correo", description="Recibe los datos del correo e imprime en consola para simular el envío sin bloquear procesos.")
def enviar_notificacion(payload: NotificacionRequest):
    print("\n" + "="*40)
    print("SIMULACIÓN DE ENVÍO DE CORREO")
    print(f"Para:    {payload.destinatario}")
    print(f"Asunto:  {payload.asunto}")
    print(f"Mensaje: {payload.mensaje}")
    print("="*40 + "\n")
    
    return {"mensaje": "Notificación procesada (simulada)"}