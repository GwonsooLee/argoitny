#!/usr/bin/env python
"""Test worker to debug Celery issues"""
import os
import sys
import signal
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from config.celery import app
from celery.worker.worker import Worker

def main():
    """Run a simple worker"""
    logger.info("Starting test worker...")

    # Create worker
    worker = Worker(
        app=app,
        loglevel='DEBUG',
        pool_cls='solo',
        events=True,
        without_gossip=False,
        without_mingle=False,
        without_heartbeat=False,
    )

    # Setup signal handlers
    def shutdown(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("Worker configured, starting...")

    try:
        # Start worker
        worker.start()
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()