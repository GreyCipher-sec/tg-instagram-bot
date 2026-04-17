import os
import re
import logging
import tempfile
from pathlib import Path
import asyncio

from dotenv import load_dotenv
from telegram import Update, Message
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import yt_dlp
import instaloader

load_dotenv()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
INSTAGRAM_COOKIES_FILE = os.environ.get("INSTAGRAM_COOKIES_FILE", "")

_raw_ids = os.environ.get("ALLOWED_CHAT_IDS", "")
ALLOWED_CHAT_IDS: list[int] = (
    [int(i.strip()) for i in _raw_ids.split(",") if i.strip()]
    if _raw_ids.strip()
    else []
)

MAX_FILE_BYTES = 50 * 1024 * 1024

INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/"
    r"(?:p|reel|reels|tv|stories)/[A-Za-z0-9_\-]+/?(?:\?[^\s]*)?"
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Instagram

def find_instagram_urls(text: str) -> list[str]:
    return INSTAGRAM_URL_PATTERN.findall(text)

def build_ydl_options(output_dir: str) -> dict:
    options = {
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "noplaylist": False,
    }

    cookies_exist = INSTAGRAM_COOKIES_FILE and Path(INSTAGRAM_COOKIES_FILE).exists()
    if cookies_exist:
        options["cookiefile"] = INSTAGRAM_COOKIES_FILE

    return options

def resolve_file_path(ydl: yt_dlp.YoutubeDL, entry: dict) -> Path | None:
    candidate = Path(ydl.prepare_filename(entry))
    if candidate.exists():
        return candidate

    for ext in ("mp4", "webm", "jpg", "jpeg", "png", "webp"):
        alternative = candidate.with_suffix(f".{ext}")
        if alternative.exists():
            return alternative

    return None

def is_photo_post_error(exc: Exception) -> bool:
    return "there is no video in this post" in str(exc).lower()

def download_images(url: str, output_dir: str) -> list[Path]:
    shortcode = re.search(r"/(?:p|reel)/([A-Za-z0-9_\-]+)", url)
    if not shortcode:
        return []

    loader = instaloader.Instaloader(
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        dirname_pattern=output_dir,
    )

    if INSTAGRAM_COOKIES_FILE and Path(INSTAGRAM_COOKIES_FILE).exists():
        import http.cookiejar
        jar = http.cookiejar.MozillaCookieJar(INSTAGRAM_COOKIES_FILE)
        jar.load(ignore_discard=True, ignore_expires=True)
        loader.context._session.cookies.update(jar)

    post = instaloader.Post.from_shortcode(loader.context, shortcode.group(1))
    loader.download_post(post, target=Path(output_dir))

    return sorted(Path(output_dir).glob("*.jpg"))

def download_media(url: str, output_dir: str) -> list[Path]:
    try:
        with yt_dlp.YoutubeDL(build_ydl_options(output_dir)) as ydl:
            info = ydl.extract_info(url, download=True)
            entries = info.get("entries") or [info]
            paths = [resolve_file_path(ydl, entry) for entry in entries if entry]
            result = [p for p in paths if p is not None]

            if not result:
                logger.info("yt-dlp returned no files, falling back to instaloader")
                return download_images(url, output_dir)

            return result
    except Exception as exc:
        if not is_photo_post_error(exc):
            raise

        logger.info("Photo post detected, falling back to instaloader")
        return download_images(url, output_dir)

# Telegram sending

def is_video(path: Path) -> bool:
    return path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def exceeds_telegram_limit(path: Path) -> bool:
    return path.stat().st_size > MAX_FILE_BYTES


async def send_file(message: Message, path: Path) -> None:
    if exceeds_telegram_limit(path):
        size_mb = path.stat().st_size // (1024 * 1024)
        await message.reply_text(f"⚠️ File too large ({size_mb} MB). Telegram bots are limited to 50 MB.")
        return

    with open(path, "rb") as fh:
        if is_video(path):
            await message.reply_video(video=fh, supports_streaming=True, write_timeout=120, read_timeout=120)
        elif is_image(path):
            await message.reply_photo(photo=fh)
        else:
            await message.reply_document(document=fh)


async def send_all_files(message: Message, files: list[Path]) -> None:
    for file in files:
        try:
            await send_file(message, file)
        except Exception as exc:
            logger.exception("Failed to send %s: %s", file.name, exc)
            await message.reply_text("❌ Downloaded but failed to send. Please try again.")

# Bot handler

def is_allowed_chat(chat_id: int) -> bool:
    return not ALLOWED_CHAT_IDS or chat_id in ALLOWED_CHAT_IDS


async def process_url(url: str, message: Message, tmpdir: str) -> None:
    logger.info("Processing %s in chat %s", url, message.chat_id)

    status = await message.reply_text("⏳ Fetching media from Instagram…", disable_notification=True)

    try:
        files = download_media(url, tmpdir)
    except Exception as exc:
        logger.exception("Download failed for %s: %s", url, exc)
        await status.edit_text(
            "❌ Could not download media. The post may be private or deleted.\n"
            "If this keeps happening, update yt-dlp: `pip install -U yt-dlp`"
        )
        return

    if not files:
        await status.edit_text("❌ No media found at that URL.")
        return

    await status.delete()
    await send_all_files(message, files)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not is_allowed_chat(update.effective_chat.id):
        return

    text = message.text or message.caption or ""
    urls = find_instagram_urls(text)
    if not urls:
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        for url in urls:
            await process_url(url, message, tmpdir)

# Entry point

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Bot token not found! Set TELEGRAM_BOT_TOKEN in your .env file.")

    asyncio.set_event_loop(asyncio.new_event_loop())

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
