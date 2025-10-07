# Gunicorn + Uvicorn Configuration Guide

This document explains the Gunicorn configuration for the AlgoItny backend.

## Overview

The backend now uses **Gunicorn** as the WSGI/ASGI server with **Uvicorn workers** for async support. This setup provides:

- Multiprocess architecture for better CPU utilization
- Async I/O support through Uvicorn workers
- Production-ready process management
- Automatic worker recycling and health monitoring
- Better performance under load

## Configuration Details

### Worker Configuration

**File**: `gunicorn.conf.py`

**Key Settings**:
- **Workers**: By default, `(CPU cores * 2) + 1` workers are spawned
  - Can be overridden with `GUNICORN_WORKERS` environment variable
  - For containers with 2 CPUs: 5 workers
  - For containers with 4 CPUs: 9 workers

- **Worker Class**: `uvicorn.workers.UvicornWorker`
  - Enables async/await support in Django views
  - Uses ASGI protocol for better WebSocket and async support

- **Worker Connections**: 1000 concurrent connections per worker

- **Max Requests**: 1000 requests per worker before recycling
  - Prevents memory leaks
  - Adds jitter of 50 requests to avoid thundering herd

### Timeout Configuration

- **Timeout**: 120 seconds for worker responses
- **Graceful Timeout**: 30 seconds for graceful shutdown
- **Keepalive**: 5 seconds for persistent connections

### Logging

- **Access Log**: Streamed to stdout (Docker-friendly)
- **Error Log**: Streamed to stderr
- **Log Level**: Controlled by `GUNICORN_LOG_LEVEL` (default: info)

## Environment Variables

Set these in your `.env` file or docker-compose:

```bash
# Number of worker processes (default: auto-calculated)
GUNICORN_WORKERS=4

# Logging level: debug, info, warning, error, critical
GUNICORN_LOG_LEVEL=info
```

## Docker Compose Integration

The `docker-compose.yml` has been updated to:

1. Use Gunicorn instead of `runserver`
2. Pass worker and logging configuration via environment variables
3. Use the ASGI application for async support

**Command**:
```bash
gunicorn config.asgi:application -c gunicorn.conf.py
```

## Performance Optimizations

### 1. Database Connection Pooling
- `CONN_MAX_AGE: 600` - Connections kept alive for 10 minutes
- `CONN_HEALTH_CHECKS: True` - Verify connections before use
- Reduces database connection overhead

### 2. Worker Process Management
- Automatic worker recycling prevents memory leaks
- Graceful worker shutdown ensures no dropped requests
- Health monitoring detects and replaces unhealthy workers

### 3. Async Support
- Uvicorn workers enable native async/await in Django
- Better I/O concurrency for database and external API calls
- WebSocket support for real-time features

## Monitoring

### View Active Workers

In the backend container:
```bash
ps aux | grep gunicorn
```

### Check Logs

```bash
docker logs -f algoitny-backend
```

### Monitor Worker Health

Gunicorn automatically logs:
- Worker startup/shutdown
- Worker crashes and restarts
- Request timeouts
- Slow requests

## Production Recommendations

### For Small Deployments (1-2 CPUs)
```bash
GUNICORN_WORKERS=3
GUNICORN_LOG_LEVEL=warning
```

### For Medium Deployments (4 CPUs)
```bash
GUNICORN_WORKERS=6
GUNICORN_LOG_LEVEL=info
```

### For Large Deployments (8+ CPUs)
```bash
GUNICORN_WORKERS=12
GUNICORN_LOG_LEVEL=warning
```

### High-Traffic Tuning
For high-traffic scenarios, consider:
- Increasing `worker_connections` to 2000+
- Adjusting `max_requests` based on memory usage
- Using Redis for session storage
- Implementing CDN for static files
- Adding nginx as a reverse proxy

## Troubleshooting

### Workers Timing Out
- Increase `timeout` in `gunicorn.conf.py`
- Check for slow database queries
- Profile async operations

### High Memory Usage
- Reduce `max_requests` for more frequent recycling
- Check for memory leaks in application code
- Monitor with `docker stats`

### Connection Errors
- Verify database connection pooling settings
- Check `CONN_MAX_AGE` and `CONN_HEALTH_CHECKS`
- Ensure MySQL `max_connections` is sufficient

### Worker Crashes
- Check error logs for stack traces
- Verify all async operations use proper await syntax
- Ensure no blocking I/O in async views

## Migration from Runserver

**Before** (Development):
```bash
python manage.py runserver 0.0.0.0:8000
```

**After** (Production):
```bash
gunicorn config.asgi:application -c gunicorn.conf.py
```

**Key Differences**:
- Multiple worker processes instead of single-threaded
- Production-grade error handling and logging
- Automatic worker health monitoring
- Better performance under load
- Async/await support with Uvicorn workers

## Additional Resources

- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Django ASGI Documentation](https://docs.djangoproject.com/en/stable/howto/deployment/asgi/)
