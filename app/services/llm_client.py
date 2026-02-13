import httpx
import os
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def enviar_prompt(self, system_prompt: str, user_prompt: str):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000", # Requerido por OpenRouter
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "google/gemini-2.0-flash-001", # Modelo rápido y barato
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": { "type": "json_object" } # Forzamos respuesta JSON
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=headers, json=payload, timeout=60.0)
            return response.json()