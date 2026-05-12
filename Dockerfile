FROM python:3.12-slim

# Dependencias del sistema requeridas por OpenCV y otras librerías
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY app.py .
COPY web_app.py .
COPY job_runner.py .
COPY config_schema.py .
COPY history.py .
COPY styles.css .

# Variables de entorno por defecto
ENV SAM_CHECKPOINT_PATH=/data/sam_vit_b_01ec64.pth
ENV INPUT_DIR=/data/in
ENV OUTPUT_DIR=/data/res
ENV PORT=8501

# Crear directorios de datos
RUN mkdir -p /data/in /data/res

EXPOSE 8501

CMD ["sh", "-c", "streamlit run web_app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true"]
