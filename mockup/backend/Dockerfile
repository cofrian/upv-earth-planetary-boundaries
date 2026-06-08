FROM python:3.11-slim

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Torch en versión CPU: evita arrastrar las ruedas CUDA (~2.5 GB) y hace que la
# imagen sea independiente de la GPU y del sistema operativo anfitrión.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

COPY mockup/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mockup/backend/app /app/app
COPY mockup/backend/scripts /app/scripts

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=10 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
