import asyncio
import os
import traceback

from aiohttp import (
    web,
)

from aiogram import (
    Bot,
    Dispatcher,
    F,
)
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import (
    BOT_TOKEN,
    ADMIN_ID,
    PORT,
    PUBLIC_BASE_URL,
    TELEGRAM_CHANNEL,
    POST_INTERVAL_HOURS,
    DAILY_POST_LIMIT,
)

from ai import generate_post
from instagram import (
    verify_connection,
)
from scheduler import Scheduler

from storage import (
    get_settings,
    update_settings,
    get_history,
    posts_today,
)


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is missing."
    )

if not ADMIN_ID:
    raise RuntimeError(
        "ADMIN_ID is missing."
    )

if not PUBLIC_BASE_URL:
    raise RuntimeError(
        "PUBLIC_BASE_URL is missing."
    )


bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


scheduler = Scheduler(
    base_url=PUBLIC_BASE_URL,
    telegram_bot=bot,
    admin_id=ADMIN_ID,
)


def admin_only(user_id):
    return int(user_id) == int(
        ADMIN_ID
    )


def main_keyboard():
    settings = get_settings()

    enabled = settings.get(
        "enabled",
        False,
    )

    status_text = (
        "🟢 Bot ON"
        if enabled
        else "🔴 Bot OFF"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=status_text,
                    callback_data="toggle",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🤖 Generate & Publish",
                    callback_data="publish",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👀 Generate Preview",
                    callback_data="preview",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Statistics",
                    callback_data="stats",
                ),
                InlineKeyboardButton(
                    text="⚙️ Settings",
                    callback_data="settings",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📜 History",
                    callback_data="history",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Check Instagram",
                    callback_data="instagram",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="refresh",
                ),
            ],
        ]
    )


def settings_text():
    settings = get_settings()

    return (
        "⚙️ <b>Settings</b>\n\n"
        f"Status: "
        f"{'ON' if settings['enabled'] else 'OFF'}\n"
        f"Interval: "
        f"{settings['interval_hours']} hours\n"
        f"Daily limit: "
        f"{settings['daily_limit']}\n"
        f"Telegram: "
        f"{settings['telegram_channel'] or TELEGRAM_CHANNEL}\n"
        f"Style: "
        f"{settings['content_style']}"
    )


@dp.message(Command("start"))
async def start(
    message: Message,
):
    if not admin_only(
        message.from_user.id
    ):
        await message.answer(
            "⛔ Only admin can access this bot."
        )
        return

    await message.answer(
        "🚀 <b>AI Instagram Publisher</b>\n\n"
        "AI content generation + "
        "automatic Instagram publishing.",
        reply_markup=main_keyboard(),
        parse_mode="HTML",
    )


@dp.message(Command("status"))
async def status_command(
    message: Message,
):
    if not admin_only(
        message.from_user.id
    ):
        await message.answer(
            "⛔ Only admin can access this bot."
        )
        return

    settings = get_settings()

    await message.answer(
        settings_text(),
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@dp.callback_query()
async def callbacks(
    callback: CallbackQuery,
):
    if not admin_only(
        callback.from_user.id
    ):
        await callback.answer(
            "Only admin can access this bot.",
            show_alert=True,
        )
        return

    data = callback.data

    await callback.answer()

    if data == "toggle":

        settings = get_settings()

        new_value = not bool(
            settings.get(
                "enabled",
                False,
            )
        )

        update_settings(
            enabled=new_value
        )

        text = (
            "🟢 Automatic publishing ENABLED."
            if new_value
            else "🔴 Automatic publishing DISABLED."
        )

        await callback.message.edit_text(
            text,
            reply_markup=main_keyboard(),
        )

    elif data == "publish":

        await callback.message.edit_text(
            "⏳ Generating and publishing...",
        )

        result = (
            await scheduler.generate_and_publish(
                reason="manual"
            )
        )

        if result.get("ok"):
            await callback.message.answer(
                "✅ Published successfully.",
                reply_markup=main_keyboard(),
            )
        else:
            await callback.message.answer(
                "❌ Publish failed:\n"
                + str(
                    result.get("reason")
                ),
                reply_markup=main_keyboard(),
            )

    elif data == "preview":

        await callback.message.edit_text(
            "⏳ Generating preview..."
        )

        try:
            post = await generate_post()

            image_path = post[
                "image"
            ]["path"]

            caption = (
                "👀 <b>AI Preview</b>\n\n"
                f"<b>{post['topic']}</b>\n\n"
                f"{post['caption']}"
            )

            await callback.message.answer_photo(
                photo=FSInputFile(
                    image_path
                ),
                caption=caption[:1024],
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )

        except Exception as e:
            await callback.message.answer(
                "❌ Preview failed:\n"
                f"{e}",
                reply_markup=main_keyboard(),
            )

    elif data == "stats":

        history = get_history()

        total = len(history)
        today = posts_today()

        successful = sum(
            1
            for item in history
            if item.get("published") is True
        )

        await callback.message.edit_text(
            "📊 <b>Statistics</b>\n\n"
            f"Total generated/published: {total}\n"
            f"Successful posts: {successful}\n"
            f"Published today: {today}",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    elif data == "settings":

        await callback.message.edit_text(
            settings_text(),
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    elif data == "history":

        history = get_history()

        if not history:
            text = "📜 No publishing history yet."
        else:
            lines = [
                "📜 <b>Recent History</b>\n"
            ]

            for item in history[:10]:

                topic = item.get(
                    "topic",
                    "Unknown",
                )

                media_id = item.get(
                    "media_id",
                    "-",
                )

                lines.append(
                    f"• {topic}\n"
                    f"  Media: {media_id}"
                )

            text = "\n".join(lines)

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    elif data == "instagram":

        await callback.message.edit_text(
            "⏳ Checking Instagram connection..."
        )

        try:
            info = await verify_connection()

            username = info.get(
                "username",
                "unknown",
            )

            await callback.message.edit_text(
                "✅ Instagram connected.\n\n"
                f"Username: @{username}",
                reply_markup=main_keyboard(),
            )

        except Exception as e:

            await callback.message.edit_text(
                "❌ Instagram connection failed.\n\n"
                f"{e}",
                reply_markup=main_keyboard(),
            )

    elif data == "refresh":

        await callback.message.edit_text(
            "🚀 <b>AI Instagram Publisher</b>\n\n"
            "Panel refreshed.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )


async def root(
    request,
):
    return web.json_response({
        "ok": True,
        "service": "instagram-ai-publisher",
        "status": "running",
    })


async def health(
    request,
):
    return web.json_response({
        "ok": True,
        "status": "healthy",
    })


async def status_api(
    request,
):
    settings = get_settings()

    return web.json_response({
        "ok": True,
        "enabled": settings.get(
            "enabled",
            False,
        ),
        "interval_hours": settings.get(
            "interval_hours",
            6,
        ),
        "daily_limit": settings.get(
            "daily_limit",
            3,
        ),
        "posts_today": posts_today(),
    })


async def media(
    request,
):
    filename = request.match_info[
        "filename"
    ]

    # Prevent directory traversal
    filename = os.path.basename(
        filename
    )

    path = os.path.join(
        "data",
        "media",
        filename,
    )

    if not os.path.isfile(path):
        raise web.HTTPNotFound()

    return web.FileResponse(
        path
    )


async def start_web_server():
    app = web.Application()

    app.router.add_get(
        "/",
        root,
    )

    app.router.add_get(
        "/health",
        health,
    )

    app.router.add_get(
        "/status",
        status_api,
    )

    app.router.add_get(
        "/media/{filename}",
        media,
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    print(
        f"Web server running on "
        f"0.0.0.0:{PORT}"
    )


async def main():

    await start_web_server()

    scheduler_task = asyncio.create_task(
        scheduler.run()
    )

    try:

        print(
            "Telegram bot starting..."
        )

        await dp.start_polling(
            bot
        )

    finally:

        scheduler.running = False

        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(
            main()
        )
    except KeyboardInterrupt:
        pass
