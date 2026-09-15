FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PHAROS_MODE=hosted \
    PHAROS_HOST=0.0.0.0 \
    PORT=7860 \
    PHAROS_DATA=/data/pharos

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && addgroup --system pharos \
    && adduser --system --ingroup pharos --home /home/pharos pharos \
    && mkdir -p /data/pharos \
    && chown pharos:pharos /data/pharos

USER pharos
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/healthz', timeout=2).read()"]
CMD ["pharos-web"]
