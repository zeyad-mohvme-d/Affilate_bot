"""
Image Builder — generates a branded 1080x1080 product card.
Product photo + name + price + CTA button + watermark.
"""

import io
import logging
import platform
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "images"

# ── Colors ────────────────────────────────────────────────────────────────
BG_COLOR = (255, 255, 255)
ACCENT_COLOR = (232, 65, 24)
TEXT_COLOR = (33, 33, 33)
PRICE_COLOR = (232, 65, 24)
CTA_BG = (232, 65, 24)
CTA_TEXT = (255, 255, 255)
WATERMARK_COLOR = (180, 180, 180)
DISCOUNT_BG = (39, 174, 96)
DISCOUNT_TEXT = (255, 255, 255)


# ── Font helper ───────────────────────────────────────────────────────────
BUNDLED_FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoNaskhArabic.ttf"


def _find_font(bold=False):
    """Return a path to an Arabic-capable font. Prefers the bundled Noto Naskh Arabic
    (works identically on Windows + Linux), falls back to system fonts."""
    candidates = [BUNDLED_FONT]
    if platform.system() == "Windows":
        base = Path("C:/Windows/Fonts")
        candidates += [
            base / ("tahomabd.ttf" if bold else "tahoma.ttf"),
            base / ("arialbd.ttf" if bold else "arial.ttf"),
        ]
    else:
        candidates += [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
                 else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold
                 else "/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
        ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _load_font(size, bold=False):
    path = _find_font(bold)
    if not path:
        return ImageFont.load_default()
    font = ImageFont.truetype(path, size)
    if bold and path == str(BUNDLED_FONT):
        try:
            font.set_variation_by_name("Bold")
        except Exception:
            pass
    return font


def _shape_arabic(text):
    """Reshape and reorder Arabic text for correct Pillow rendering."""
    if not HAS_ARABIC:
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


# ── Product image download ────────────────────────────────────────────────
def _download_image(url, size=(600, 600)):
    """Download a product image from URL. Returns a PIL Image or None."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        img.thumbnail(size, Image.LANCZOS)
        return img
    except Exception as e:
        logger.warning(f"Could not download product image: {e}")
        return None


def _make_placeholder(size=(600, 600)):
    """Draw a gray placeholder when the product image is unavailable."""
    ph = Image.new("RGBA", size, (220, 220, 220, 255))
    draw = ImageDraw.Draw(ph)
    font = _load_font(40)
    draw.text(
        (size[0] // 2, size[1] // 2),
        _shape_arabic("لا توجد صورة"),
        fill=(150, 150, 150),
        font=font,
        anchor="mm",
    )
    return ph


# ── Main builder ──────────────────────────────────────────────────────────
def build(product):
    """
    Build a 1080x1080 branded product card.

    product dict keys:
        name        — product name (str)
        price       — display price, e.g. "129.00 ر.س" (str)
        image_url   — URL of the product photo (str)
        asin        — Amazon product ID, used for filename (str)
        has_discount — whether the item is discounted (bool, optional)
        old_price   — original price before discount (str, optional)

    Returns the path to the saved image.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    card = Image.new("RGB", (1080, 1080), BG_COLOR)
    draw = ImageDraw.Draw(card)

    # ── Top accent bar ────────────────────────────────────────────────
    draw.rectangle([(0, 0), (1080, 8)], fill=ACCENT_COLOR)

    # ── Product image (centered, upper half) ──────────────────────────
    product_img = _download_image(product.get("image_url", ""))
    if product_img is None:
        product_img = _make_placeholder()

    paste_x = (1080 - product_img.width) // 2
    paste_y = 60
    if product_img.mode == "RGBA":
        card.paste(product_img, (paste_x, paste_y), product_img)
    else:
        card.paste(product_img, (paste_x, paste_y))

    # ── Discount badge (top-left) ─────────────────────────────────────
    if product.get("has_discount"):
        badge_font = _load_font(28, bold=True)
        draw.rounded_rectangle([(30, 30), (180, 80)], radius=10, fill=DISCOUNT_BG)
        draw.text((105, 55), _shape_arabic("خصم"), fill=DISCOUNT_TEXT,
                  font=badge_font, anchor="mm")

    # ── Divider line ──────────────────────────────────────────────────
    y_divider = paste_y + product_img.height + 30
    draw.line([(80, y_divider), (1000, y_divider)], fill=(230, 230, 230), width=2)

    # ── Product name ──────────────────────────────────────────────────
    name_font = _load_font(38, bold=True)
    name_text = _shape_arabic(product.get("name", "منتج"))

    # Word-wrap long names (max ~30 chars per line)
    words = name_text.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=name_font)
        if bbox[2] - bbox[0] > 900:
            if current:
                lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)
    lines = lines[:3]

    y_name = y_divider + 25
    for line in lines:
        draw.text((540, y_name), line, fill=TEXT_COLOR, font=name_font, anchor="mt")
        y_name += 50

    # ── Price ─────────────────────────────────────────────────────────
    price_font = _load_font(52, bold=True)
    y_price = y_name + 20
    price_text = _shape_arabic(product.get("price", ""))

    if product.get("old_price"):
        old_font = _load_font(34)
        old_text = _shape_arabic(product["old_price"])
        draw.text((540, y_price), old_text, fill=(180, 180, 180),
                  font=old_font, anchor="mt")
        # Strikethrough
        bbox = draw.textbbox((540, y_price), old_text, font=old_font, anchor="mt")
        mid_y = (bbox[1] + bbox[3]) // 2
        draw.line([(bbox[0] - 5, mid_y), (bbox[2] + 5, mid_y)],
                  fill=(180, 180, 180), width=2)
        y_price += 45

    draw.text((540, y_price), price_text, fill=PRICE_COLOR,
              font=price_font, anchor="mt")

    # ── CTA button ────────────────────────────────────────────────────
    cta_font = _load_font(36, bold=True)
    cta_text = _shape_arabic("اطلب الآن")
    y_cta = y_price + 90
    btn_w, btn_h = 380, 70
    btn_x = (1080 - btn_w) // 2
    draw.rounded_rectangle(
        [(btn_x, y_cta), (btn_x + btn_w, y_cta + btn_h)],
        radius=15,
        fill=CTA_BG,
    )
    draw.text((540, y_cta + btn_h // 2), cta_text, fill=CTA_TEXT,
              font=cta_font, anchor="mm")

    # ── Watermark (bottom) ────────────────────────────────────────────
    wm_font = _load_font(22)
    draw.text((540, 1045), "Amazon Affiliate Bot", fill=WATERMARK_COLOR,
              font=wm_font, anchor="mm")

    # ── Bottom accent bar ─────────────────────────────────────────────
    draw.rectangle([(0, 1072), (1080, 1080)], fill=ACCENT_COLOR)

    # ── Save ──────────────────────────────────────────────────────────
    asin = product.get("asin", "unknown")
    out_path = OUTPUT_DIR / f"{asin}.jpg"
    card.convert("RGB").save(out_path, "JPEG", quality=92)
    logger.info(f"Image built: {out_path}")
    return str(out_path)


# ── Standalone test ───────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    sample_product = {
        "name": "مثقاب كهربائي لاسلكي بوش 18 فولت احترافي",
        "price": "499.00 SAR",
        "old_price": "799.00 SAR",
        "image_url": "https://picsum.photos/600/600",
        "asin": "TEST001",
        "has_discount": True,
    }

    path = build(sample_product)
    print("Card saved to: output/images/" + Path(path).name)
    print("Open the image to verify it looks correct.")
