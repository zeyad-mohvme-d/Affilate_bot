"""
Full integration test: scrape -> caption -> image -> video -> ALL 3 platforms.
Run: python test_all_platforms.py
"""

import sys
import logging

from scraper.amazon_scraper import get_products
from content.caption import build as build_caption
from content.image_builder import build as build_image
from content.video_builder import build as build_video
from posters.telegram_poster import post as post_telegram
from posters.pinterest_poster import post as post_pinterest
from posters.x_poster import post as post_x

for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Step 1: Scrape a product
print("\n" + "=" * 60)
print("STEP 1/6: Scraping a real product from Amazon.sa")
print("=" * 60)
products = get_products(limit=1, use_categories=False)
if not products:
    print("ERROR: No products scraped.")
    sys.exit(1)
product = products[0]
print(f"   Found: {product['name'][:70]}")
print(f"   Price: {product['price']}")
print(f"   Discount: {product['has_discount']}")

# Step 2: Build image
print("\n" + "=" * 60)
print("STEP 2/6: Building product card image")
print("=" * 60)
image_path = build_image(product)
print(f"   Image saved: {image_path}")

# Step 3: Build video
print("\n" + "=" * 60)
print("STEP 3/6: Building TikTok video")
print("=" * 60)
video_path = build_video(product)
print(f"   Video saved: {video_path}")

# Step 4: Telegram
print("\n" + "=" * 60)
print("STEP 4/6: Posting to Telegram")
print("=" * 60)
try:
    caption_tg = build_caption(product, platform="telegram")
    post_telegram(image_path, caption_tg, video_path=video_path)
    print("   Telegram: SUCCESS")
except Exception as e:
    print(f"   Telegram: FAILED - {e}")

# Step 5: X
print("\n" + "=" * 60)
print("STEP 5/6: Posting to X (Twitter)")
print("=" * 60)
try:
    caption_x = build_caption(product, platform="x")
    post_x(caption_x, headed=False)
    print("   X: SUCCESS")
except Exception as e:
    print(f"   X: FAILED - {e}")

# Step 6: Pinterest
print("\n" + "=" * 60)
print("STEP 6/6: Posting to Pinterest")
print("=" * 60)
try:
    caption_pin = build_caption(product, platform="pinterest")
    affiliate_link = product["affiliate_link_us"]
    post_pinterest(image_path, caption_pin, affiliate_link, headed=False)
    print("   Pinterest: SUCCESS")
except Exception as e:
    print(f"   Pinterest: FAILED - {e}")

print("\n" + "=" * 60)
print("ALL DONE - Check Telegram, X, and Pinterest accounts!")
print("=" * 60)
