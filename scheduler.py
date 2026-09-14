import asyncio
import traceback
from datetime import datetime, timezone

from ai import generate_post
from instagram import publish_image
from storage import (
    add_history,
    can_post_today,
    get_settings,
    mark_last_post,
)


class Scheduler:
    def __init__(
        self,
        base_url: str,
        telegram_bot,
        admin_id: int,
    ):
        self.base_url = base_url.rstrip("/")
        self.bot = telegram_bot
        self.admin_id = admin_id

        self.running = True
        self.lock = asyncio.Lock()

    async def generate_and_publish(
        self,
        reason="manual",
    ):
        async with self.lock:

            try:
                settings = get_settings()

                if (
                    reason == "scheduled"
                    and not settings.get(
                        "enabled",
                        False,
                    )
                ):
                    return {
                        "ok": False,
                        "reason": "disabled",
                    }

                if not can_post_today():
                    message = (
                        "⚠️ Daily post limit reached."
                    )

                    await self.notify_admin(
                        message
                    )

                    return {
                        "ok": False,
                        "reason": "daily_limit",
                    }

                await self.notify_admin(
                    "🤖 Generating AI post..."
                )

                post = await generate_post()

                image_filename = (
                    post["image"]["filename"]
                )

                image_url = (
                    f"{self.base_url}"
                    f"/media/{image_filename}"
                )

                await self.notify_admin(
                    "🖼 AI image generated.\n"
                    "📤 Publishing to Instagram..."
                )

                result = await publish_image(
                    image_url=image_url,
                    caption=post["caption"],
                )

                now = datetime.now(
                    timezone.utc
                ).isoformat()

                add_history({
                    "created_at": now,
                    "topic": post["topic"],
                    "caption": post["caption"],
                    "image": image_filename,
                    "content_hash": post[
                        "content_hash"
                    ],
                    "published": True,
                    "media_id": result[
                        "media_id"
                    ],
                    "creation_id": result[
                        "creation_id"
                    ],
                    "reason": reason,
                })

                mark_last_post()

                await self.notify_admin(
                    "✅ Instagram post published!\n\n"
                    f"Topic: {post['topic']}\n"
                    f"Media ID: {result['media_id']}"
                )

                return {
                    "ok": True,
                    "post": post,
                    "result": result,
                }

            except Exception as e:
                traceback.print_exc()

                await self.notify_admin(
                    "❌ Publishing failed:\n\n"
                    f"{type(e).__name__}: {e}"
                )

                return {
                    "ok": False,
                    "reason": str(e),
                }

    async def notify_admin(
        self,
        text,
    ):
        try:
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=text,
            )
        except Exception:
            traceback.print_exc()

    async def run(self):
        await self.notify_admin(
            "🟢 AI Publisher scheduler started."
        )

        while self.running:

            try:
                settings = get_settings()

                enabled = bool(
                    settings.get(
                        "enabled",
                        False,
                    )
                )

                interval_hours = max(
                    1,
                    int(
                        settings.get(
                            "interval_hours",
                            6,
                        )
                    ),
                )

                if enabled:

                    result = (
                        await self.generate_and_publish(
                            reason="scheduled"
                        )
                    )

                    # Don't run immediately again.
                    # Always wait for the configured interval.
                    await asyncio.sleep(
                        interval_hours * 3600
                    )

                else:
                    await asyncio.sleep(30)

            except asyncio.CancelledError:
                break

            except Exception:
                traceback.print_exc()

                await asyncio.sleep(
                    60
              )
