ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Startup script to auto-run migrations then start API
RUN chmod +x /app/start.sh || true

EXPOSE 8000

CMD ["/bin/sh", "-c", "/app/start.sh"]
