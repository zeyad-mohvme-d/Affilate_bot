"""
Caption Builder — generates marketing text for each product post.
Rotates between templates to avoid spam flags.
Reads hashtags and language from config.json.
"""

import random
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import load_config as _load_config

logger = logging.getLogger(__name__)

TEMPLATES_AR = [
    (
        "🔥 عرض اليوم\n"
        "📦 {name}\n"
        "{discount_line}"
        "💰 السعر: {price}\n\n"
        "🛒 اطلب الآن:\n{link}\n\n"
        "{hashtags}"
    ),
    (
        "⭐ منتج مميز\n"
        "📦 {name}\n"
        "{discount_line}"
        "💲 {price}\n\n"
        "🔗 للطلب:\n{link}\n\n"
        "{hashtags}"
    ),
    (
        "💎 لا تفوّت هالعرض!\n"
        "📦 {name}\n"
        "{discount_line}"
        "💰 بسعر: {price}\n\n"
        "👇 اطلبه من هنا:\n{link}\n\n"
        "{hashtags}"
    ),
    (
        "🛍️ وصل حديثاً\n"
        "📦 {name}\n"
        "{discount_line}"
        "💰 السعر: {price}\n\n"
        "🛒 احصل عليه الآن:\n{link}\n\n"
        "{hashtags}"
    ),
    (
        "✨ اختيارنا لك اليوم\n"
        "📦 {name}\n"
        "{discount_line}"
        "💲 فقط {price}\n\n"
        "🔗 رابط الشراء:\n{link}\n\n"
        "{hashtags}"
    ),
    (
        "🏷️ عرض خاص\n"
        "📦 {name}\n"
        "{discount_line}"
        "💰 السعر الحالي: {price}\n\n"
        "🛒 اشتري الآن:\n{link}\n\n"
        "{hashtags}"
    ),
    (
        "📢 توصية اليوم\n"
        "📦 {name}\n"
        "{discount_line}"
        "💲 بـ {price} بس!\n\n"
        "👇 الرابط:\n{link}\n\n"
        "{hashtags}"
    ),
    (
        "🎯 صفقة ما تتكرر\n"
        "📦 {name}\n"
        "{discount_line}"
        "💰 {price}\n\n"
        "🛒 اطلبه قبل ينتهي:\n{link}\n\n"
        "{hashtags}"
    ),
]

_last_template_index = -1


def build(product, platform="telegram"):
    """
    Build a marketing caption for a product.

    product dict keys:
        name, price, old_price, has_discount,
        affiliate_link_saudi, affiliate_link_us

    platform: "telegram", "x", or "pinterest"
        - telegram/x use Saudi affiliate link
        - pinterest uses US affiliate link
    """
    global _last_template_index

    config = _load_config()
    hashtags = config.get("captions", {}).get("hashtags", "")

    if platform == "pinterest":
        link = product.get("affiliate_link_us", product.get("link", ""))
    else:
        link = product.get("affiliate_link_saudi", product.get("link", ""))

    discount_line = ""
    if product.get("has_discount") and product.get("old_price"):
        discount_line = f"🏷️ قبل: {product['old_price']} ← خصم!\n"

    available = list(range(len(TEMPLATES_AR)))
    if _last_template_index in available and len(available) > 1:
        available.remove(_last_template_index)
    chosen = random.choice(available)
    _last_template_index = chosen

    template = TEMPLATES_AR[chosen]

    caption = template.format(
        name=product.get("name", ""),
        price=product.get("price", ""),
        discount_line=discount_line,
        link=link,
        hashtags=hashtags,
    )

    if platform == "x" and len(caption) > 270:
        caption = _trim_for_x(caption, link)

    return caption


def _trim_for_x(caption, link):
    """Trim caption to fit X's 280 char limit, keeping the link intact."""
    max_len = 275
    lines = caption.split("\n")
    result = []
    current_len = 0

    for line in lines:
        if link in line:
            result.append(line)
            current_len += len(line) + 1
            continue
        if current_len + len(line) + 1 <= max_len:
            result.append(line)
            current_len += len(line) + 1

    return "\n".join(result)


# ── Standalone test ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    sample = {
        "name": "مثقاب كهربائي لاسلكي بوش 18 فولت",
        "price": "499.00 SAR",
        "old_price": "799.00 SAR",
        "has_discount": True,
        "affiliate_link_saudi": "https://www.amazon.sa/dp/B0TEST?tag=tikshoping01-21",
        "affiliate_link_us": "https://www.amazon.sa/dp/B0TEST?tag=electron039ae-20",
    }

    print("=== 5 captions (should all be different) ===\n")
    for i in range(5):
        print(f"--- Caption {i + 1} ---")
        print(build(sample, platform="telegram"))
        print()
