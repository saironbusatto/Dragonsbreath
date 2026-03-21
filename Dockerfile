FROM python:3.11-slim

WORKDIR /app

# Dependências de sistema para Google Cloud TTS (gRPC)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Apenas dependências necessárias para a Web API
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY . .

EXPOSE 8080
CMD uvicorn web_api:app --host 0.0.0.0 --port ${PORT:-8080}
