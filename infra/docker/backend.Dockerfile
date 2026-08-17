FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl libpq-dev netcat-openbsd libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt
COPY backend /app
RUN chmod +x /app/entrypoint.sh 2>/dev/null || true
ARG BACKEND_PORT=5001
EXPOSE ${BACKEND_PORT}
CMD ["bash", "-lc", "./entrypoint.sh"]
