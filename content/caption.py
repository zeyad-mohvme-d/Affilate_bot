"""
Caption Builder — generates the marketing text for each product post.

Format matches the Saudi-deals-channel style:

    {product name}

    العرض الآن {price} ✅

    {bank discount line}
    {channel code line}

    {affiliate link}

The two discount lines are static text from config.json (captions.bank_discount_line
and captions.channel_code_line) — client edits these when their promo codes change.
Either line can be empty to skip it.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import load_config as _load_config

logger = logging.getLogger(__name__)

X_MAX_LEN = 275  # Hard cap a bit under X's 280 to be safe.


def build(product, platform="telegram"):
    """
    Build a marketing caption for a product.

    product dict keys used:
        name, price, affiliate_link_saudi, affiliate_link_us

    platform: "telegram", "x", or "pinterest"
        - telegram/x use Saudi affiliate link
        - pinterest uses US affiliate link
    """
    captions = _load_config().get("captions", {})
    bank_line = (captions.get("bank_discount_line") or "").strip()
    channel_line = (captions.get("channel_code_line") or "").strip()

    if platform == "pinterest":
        link = product.get("affiliate_link_us") or product.get("link", "")
    else:
        link = product.get("affiliate_link_saudi") or product.get("link", "")

    name = (product.get("name") or "").strip()
    price = (product.get("price") or "").strip()

    sections = [name, f"العرض الآن {price} ✅"]

    discount_lines = [line for line in (bank_line, channel_line) if line]
    if discount_lines:
        sections.append("\n".join(discount_lines))

    sections.append(link)

    caption = "\n\n".join(sections)

    if platform == "x" and len(caption) > X_MAX_LEN:
        caption = _trim_for_x(name, price, discount_lines, link)

    return caption


def _trim_for_x(name, price, discount_lines, link):
    """Build a shorter caption for X. Keeps the link intact and trims the name."""
    price_line = f"العرض الآن {price} ✅"
    discount_block = "\n".join(discount_lines) if discount_lines else ""

    # Fixed parts always kept: price line, discount block, link.
    fixed = "\n\n".join(part for part in (price_line, discount_block, link) if part)
    fixed_len = len(fixed) + 2  # +2 for the blank line after the name

    available = X_MAX_LEN - fixed_len
    if available <= 0:
        # No room for name at all — drop it.
        return fixed

    if len(name) > available:
        name = name[: max(0, available - 1)].rstrip() + "…"

    return f"{name}\n\n{fixed}"
