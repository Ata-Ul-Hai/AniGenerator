FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Step 1: Install system dependencies including NodeSource for Node.js 20
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		chromium \
		curl \
		ffmpeg \
		ca-certificates \
		gnupg \
		libnss3 \
		libatk1.0-0 \
		libatk-bridge2.0-0 \
		libcups2 \
		libdrm2 \
		libxkbcommon0 \
		libxcomposite1 \
		libxdamage1 \
		libxrandr2 \
		libgbm1 \
		libasound2 \
	&& mkdir -p /etc/apt/keyrings \
	&& curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
	&& echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
	&& apt-get update \
	&& apt-get install nodejs -y \
	&& rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app/backend
COPY renderer /app/renderer
COPY assets /app/assets
COPY scripts /app/scripts

# Use npm install for better compatibility with different environments
RUN npm install --prefix /app/renderer

RUN useradd --system --uid 10001 --create-home appuser \
	&& mkdir -p /app/renderer/runs /app/renderer/public/runs \
	&& chown -R appuser:appuser /app

USER appuser

# Use the PORT environment variable if provided (default to 8080 for Cloud Run)
# Run migrations as a 'soft' step, then start the web server
CMD ["sh", "-c", "python /app/scripts/migrate_db.py || echo 'Migration failed, but continuing...' && uvicorn backend.main:app --app-dir /app --host 0.0.0.0 --port ${PORT:-8080}"]
