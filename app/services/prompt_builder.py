class PromptBuilder:
    @staticmethod
    def construir_instrucciones(datos_proyecto: dict) -> tuple:
        system = "Eres un experto en auditoría de obras. Analiza los datos y devuelve un JSON con 'riesgos' (lista) y 'puntuacion_coherencia' (0-100)."
        
        user = f"""
        Analiza el siguiente proyecto:
        Código: {datos_proyecto.get('proyecto_codigo')}
        Detalles: {datos_proyecto.get('datos')}
        
        Devuelve estrictamente un JSON.
        """
        return system, user