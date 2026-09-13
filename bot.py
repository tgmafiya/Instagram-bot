import asyncio
import logging
import os
from datetime import datetime, timezone

from aiohttp import web

from aiogram import (
    Bot,
    Dispatcher,
    F,
)
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

from config import (
    BOT_TOKEN,
    ADMIN_ID,
    PORT,
    validate_config,
)

from storage import (
    get_settings,
    update_settings,
    get_history,
)

from ai import create_content


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    )
)

logger = logging.getLogger(__name__)


validate_config()

ADMIN_ID = int(ADMIN_ID)

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


class State:

    def __init__(self):

        self.started_at = (
            datetime.now(
                timezone.utc
            )
        )

        self.last_generation = None
        self.last_error = None

        self.total_generated = 0

        self.lock = asyncio.Lock()


state = State()


# ==========================================
# ADMIN CHECK
# ==========================================

def is_admin(user_id):
    return user_id == ADMIN_ID


async def reject_if_not_admin(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "⛔ Only admin can access this bot."
        )

        return True

    return False


# ==========================================
# KEYBOARD
# ==========================================

def main_keyboard():

    settings = get_settings()

    enabled = settings.get(
        "enabled",
        True
    )

    status = (
        "🟢 ON"
        if enabled
        else
        "🔴 OFF"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=f"⚙️ Bot: {status}",
                    callback_data="toggle"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🎨 Generate Post",
                    callback_data="generate"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📋 Preview",
                    callback_data="preview"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📊 Statistics",
                    callback_data="stats"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⚙️ Settings",
                    callback_data="settings"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📝 History",
                    callback_data="history"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="refresh"
                )
            ],
        ]
    )


# ==========================================
# HOME
# ==========================================

def home_text():

    settings = get_settings()

    status = (
        "🟢 RUNNING"
        if settings.get("enabled")
        else "🔴 STOPPED"
    )

    history = get_history()

    return (
        "🤖 <b>AI Instagram Manager</b>\n\n"
        f"Status: {status}\n"
        f"Generated posts: {len(history)}\n"
        f"Interval: "
        f"{settings.get('interval_hours')}h\n"
        f"Daily limit: "
        f"{settings.get('daily_limit')}\n\n"
        "AI content engine is ready."
    )


@dp.message(Command("start"))
async def start_handler(
    message: Message
):

    if await reject_if_not_admin(
        message
    ):
        return

    await message.answer(
        home_text(),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@dp.message(Command("status"))
async def status_command(
    message: Message
):

    if await reject_if_not_admin(
        message
    ):
        return

    settings = get_settings()

    await message.answer(
        home_text(),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


# ==========================================
# CALLBACKS
# ==========================================

@dp.callback_query(F.data == "refresh")
async def refresh_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Not authorized.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        home_text(),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "toggle")
async def toggle_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Not authorized.",
            show_alert=True
        )
        return

    settings = get_settings()

    new_state = not settings.get(
        "enabled",
        True
    )

    update_settings(
        enabled=new_state
    )

    await callback.message.edit_text(
        home_text(),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer(
        "Enabled" if new_state else "Stopped"
    )


@dp.callback_query(F.data == "generate")
async def generate_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Not authorized.",
            show_alert=True
        )
        return

    await callback.answer(
        "Generating..."
    )

    try:

        async with state.lock:

            result = await asyncio.to_thread(
                create_content
            )

            state.last_generation = (
                datetime.now(
                    timezone.utc
                )
            )

            state.total_generated += 1
            state.last_error = None

        image = FSInputFile(
            result["image"]
        )

        await callback.message.answer_photo(
            image,
            caption=(
                "🎨 <b>Generated Post</b>\n\n"
                + result["caption"]
            ),
            parse_mode="HTML"
        )

    except Exception as exc:

        state.last_error = str(exc)

        logger.exception(
            "Manual generation failed"
        )

        await callback.message.answer(
            "❌ Generation failed:\n\n"
            + str(exc)
        )


@dp.callback_query(F.data == "preview")
async def preview_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Not authorized.",
            show_alert=True
        )
        return

    history = get_history()

    if not history:

        await callback.answer(
            "No generated posts yet.",
            show_alert=True
        )
        return

    latest = history[-1]

    await callback.message.answer(
        "📋 <b>Latest Post</b>\n\n"
        f"<b>Topic:</b> "
        f"{latest.get('topic')}\n\n"
        f"{latest.get('caption')}",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "stats")
async def stats_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Not authorized.",
            show_alert=True
        )
        return

    history = get_history()

    last = (
        history[-1]
        if history
        else None
    )

    text = (
        "📊 <b>Statistics</b>\n\n"
        f"Total generated: {len(history)}\n"
        f"Current session: "
        f"{state.total_generated}\n\n"
    )

    if last:

        text += (
            f"Last topic: "
            f"{last.get('topic')}\n"
            f"Created: "
            f"{last.get('created_at')}"
        )

    await callback.message.answer(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "history")
async def history_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Not authorized.",
            show_alert=True
        )
        return

    history = get_history()

    if not history:

        await callback.answer(
            "History empty.",
            show_alert=True
        )
        return

    latest = history[-10:]

    lines = [
        "📝 <b>Last 10 Posts</b>\n"
    ]

    for index, item in enumerate(
        reversed(latest),
        1
    ):

        lines.append(
            f"{index}. "
            f"{item.get('topic', 'Unknown')}"
        )

    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "settings")
async def settings_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Not authorized.",
            show_alert=True
        )
        return

    settings = get_settings()

    text = (
        "⚙️ <b>Settings</b>\n\n"
        f"Enabled: "
        f"{settings.get('enabled')}\n"
        f"Interval: "
        f"{settings.get('interval_hours')}h\n"
        f"Daily limit: "
        f"{settings.get('daily_limit')}\n"
        f"Telegram: "
        f"{settings.get('telegram_channel') or 'Not set'}"
    )

    await callback.message.answer(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


# ==========================================
# HTTP SERVER
# ==========================================

async def root(
    request
):

    return web.json_response({
        "service": "AI Instagram Manager",
        "status": "running"
    })


async def health(
    request
):

    return web.json_response({
        "status": "ok"
    })


async def status(
    request
):

    settings = get_settings()

    return web.json_response({
        "status": (
            "running"
            if settings.get("enabled")
            else "stopped"
        ),
        "generated": len(
            get_history()
        ),
        "last_generation": (
            state.last_generation.isoformat()
            if state.last_generation
            else None
        ),
        "last_error": state.last_error
    })


async def start_web_server():

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

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    logger.info(
        "HTTP server running on port %s",
        PORT
    )

    return runner


# ==========================================
# AUTO SCHEDULER
# ==========================================

async def scheduler():

    await asyncio.sleep(10)

    while True:

        settings = get_settings()

        if not settings.get(
            "enabled",
            True
        ):

            await asyncio.sleep(
                30
            )

            continue

        interval = max(
            1,
            int(
                settings.get(
                    "interval_hours",
                    6
                )
            )
        )

        try:

            logger.info(
                "Automatic generation started."
            )

            async with state.lock:

                result = await asyncio.to_thread(
                    create_content
                )

                state.last_generation = (
                    datetime.now(
                        timezone.utc
                    )
                )

                state.total_generated += 1
                state.last_error = None

            logger.info(
                "Generated: %s",
                result["id"]
            )

        except Exception as exc:

            state.last_error = str(
                exc
            )

            logger.exception(
                "Automatic generation failed."
            )

        await asyncio.sleep(
            interval * 3600
        )


# ==========================================
# MAIN
# ==========================================

async def main():

    logger.info(
        "Starting AI Instagram Manager..."
    )

    runner = await start_web_server()

    scheduler_task = asyncio.create_task(
        scheduler()
    )

    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    finally:

        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()

        await runner.cleanup()


if __name__ == "__main__":

    try:
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:
        pass
