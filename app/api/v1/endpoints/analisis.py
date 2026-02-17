import json, re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.db.base import get_db, Base, engine
from app.models.analisis import (
    Analisis, SnapshotRecibido, EstadoAnalisis, 
    ResultadoAnalisis, ObservacionGenerada, 
    DatoProyecto, DatoEtapa, DatoAvance, DatoSeguridad,
    InvocacionLLM, PromptGenerado, RespuestaLLM
)
from app.schemas.snapshot import SnapshotCreate
from app.services.llm_client import LLMClient
from app.services.prompt_builder import PromptBuilder
from app.services.webhook_client import WebhookClient
from app.utils.logger import logger

router = APIRouter()

@router.post("/iniciar", tags=["Procesamiento"])
async def iniciar_analisis(snapshot_in: SnapshotCreate, db: Session = Depends(get_db)):
    """Inicia el proceso de persistencia de datos y análisis con IA."""
    logger.info(f"📥 Recibida solicitud para proyecto: {snapshot_in.proyecto_codigo}")
    
    nuevo_analisis = Analisis(
        proyecto_codigo=snapshot_in.proyecto_codigo, 
        estado=EstadoAnalisis.PROCESANDO
    )
    db.add(nuevo_analisis)
    db.flush() 

    try:
        # 1. PERSISTENCIA DE DATOS ESTRUCTURADOS
        nuevo_snapshot = SnapshotRecibido(
            analisis_id=nuevo_analisis.id,
            payload_completo=json.dumps(snapshot_in.datos)
        )
        db.add(nuevo_snapshot)
        db.flush() 

        datos_json = snapshot_in.datos
        
        # Mapeos de Snapshot (Proyecto, Etapas, Avances, Seguridad)
        db.add(DatoProyecto(
            snapshot_id=nuevo_snapshot.id,
            codigo=datos_json.get("proyecto", {}).get("codigo"),
            nombre=datos_json.get("proyecto", {}).get("nombre"),
            responsable_tecnico=datos_json.get("proyecto", {}).get("responsable_tecnico")
        ))

        for etapa in datos_json.get("etapas", []):
            if isinstance(etapa, dict):
                db.add(DatoEtapa(
                    snapshot_id=nuevo_snapshot.id,
                    nombre=etapa.get("nombre"),
                    estado=etapa.get("estado"),
                    avance_estimado=etapa.get("avance_estimado")
                ))

        for avance in datos_json.get("registros_avance", []):
            if isinstance(avance, dict):
                fecha_obj = None
                try: fecha_obj = datetime.strptime(avance.get("fecha"), "%Y-%m-%d").date()
                except: pass
                db.add(DatoAvance(
                    snapshot_id=nuevo_snapshot.id,
                    fecha_registro=fecha_obj,
                    supervisor=avance.get("supervisor"),
                    porcentaje_avance=avance.get("porcentaje_avance"),
                    presenta_desvios=avance.get("presenta_desvios", False),
                    tareas_ejecutadas=avance.get("tareas_ejecutadas", []),
                    oficios_activos=avance.get("oficios_activos", [])
                ))

        lista_seguridad = datos_json.get("medidas_seguridad", [])
        if lista_seguridad:
            total = len(lista_seguridad)
            cumple = sum(1 for m in lista_seguridad if isinstance(m, dict) and m.get("cumple") is True)
            db.add(DatoSeguridad(
                snapshot_id=nuevo_snapshot.id,
                fecha_registro=datetime.now().date(),
                medidas_implementadas=lista_seguridad,
                total_medidas_chequeadas=total,
                cumple_todas=(total == cumple)
            ))

        db.commit()
        logger.info(f"💾 Datos guardados exitosamente")

        # 2. PROCESAMIENTO CON IA Y AUDITORÍA
        prompt_builder = PromptBuilder()
        system_p, user_p = prompt_builder.construir_instrucciones(snapshot_in.model_dump())
        
        invocacion = InvocacionLLM(
            analisis_id=nuevo_analisis.id,
            modelo_usado="gpt-4o-mini",
            invocado_at=datetime.utcnow()
        )
        db.add(invocacion)
        db.flush()

        db.add(PromptGenerado(invocacion_id=invocacion.id, system_prompt=system_p, user_prompt=user_p))

        llm_client = LLMClient()
        start_time = datetime.utcnow()
        respuesta_raw = await llm_client.enviar_prompt(system_p, user_p)
        end_time = datetime.utcnow()

        invocacion.duracion_ms = int((end_time - start_time).total_seconds() * 1000)
        
        if "choices" not in respuesta_raw:
             invocacion.exitosa = False
             invocacion.error_detalle = str(respuesta_raw)
             db.commit()
             raise Exception("Fallo en respuesta de IA")

        string_contenido = respuesta_raw['choices'][0]['message']['content']
        invocacion.tokens_prompt = respuesta_raw.get("usage", {}).get("prompt_tokens")
        invocacion.tokens_respuesta = respuesta_raw.get("usage", {}).get("completion_tokens")

        contenido_ia = {}
        try:
            contenido_ia = json.loads(string_contenido)
        except:
            match = re.search(r"(\{.*\})", string_contenido, re.DOTALL)
            if match: contenido_ia = json.loads(match.group(1))

        db.add(RespuestaLLM(invocacion_id=invocacion.id, respuesta_raw=string_contenido, respuesta_parseada=contenido_ia))

        # 3. RESULTADOS DE NEGOCIO
        resultado = ResultadoAnalisis(
            analisis_id=nuevo_analisis.id,
            resumen_general=contenido_ia.get('resumen'),
            score_coherencia=contenido_ia.get('score_coherencia'),
            detecta_riesgos=len(contenido_ia.get('riesgos', [])) > 0
        )
        db.add(resultado)
        db.flush()

        for riesgo in contenido_ia.get('riesgos', []):
            db.add(ObservacionGenerada(
                resultado_id=resultado.id,
                titulo=riesgo.get('titulo'),
                descripcion=riesgo.get('descripcion'),
                nivel=riesgo.get('nivel')
            ))

        nuevo_analisis.estado = EstadoAnalisis.COMPLETADO
        db.commit()
        
        webhook = WebhookClient()
        await webhook.notificar_finalizacion(nuevo_analisis.id, nuevo_analisis.proyecto_codigo, nuevo_analisis.estado)

        return {"analisis_id": nuevo_analisis.id, "resultado": contenido_ia}

    except Exception as e:
        db.rollback() 
        nuevo_analisis.estado = EstadoAnalisis.ERROR
        db.commit()
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detalle/{analisis_id}", tags=["Consultas"])
async def obtener_analisis_completo(analisis_id: str, db: Session = Depends(get_db)):
    """Obtiene la radiografía completa de un análisis y su auditoría."""
    analisis = db.query(Analisis).options(
        joinedload(Analisis.snapshot).joinedload(SnapshotRecibido.proyecto),
        joinedload(Analisis.snapshot).joinedload(SnapshotRecibido.etapas),
        joinedload(Analisis.resultado).joinedload(ResultadoAnalisis.observaciones),
        joinedload(Analisis.invocaciones).joinedload(InvocacionLLM.respuesta)
    ).filter(Analisis.id == analisis_id).first()

    if not analisis:
        raise HTTPException(status_code=404, detail="No encontrado")

    return {
        "id": analisis.id,
        "estado": analisis.estado,
        "datos_obra": {
            "proyecto": analisis.snapshot.proyecto[0] if analisis.snapshot and analisis.snapshot.proyecto else None,
            "etapas": len(analisis.snapshot.etapas) if analisis.snapshot else 0
        },
        "auditoria": [
            {"modelo": i.modelo_usado, "tokens": (i.tokens_prompt or 0) + (i.tokens_respuesta or 0)} 
            for i in analisis.invocaciones
        ],
        "resultado": analisis.resultado
    }

@router.post("/reset-db", tags=["Mantenimiento"])
def reset_database():
    """Limpia y recrea la base de datos."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return {"mensaje": "Base de datos reseteada"}