# Streamlit diagnostic + guidance dashboard.
# Build:  docker build -t pricing-ai .
# Run:    docker run -p 8501:8501 pricing-ai
FROM python:3.12-slim

WORKDIR /app

# libgomp1 is the OpenMP runtime LightGBM needs at import time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only what the app needs at runtime (see .dockerignore for exclusions).
COPY pricing/ ./pricing/
COPY app/ ./app/
COPY data/synthetic/ ./data/synthetic/

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
EXPOSE 8501

CMD ["streamlit", "run", "app/dashboard.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
