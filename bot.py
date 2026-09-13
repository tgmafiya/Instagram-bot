import asyncio
import logging
import os
from datetime import datetime, timezone

from aiohttp import web

from ai import create_content
from config import (
    PORT,
    POST_INTERVAL_HOURS,
    DAILY_GENERATION_LIMIT,
)

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    )
)

logger = logging.getLogger(__name__)


class BotState:

    def __init__(self):
        self.started_at = datetime.now(
            timezone.utc
        )

        self.last_generation = None
        self.last_error = None

        self.generated_today = 0
        self.today = (
            datetime.now(
                timezone.utc
            ).date()
        )

        self.total_generated = 0

        self.lock = asyncio.Lock()

    def reset_day_if_needed(self):
        today = (
            datetime.now(
                timezone.utc
            ).date()
        )

        if today != self.today:
            self.today = today
            self.generated_today = 0


state = BotState()


async def root(request):
    return web.json_response({
        "service": "instagram-ai-content-bot",
        "status": "running"
    })


async def health(request):
    state.reset_day_if_needed()

    return web.json_response({
        "status": "ok",
        "service": "instagram-ai-content-bot",
        "time": datetime.now(
            timezone.utc
        ).isoformat()
    })


async def status(request):
    state.reset_day_if_needed()

    return web.json_response({
        "status": "running",
        "started_at": state.started_at.isoformat(),
        "last_generation": (
            state.last_generation.isoformat()
            if state.last_generation
            else None
        ),
        "last_error": state.last_error,
        "generated_today": state.generated_today,
        "daily_limit": DAILY_GENERATION_LIMIT,
        "total_generated": state.total_generated
    })


async def generate_once():
    state.reset_day_if_needed()

    if (
        state.generated_today
        >= DAILY_GENERATION_LIMIT
    ):
        logger.info(
            "Daily generation limit reached."
        )
        return

    async with state.lock:

        # Check again after acquiring lock.
        state.reset_day_if_needed()

        if (
            state.generated_today
            >= DAILY_GENERATION_LIMIT
        ):
            return

        try:
            logger.info(
                "Starting AI content generation..."
            )

            result = await asyncio.to_thread(
                create_content
            )

            state.generated_today += 1
            state.total_generated += 1

            state.last_generation = (
                datetime.now(timezone.utc)
            )

            state.last_error = None

            logger.info(
                "Content generated successfully: %s",
                result["id"]
            )

        except Exception as exc:
            state.last_error = str(exc)

            logger.exception(
                "AI generation failed."
            )


async def scheduler():
    # Give HTTP server time to start.
    await asyncio.sleep(5)

    while True:

        try:
            await generate_once()

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Unexpected scheduler error."
            )

        sleep_seconds = (
            POST_INTERVAL_HOURS * 3600
        )

        logger.info(
            "Next generation in %s hours.",
            POST_INTERVAL_HOURS
        )

        await asyncio.sleep(
            sleep_seconds
        )


async def on_startup(app):
    app["scheduler_task"] = (
        asyncio.create_task(
            scheduler()
        )
    )

    logger.info(
        "Scheduler started."
    )


async def on_cleanup(app):
    task = app.get(
        "scheduler_task"
    )

    if task:
        task.cancel()

        try:
            await task

        except asyncio.CancelledError:
            pass

    logger.info(
        "Scheduler stopped."
    )


def create_app():
    app = web.Application()

    app.router.add_get(
        "/",
        root
    )

    app.router.add_get(
        "/health",
        health
    )

    app.router.add_get(
        "/status",
        status
    )

    app.on_startup.append(
        on_startup
    )

    app.on_cleanup.append(
        on_cleanup
    )

    return app


def main():
    port = int(
        os.getenv(
            "PORT",
            str(PORT)
        )
    )

    app = create_app()

    logger.info(
        "Starting server on 0.0.0.0:%s",
        port
    )

    web.run_app(
        app,
        host="0.0.0.0",
        port=port
    )


if __name__ == "__main__":
    main()
