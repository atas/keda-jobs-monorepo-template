"""Shared NATS JetStream consumer for keda-jobs.

Provides run_consumer() — the main entry point for all jobs. Connects to NATS
JetStream, pulls messages from a durable consumer, calls the handler, and
manages acks/nacks. Includes a health check HTTP server on :8080.
"""

import asyncio
import json
import logging
import os
import signal

import nats
from aiohttp import web

logger = logging.getLogger(__name__)


async def _health_handler(request):
    return web.Response(text="OK")


async def _run_health_server():
    app = web.Application()
    app.router.add_get("/health", _health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    return runner


async def _run(handler, job_name, concurrency):
    nats_url = os.environ.get("NATS_URL", "nats://localhost:4222")
    stream = os.environ.get("NATS_STREAM", "keda-jobs-events")
    consumer_name = os.environ.get("NATS_CONSUMER", f"{job_name}-consumer")
    subject_filter = os.environ.get("NATS_SUBJECT_FILTER", job_name)

    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting {job_name} consumer (stream={stream}, consumer={consumer_name}, filter={subject_filter})")

    health_runner = await _run_health_server()
    logger.info("Health check server running on :8080")

    nc = await nats.connect(nats_url)
    js = nc.jetstream()

    sub = await js.pull_subscribe(
        subject_filter,
        durable=consumer_name,
        stream=stream,
    )

    shutdown = asyncio.Event()

    def _signal_handler():
        logger.info("Received shutdown signal")
        shutdown.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    async def publish(subject: str, data: dict):
        payload = json.dumps(data).encode()
        await js.publish(subject, payload)
        logger.info(f"Published to {subject}")

    logger.info(f"Pulling messages (concurrency={concurrency})...")

    while not shutdown.is_set():
        try:
            msgs = await sub.fetch(batch=concurrency, timeout=5)
        except nats.errors.TimeoutError:
            continue

        for msg in msgs:
            try:
                await msg.in_progress()
                data = json.loads(msg.data.decode())
                logger.info(f"Processing message on {msg.subject}")
                await asyncio.wait_for(handler(data, publish), timeout=300)
                await msg.ack()
                logger.info("Message processed and acked")
            except asyncio.TimeoutError:
                logger.error("Handler timed out after 5 minutes, nacking")
                await msg.nak(delay=30)
            except Exception:
                logger.exception("Handler failed, nacking message")
                await msg.nak(delay=30)

    logger.info("Shutting down...")
    await sub.unsubscribe()
    await nc.drain()
    await health_runner.cleanup()
    logger.info("Shutdown complete")


def run_consumer(handler, job_name, concurrency=1):
    """Main entry point. Blocks until SIGTERM/SIGINT."""
    asyncio.run(_run(handler, job_name, concurrency))
