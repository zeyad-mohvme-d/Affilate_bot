"""
main.py — Orchestrator for Amazon Affiliate Bot.

Two modes (GitHub Actions calls each separately):
  --scrape : Scrape fresh products and refill the daily queue.
  --post   : Post the next product from the queue to all 3 platforms.

Queue lives at: state/queue.json
History lives at: state/posted.json (prevents duplicates)
"""

import argparse
import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

import requests

from scraper.amazon_scraper import get_products
from content.caption import build as build_caption
from content.video_builder import build as build_video
from posters.telegram_poster import post as post_telegram
from posters.pinterest_poster import post as post_pinterest
from posters.x_poster import post as post_x
from core.config import load_config

PROJECT_DIR = Path(__file__).resolve().parent
STATE_DIR = PROJECT_DIR / "state"
QUEUE_PATH = STATE_DIR / "queue.json"
POSTED_PATH = STATE_DIR / "posted.json"
IMAGE_DIR = PROJECT_DIR / "output" / "images"


def download_product_image(product):
    """Download the raw Amazon product image and save it to disk."""
    url = product.get("image_url")
    if not url:
        raise RuntimeError(f"Product {product.get('asin')} has no image_url")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGE_DIR / f"{product['asin']}.jpg"

    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest

for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def load_json(path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Scrape mode ──────────────────────────────────────────────────────────

def run_scrape():
    """Scrape fresh products and save them to the queue."""
    config = load_config()
    products_per_day = config.get("products_per_day", 10)

    logger.info(f"Scraping {products_per_day} products from Amazon.sa...")
    products = get_products(
        limit=products_per_day * 2,
        use_categories=True,
        max_categories=5,
    )

    if not products:
        logger.error("No products scraped. Aborting.")
        sys.exit(1)

    # Filter out already-posted ASINs
    posted = load_json(POSTED_PATH, [])
    posted_asins = set(posted)
    fresh = [p for p in products if p["asin"] not in posted_asins]

    queue = fresh[:products_per_day]
    save_json(QUEUE_PATH, queue)
    logger.info(f"Queue refilled with {len(queue)} products.")


# ── Post mode ────────────────────────────────────────────────────────────

def run_post():
    """Post the next product from the queue to all 3 platforms."""
    queue = load_json(QUEUE_PATH, [])
    if not queue:
        logger.error("Queue is empty. Run --scrape first.")
        sys.exit(1)

    product = queue[0]
    logger.info(f"Posting: {product['name'][:70]}")

    # Download the raw Amazon product photo (no overlay / branding).
    try:
        image_path = download_product_image(product)
        logger.info(f"Image: {image_path}")
    except Exception:
        logger.error(f"Image download failed:\n{traceback.format_exc()}")
        sys.exit(1)

    try:
        video_path = build_video(product)
        logger.info(f"Video: {video_path}")
    except Exception:
        logger.warning(f"Video build failed (skipping video):\n{traceback.format_exc()}")
        video_path = None

    results = {}

    # Telegram
    try:
        caption = build_caption(product, platform="telegram")
        post_telegram(image_path, caption, video_path=video_path)
        results["telegram"] = "OK"
    except Exception as e:
        results["telegram"] = f"FAIL: {e}"
        logger.error(f"Telegram failed:\n{traceback.format_exc()}")

    # X
    try:
        caption = build_caption(product, platform="x")
        post_x(caption, headed=False)
        results["x"] = "OK"
    except Exception as e:
        results["x"] = f"FAIL: {e}"
        logger.error(f"X failed:\n{traceback.format_exc()}")

    # Pinterest
    try:
        caption = build_caption(product, platform="pinterest")
        post_pinterest(image_path, caption, product["affiliate_link_us"], headed=False)
        results["pinterest"] = "OK"
    except Exception as e:
        results["pinterest"] = f"FAIL: {e}"
        logger.error(f"Pinterest failed:\n{traceback.format_exc()}")

    # Mark posted only if at least one platform succeeded
    if any(v == "OK" for v in results.values()):
        queue.pop(0)
        save_json(QUEUE_PATH, queue)

        posted = load_json(POSTED_PATH, [])
        posted.append(product["asin"])
        posted = posted[-500:]  # keep last 500
        save_json(POSTED_PATH, posted)
        logger.info(f"Product marked posted. Queue size: {len(queue)}")
    else:
        logger.error("All platforms failed. Product NOT removed from queue.")

    print("\n" + "=" * 60)
    print(f"  POST SUMMARY — {datetime.utcnow().isoformat()}Z")
    print("=" * 60)
    print(f"  Product : {product['name'][:60]}")
    print(f"  ASIN    : {product['asin']}")
    for platform, status in results.items():
        print(f"  {platform.capitalize():9s}: {status}")
    print("=" * 60)


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scrape", action="store_true", help="Refill the queue")
    parser.add_argument("--post", action="store_true", help="Post next product")
    args = parser.parse_args()

    if args.scrape:
        run_scrape()
    elif args.post:
        run_post()
    else:
        parser.print_help()
        sys.exit(1)
