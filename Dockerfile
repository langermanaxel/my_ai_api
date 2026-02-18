# --- Etapa 1: Constructor (Build) ---
FROM python:3.12-slim AS builder

# Instalar uv directamente desde el binario oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Optimizamos caché: primero archivos de dependencias
COPY pyproject.toml uv.lock ./

# Sincronizamos dependencias (crea .venv)
RUN uv sync --frozen --no-install-project --no-dev

# --- Etapa 2: Ejecución (Runtime) ---
FROM python:3.12-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Instalar curl para el Healthcheck y dependencias de postgres
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar el entorno virtual y el código
COPY --from=builder /app/.venv /app/.venv
COPY . .

# Seguridad: Usuario no-root
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exponer el puerto
EXPOSE 8000

# Healthcheck apuntando a la ruta oficial versionada
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]