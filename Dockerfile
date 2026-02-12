FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY oracle_worker ./oracle_worker

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "oracle_worker.worker"]
