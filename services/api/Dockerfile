FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
# system libs RapidOCR / OpenCV need
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-scan.txt requirements-db.txt ./
RUN pip install -r requirements.txt -r requirements-scan.txt -r requirements-db.txt
COPY . .
ENV PORT=8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
