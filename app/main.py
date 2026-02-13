from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.db.base import Base, engine, get_db
from app.models.analisis import Analisis, SnapshotRecibido, EstadoAnalisis, ResultadoAnalisis, ObservacionGenerada
from app.schemas.snapshot import SnapshotCreate
from app.services.llm_client import LLMClient
from app.services.prompt_builder import PromptBuilder

# Crear tablas en la DB (Asegúrate de haber borrado las tablas viejas antes)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Analisis API")

@app.post("/analisis/iniciar")
async def iniciar_analisis(snapshot_in: SnapshotCreate, db: Session = Depends(get_db)):
    # 1. Crear Analisis y Snapshot (Persistencia inicial)
    nuevo_analisis = Analisis(
        proyecto_codigo=snapshot_in.proyecto_codigo, 
        estado=EstadoAnalisis.PROCESANDO
    )
    db.add(nuevo_analisis)
    db.flush()

    nuevo_snapshot = SnapshotRecibido(
        analisis_id=nuevo_analisis.id,
        payload_completo=json.dumps(snapshot_in.datos)
    )
    db.add(nuevo_snapshot)
    db.commit() # Guardamos los datos de entrada primero por seguridad

    try:
        # 2. IA - Generación de Prompt y llamada
        prompt_builder = PromptBuilder()
        system, user = prompt_builder.construir_instrucciones(snapshot_in.model_dump())
        
        llm_client = LLMClient()
        respuesta_raw = await llm_client.enviar_prompt(system, user)
        
        # Extraer el contenido de la respuesta de OpenRouter/Gemini
        # Nota: Usamos .get() para evitar errores si la respuesta no es la esperada
        string_contenido = respuesta_raw['choices'][0]['message']['content']
        contenido_ia = json.loads(string_contenido)

        # 3. Persistencia del Resultado
        resultado = ResultadoAnalisis(
            analisis_id=nuevo_analisis.id,
            resumen_general=contenido_ia.get('resumen'),
            score_coherencia=contenido_ia.get('score_coherencia'),
            detecta_riesgos=len(contenido_ia.get('riesgos', [])) > 0
        )
        db.add(resultado)
        db.flush()

        # Guardar cada observación de riesgo encontrada por la IA
        for riesgo in contenido_ia.get('riesgos', []):
            obs = ObservacionGenerada(
                resultado_id=resultado.id,
                titulo=riesgo.get('titulo'),
                descripcion=riesgo.get('descripcion'),
                nivel=riesgo.get('nivel')
            )
            db.add(obs)

        # 4. Finalización exitosa
        nuevo_analisis.estado = EstadoAnalisis.COMPLETADO
        db.commit()

        return {
            "mensaje": "Análisis completo y guardado", 
            "analisis_id": str(nuevo_analisis.id),
            "resultado": contenido_ia
        }

    except Exception as e:
        # En caso de error, marcamos el análisis como fallido en la DB
        db.rollback() # Revierte cambios no confirmados
        nuevo_analisis.estado = EstadoAnalisis.ERROR
        db.commit()
        
        # Log para el desarrollador
        print(f"Error procesando análisis: {str(e)}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Error en el procesamiento de IA: {str(e)}"
        )

@app.get("/")
def read_root():
    return {"status": "API Online 🚀"}