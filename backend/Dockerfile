# syntax=docker/dockerfile:1
# Build context is the repository root (see docker-compose.yml) so the
# synthetic sample_data/ can be bundled for the demo / "load sample" feature.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY sample_data/ /sample_data/
RUN chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 10001 loglens \
    && chown -R loglens /app
USER loglens

ENV SAMPLE_DATA_DIR=/sample_data
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
