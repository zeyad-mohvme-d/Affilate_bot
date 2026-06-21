"""
Video Builder — generates a ~15-second vertical video (1080x1920) for TikTok.
Product image with zoom/pan effect + text overlay (name + price).
"""

import io
import logging
import platform
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx,
)

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "videos"
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
DURATION = 15
FPS = 24

# ── Colors ────────────────────────────────────────────────────────────────
BG_COLOR = (255, 255, 255)
ACCENT_COLOR = (232, 65, 24)
TEXT_COLOR = (33, 33, 33)
PRICE_COLOR = (232, 65, 24)


# ── Font helper ───────────────────────────────────────────────────────────
BUNDLED_FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoNaskhArabic.ttf"


def _find_font(bold=False):
    """Prefers the bundled Noto Naskh Arabic; falls back to system fonts."""
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
    if not HAS_ARABIC:
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


# ── Image download ────────────────────────────────────────────────────────

def _download_image(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception as e:
        logger.warning(f"Could not download product image for video: {e}")
        return None


# ── Frame builders ────────────────────────────────────────────────────────

def _build_product_frame(product_img):
    """Build the product showcase frame (top half: image, bottom: gradient)."""
    frame = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(frame)

    # Top accent bar
    draw.rectangle([(0, 0), (VIDEO_WIDTH, 10)], fill=ACCENT_COLOR)

    if product_img:
        img = product_img.copy()
        img.thumbnail((900, 900), Image.LANCZOS)
        x = (VIDEO_WIDTH - img.width) // 2
        y = 200
        frame.paste(img, (x, y))

    return frame


def _build_info_frame(product):
    """Build the product info frame (name + price + CTA)."""
    frame = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(frame)

    # Top accent bar
    draw.rectangle([(0, 0), (VIDEO_WIDTH, 10)], fill=ACCENT_COLOR)

    name_font = _load_font(52, bold=True)
    price_font = _load_font(72, bold=True)
    cta_font = _load_font(44, bold=True)

    # Product name (centered, wrapped)
    name_text = _shape_arabic(product.get("name", ""))
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
    lines = lines[:4]

    y = 500
    for line in lines:
        draw.text((VIDEO_WIDTH // 2, y), line, fill=TEXT_COLOR,
                  font=name_font, anchor="mt")
        y += 70

    # Price
    y_price = y + 60
    if product.get("has_discount") and product.get("old_price"):
        old_font = _load_font(42)
        old_text = _shape_arabic(product["old_price"])
        draw.text((VIDEO_WIDTH // 2, y_price), old_text, fill=(180, 180, 180),
                  font=old_font, anchor="mt")
        bbox = draw.textbbox((VIDEO_WIDTH // 2, y_price), old_text,
                             font=old_font, anchor="mt")
        mid_y = (bbox[1] + bbox[3]) // 2
        draw.line([(bbox[0] - 5, mid_y), (bbox[2] + 5, mid_y)],
                  fill=(180, 180, 180), width=3)
        y_price += 60

    price_text = _shape_arabic(product.get("price", ""))
    draw.text((VIDEO_WIDTH // 2, y_price), price_text, fill=PRICE_COLOR,
              font=price_font, anchor="mt")

    # CTA button
    y_cta = y_price + 130
    btn_w, btn_h = 500, 90
    btn_x = (VIDEO_WIDTH - btn_w) // 2
    draw.rounded_rectangle(
        [(btn_x, y_cta), (btn_x + btn_w, y_cta + btn_h)],
        radius=20, fill=ACCENT_COLOR,
    )
    cta_text = _shape_arabic("اطلب الآن")
    draw.text((VIDEO_WIDTH // 2, y_cta + btn_h // 2), cta_text,
              fill=(255, 255, 255), font=cta_font, anchor="mm")

    # Bottom accent bar
    draw.rectangle([(0, VIDEO_HEIGHT - 10), (VIDEO_WIDTH, VIDEO_HEIGHT)],
                   fill=ACCENT_COLOR)

    return frame


# ── Main builder ──────────────────────────────────────────────────────────

def build(product):
    """
    Build a ~15-second vertical video for TikTok.

    Returns the path to the saved MP4.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    product_img = _download_image(product.get("image_url", ""))

    # Frame 1: Product image showcase (0-8 seconds, with slow zoom)
    frame1_pil = _build_product_frame(product_img)
    frame1_clip = (
        ImageClip(np.array(frame1_pil))
        .with_duration(8)
        .resized(lambda t: 1 + 0.05 * (t / 8))
    )

    # Frame 2: Product info (8-15 seconds, with fade in)
    frame2_pil = _build_info_frame(product)
    frame2_clip = (
        ImageClip(np.array(frame2_pil))
        .with_duration(7)
        .with_effects([vfx.CrossFadeIn(1.0)])
    )

    # Combine
    video = concatenate_videoclips([frame1_clip, frame2_clip], method="compose")

    # Crop to exact dimensions (zoom may overshoot)
    video = video.cropped(
        x_center=VIDEO_WIDTH // 2,
        y_center=VIDEO_HEIGHT // 2,
        width=VIDEO_WIDTH,
        height=VIDEO_HEIGHT,
    )

    asin = product.get("asin", "unknown")
    out_path = OUTPUT_DIR / f"{asin}.mp4"

    video.write_videofile(
        str(out_path),
        fps=FPS,
        codec="libx264",
        audio=False,
        logger=None,
    )

    logger.info(f"Video built: {out_path}")
    return str(out_path)


# ── Standalone test ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    sample = {
        "name": "مثقاب كهربائي لاسلكي بوش 18 فولت احترافي",
        "price": "499.00 SAR",
        "old_price": "799.00 SAR",
        "has_discount": True,
        "image_url": "https://picsum.photos/600/600",
        "asin": "VIDEO_TEST",
    }

    print("Building test video...")
    path = build(sample)
    print(f"Video saved to: output/videos/{Path(path).name}")
    print("Open the file to check it.")
