class PromptBuilder:
    def construir_instrucciones(self, datos_entrada: dict) -> tuple:
        """
        Transforma los datos del dominio en instrucciones de lenguaje natural 
        para el LLM, asegurando una respuesta técnica y estructurada.
        """
        
        # El System Prompt define el "persona" y las reglas inquebrantables
        system = """
        Eres un Ingeniero Civil Senior y Auditor de Proyectos con 20 años de experiencia. 
        Tu objetivo es detectar riesgos financieros, operativos y de seguridad en datos de obra.
        
        REGLAS CRÍTICAS:
        1. Sé crítico, profesional y técnico. 
        2. Si los datos son inconsistentes (ej: mucho gasto pero poco avance), márcalo con nivel CRITICO.
        3. Responde EXCLUSIVAMENTE en formato JSON.
        4. No incluyas texto explicativo fuera del JSON.
        """
        
        # El User Prompt organiza los datos y define el contrato de salida
        user = f"""
        Realiza una auditoría técnica del siguiente snapshot de obra:
        
        --- INICIO DE DATOS ---
        PROYECTO: {datos_entrada.get('proyecto_codigo')}
        DATOS DE OBRA: {datos_entrada.get('datos')}
        --- FIN DE DATOS ---
        
        INSTRUCCIONES DE ANÁLISIS:
        1. Evalúa el "resumen": Un párrafo técnico detallado sobre el estado actual.
        2. Calcula el "score_coherencia": Número 0-100.
        3. Identifica "riesgos": Lista de objetos con titulo, descripcion y nivel (CRITICO, ATENCION, INFORMATIVO).
        
        ESTRUCTURA DE RESPUESTA REQUERIDA (JSON):
        {{
            "resumen": "Descripción técnica aquí...",
            "score_coherencia": 85,
            "riesgos": [
                {{
                    "titulo": "Desvío presupuestario",
                    "descripcion": "El costo acumulado supera el proyectado para la fase de cimientos.",
                    "nivel": "CRITICO"
                }}
            ]
        }}
        """
        return system, user