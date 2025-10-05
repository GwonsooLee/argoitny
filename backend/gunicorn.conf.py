"""
Gunicorn configuration file for AlgoItny Django Backend
Optimized for production with async support using Uvicorn workers
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Process naming
proc_name = "algoitny-backend"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Gunicorn with Uvicorn workers")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Gunicorn")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Gunicorn is ready. Spawning workers")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")
