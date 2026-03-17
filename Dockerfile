FROM python:3.11-slim

WORKDIR /app

# Upgrade vulnerable base image packages
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

CMD ["python", "-m", "oracle.worker"]
