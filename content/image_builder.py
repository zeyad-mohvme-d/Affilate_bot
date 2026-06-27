"""
Image handler — downloads the raw Amazon product image and saves it to disk.

Previously this built a branded 1080x1080 card (price, CTA, watermark, etc.).
Replaced with a plain downloader to match the deals-channel aesthetic:
just the original product photo, no overlays.

Public interface unchanged: build(product) -> path string.
"""

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "images"


def build(product):
    """Download the product image from Amazon, save to disk, return the path."""
    asin = product.get("asin", "unknown")
    url = product.get("image_url")
    if not url:
        raise ValueError(f"Product {asin} has no image_url")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{asin}.jpg"

    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    path.write_bytes(resp.content)

    logger.info(f"Image downloaded: {path}")
    return str(path)
