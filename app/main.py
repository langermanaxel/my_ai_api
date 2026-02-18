from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.core.logging import setup_logging
from app.db.base import Base, engine
from app.api.v1.endpoints import analisis, usuarios, health

# 1. Configuración de logs profesional
setup_logging()

# 2. Sincronización de Base de Datos
Base.metadata.create_all(bind=engine)

# 3. Inicialización de FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API profesional para análisis de obras con auditoría LLM.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 4. Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Inclusión de Routers con prefijos consistentes
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(usuarios.router, prefix=f"{settings.API_V1_STR}/auth")
app.include_router(analisis.router, prefix=f"{settings.API_V1_STR}/analisis")

@app.get("/", tags=["Estado"])
def read_root():
    return {
        "status": "API Online 🚀", 
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }