from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import json

from app.db.base import Base, engine, get_db
from app.models.analisis import Analisis, SnapshotRecibido, EstadoAnalisis
from app.schemas.snapshot import SnapshotCreate
from app.services.llm_client import LLMClient
from app.services.prompt_builder import PromptBuilder

# Crear tablas en la DB
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Analisis API")

@app.post("/analisis/iniciar")
async def iniciar_analisis(snapshot_in: SnapshotCreate, db: Session = Depends(get_db)):
    # 1. Guardar en Base de Datos (Inmutabilidad)
    nuevo_analisis = Analisis(
        proyecto_codigo=snapshot_in.proyecto_codigo,
        estado=EstadoAnalisis.PROCESANDO # Cambiamos a PROCESANDO
    )
    db.add(nuevo_analisis)
    db.flush()

    nuevo_snapshot = SnapshotRecibido(
        analisis_id=nuevo_analisis.id,
        payload_completo=json.dumps(snapshot_in.datos)
    )
    db.add(nuevo_snapshot)
    db.commit()
    db.refresh(nuevo_analisis)

    # 2. Preparar el Prompt
    prompt_builder = PromptBuilder()
    system_prompt, user_prompt = prompt_builder.construir_instrucciones(snapshot_in.dict())

    # 3. Llamar a la IA (OpenRouter)
    llm_client = LLMClient()
    respuesta_ia = await llm_client.enviar_prompt(system_prompt, user_prompt)

    # 4. Actualizar estado final en la DB
    try:
        # Aquí deberías parsear la respuesta_ia para ver si fue exitosa
        nuevo_analisis.estado = EstadoAnalisis.COMPLETADO
    except Exception:
        nuevo_analisis.estado = EstadoAnalisis.ERROR
    
    db.commit()

    return {
        "analisis_id": str(nuevo_analisis.id),
        "estado": nuevo_analisis.estado,
        "analisis_ia": respuesta_ia # Devolvemos la respuesta cruda de la IA
    }

@app.get("/")
def read_root():
    return {"status": "API Online 🚀"}