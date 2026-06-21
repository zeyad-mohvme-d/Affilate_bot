"""
Telegram Poster — sends image + caption (and optionally video) to a Telegram channel.
Uses the official Bot API via python-telegram-bot.
All credentials come from config.json.
"""

import asyncio
import logging
import sys
from pathlib import Path
from telegram import Bot

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import load_config

logger = logging.getLogger(__name__)


async def _send_photo(bot, channel_id, image_path, caption):
    with open(image_path, "rb") as photo:
        await bot.send_photo(
            chat_id=channel_id,
            photo=photo,
            caption=caption,
            parse_mode="HTML",
        )


async def _send_video(bot, channel_id, video_path, caption=None):
    with open(video_path, "rb") as video:
        await bot.send_video(
            chat_id=channel_id,
            video=video,
            caption=caption,
            supports_streaming=True,
        )


async def _post_async(image_path, caption, video_path=None):
    config = load_config()
    bot_token = config["telegram"]["bot_token"]
    channel_id = config["telegram"]["channel_id"]

    bot = Bot(token=bot_token)

    await _send_photo(bot, channel_id, image_path, caption)
    logger.info("Telegram: image sent successfully.")

    if video_path:
        await _send_video(bot, channel_id, video_path)
        logger.info("Telegram: video sent successfully.")


def post(image_path, caption, video_path=None):
    """Public entry point — sends image (and optional video) to the Telegram channel."""
    try:
        asyncio.run(_post_async(image_path, caption, video_path))
    except Exception as e:
        logger.error(f"Telegram posting failed: {e}")
        raise


# ---------------------------------------------------------------------------
# Quick standalone test: python -m posters.telegram_poster
# Sends a test image to verify bot + channel are configured correctly.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import os

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    config = load_config()
    token = config["telegram"]["bot_token"]
    channel = config["telegram"]["channel_id"]

    if "PUT_" in token or "PUT_" in channel:
        print("ERROR: Fill in your real bot_token and channel_id in config.json first.")
        sys.exit(1)

    # Create a simple test image if none exists
    test_image = Path(__file__).resolve().parent.parent / "output" / "images" / "test.jpg"
    if not test_image.exists():
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (1080, 1080), color=(41, 128, 185))
            draw = ImageDraw.Draw(img)
            draw.text(
                (540, 500),
                "Telegram Bot Test",
                fill="white",
                anchor="mm",
            )
            draw.text(
                (540, 580),
                "If you see this, it works!",
                fill="white",
                anchor="mm",
            )
            test_image.parent.mkdir(parents=True, exist_ok=True)
            img.save(test_image)
            print(f"Created test image: {test_image}")
        except ImportError:
            print("ERROR: Pillow not installed. Run: pip install pillow")
            sys.exit(1)

    test_caption = (
        "🔥 <b>Test Post</b>\n"
        "📦 This is a test from the Amazon Affiliate Bot\n"
        "✅ If you see this in your channel, Telegram posting works!"
    )

    print(f"Sending test image to channel: {channel}")
    post(str(test_image), test_caption)
    print("SUCCESS — check your Telegram channel!")
