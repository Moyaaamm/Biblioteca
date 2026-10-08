import httpx
from fastapi import FastAPI, Request, Response, HTTPException, status

app = FastAPI(title="API Gateway", description="Punto de entrada unificado SOA")

SERVICES = {
    "libros": "http://127.0.0.1:8001",
    "usuarios": "http://127.0.0.1:8002",
    "prestamos": "http://127.0.0.1:8003",
    "notificaciones": "http://127.0.0.1:8004",
    "multas": "http://127.0.0.1:8005",
    "resenas": "http://127.0.0.1:8006",
}

@app.api_route("/api/v1/{service}/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
async def gateway_proxy(service: str, path: str, request: Request):
    if service not in SERVICES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado")
    
    url = f"{SERVICES[service]}/{path}"
    body = await request.body()
    
    headers = dict(request.headers)
    headers.pop("host", None)
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                params=request.query_params
            )
            return Response(content=res.content, status_code=res.status_code, headers=dict(res.headers))
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="Falla de comunicación inter-servicio en el Gateway"
            )