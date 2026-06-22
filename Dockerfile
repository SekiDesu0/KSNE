FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py database.py utils.py ./
COPY routes/      ./routes/
COPY models/      ./models/
COPY services/    ./services/
COPY templates/   ./templates/
COPY static/      ./static/
COPY db/          ./db/

RUN mkdir -p /app/static/cache /app/db

RUN useradd --create-home --shell /bin/bash appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:5000/login >/dev/null || exit 1

CMD ["python", "app.py"]
