"""
Full pipeline test: scrape → caption → image → video → Telegram.
Run: python test_full_pipeline.py
"""

import sys
import logging
from scraper.amazon_scraper import get_products
from content.caption import build as build_caption
from content.image_builder import build as build_image
from content.video_builder import build as build_video
from posters.telegram_poster import post

for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Step 1: Scrape
print("1. Scraping a real product from Amazon.sa...")
products = get_products(limit=1, use_categories=False)

if not products:
    print("ERROR: No products scraped. Check logs.")
    sys.exit(1)

product = products[0]
print(f"   Found: {product['name'][:60]}")
print(f"   Price: {product['price']}")
print(f"   Discount: {product['has_discount']}")

# Step 2: Build caption
print("\n2. Building caption...")
caption = build_caption(product, platform="telegram")
print(f"   Preview:\n{caption[:120]}...")

# Step 3: Build image card
print("\n3. Building product card...")
image_path = build_image(product)
print("   Done.")

# Step 4: Build video
print("\n4. Building TikTok video...")
video_path = build_video(product)
print("   Done.")

# Step 5: Send image + video to Telegram
print("\n5. Sending image + video to Telegram...")
post(image_path, caption, video_path=video_path)
print("\nSUCCESS — check your Telegram channel!")
print("You should see:")
print("  - Branded image card with Arabic caption + affiliate link")
print("  - TikTok-ready video with product showcase")
