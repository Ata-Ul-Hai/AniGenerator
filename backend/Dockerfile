FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		chromium \
		curl \
		ffmpeg \
		nodejs \
		npm \
	&& rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app/backend
COPY renderer /app/renderer
COPY assets /app/assets
COPY scripts /app/scripts

RUN npm ci --prefix /app/renderer

RUN useradd --system --uid 10001 --create-home appuser \
	&& mkdir -p /app/renderer/runs /app/renderer/public/runs \
	&& chown -R appuser:appuser /app

USER appuser

CMD ["uvicorn", "backend.main:app", "--app-dir", "/app", "--host", "0.0.0.0", "--port", "8000"]
