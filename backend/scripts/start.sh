#!/bin/bash
# Production startup script for AlgoItny Backend
# This script ensures proper initialization before starting Gunicorn

set -e

echo "Starting AlgoItny Backend with Gunicorn + Uvicorn workers..."

# Wait for database to be ready (if using docker-compose, this is handled by healthcheck)
echo "Checking database connection..."

# Collect static files for production
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || true

# Start Gunicorn with Uvicorn workers
echo "Starting Gunicorn with Uvicorn workers..."
exec gunicorn config.asgi:application -c gunicorn.conf.py
