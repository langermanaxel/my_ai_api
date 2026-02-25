from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title="AI Construction Analysis API", version="1.0.0")

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)