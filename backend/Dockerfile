# Multi-stage build for optimized production image
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies (minimal set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv for faster dependency installation
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies from pyproject.toml without editable install
# Using . without -e flag to avoid creating = files
RUN uv pip install --system . && \
    find /usr/local/lib/python3.12/site-packages -type d -name "tests" ! -path "*/django/*" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.12/site-packages -type d -name "test" ! -path "*/django/*" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.12/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.12/site-packages -name "*.pyo" -delete && \
    find /usr/local/lib/python3.12/site-packages -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# ===== Production Image =====
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/django/.local/bin:$PATH"

# Install runtime dependencies only (minimal set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder (only necessary files)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/uvicorn /usr/local/bin/celery /usr/local/bin/django-admin /usr/local/bin/

# Create non-root user
RUN groupadd -r django && useradd -r -g django -u 1000 -m django

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=django:django manage.py ./
COPY --chown=django:django gunicorn.conf.py ./
COPY --chown=django:django config ./config
COPY --chown=django:django api ./api
COPY --chown=django:django scripts ./scripts

# Create necessary directories and collect static files
RUN mkdir -p /app/staticfiles /app/mediafiles /app/logs /app/tmp && \
    chown -R django:django /app && \
    chmod +x /app/scripts/*.sh

# Switch to non-root user for collectstatic
USER django

# Collect static files as django user
RUN python manage.py collectstatic --noinput --clear || true

# Copy entrypoint script
COPY --chown=django:django scripts/docker-entrypoint.sh /usr/local/bin/
USER root
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
USER django

# Expose port
EXPOSE 8000

# Health check using Python instead of curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health/').read()" || exit 1

# Entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command (can be overridden in Kubernetes)
CMD ["gunicorn", "config.asgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "120"]
