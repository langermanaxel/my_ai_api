from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import logging

from app.api.dependencies import get_db
from app.config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health", tags=["Mantenimiento"])
async def health_check(db: Session = Depends(get_db)):
    """
    Diagnóstico Profesional: Verifica el estado de la API y de la Base de Datos.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME,
        "components": {
            "api": "up",
            "database": "unknown"
        }
    }

    try:
        # Ejecutamos una consulta mínima para validar la conexión real a Postgres
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "up"
    except Exception as e:
        # Si la DB falla, el estado general de la API pasa a 'unhealthy'
        logger.error(f"Error en Health Check de Base de Datos: {str(e)}")
        health_status["components"]["database"] = "down"
        health_status["status"] = "unhealthy"

    return health_status