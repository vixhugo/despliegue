from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import data, models, results

app = FastAPI(title="ML Pipeline API", version="1.0.0")

# ✅ Configurar CORS (permitir todo en despliegue)
# En producción puedes reemplazar "*" por tu dominio de frontend (Lovable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # permite peticiones desde cualquier origen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Incluir rutas
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(results.router, prefix="/api/results", tags=["results"])

# ✅ Rutas de prueba y salud
@app.get("/")
async def root():
    return {"message": "ML Pipeline API funcionando correctamente"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API funcionando"}
