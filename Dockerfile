# Usamos Python 3.12-slim ya que es la versión que detectamos en tus logs
FROM python:3.12-slim

# Variables de entorno para optimizar Python en contenedores
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema (incluimos libpq-dev para psycopg2 si fuera necesario)
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiamos primero los archivos de configuración de dependencias
# Esto permite aprovechar la caché de capas de Docker
COPY pyproject.toml .
# Si aún conservas el requirements.txt, descomenta la siguiente línea:
# COPY requirements.txt .

# Instalamos las dependencias
# Usamos "." para instalar el proyecto definido en pyproject.toml
RUN pip install --no-cache-dir .

# Copiamos el resto del código
COPY . .

# Seguridad: Crear usuario no-root
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exponer el puerto de FastAPI
EXPOSE 8000

# Healthcheck apuntando a la ruta de salud de tu API
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/analisis/detalle/test || exit 1

# Comando para ejecutar la aplicación
# Importante: ejecutamos el módulo app.main
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]