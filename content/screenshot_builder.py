"""
Screenshot Builder — captures the top section of an Amazon product page
as the post image. Replaces the raw thumbnail with a richer visual that
includes product photo + name + price + rating + Prime badge — the
"natural Amazon product card" look.

Uses invisible_playwright (anti-detection wrapper) to reduce the chance
of Amazon serving us the "continue shopping" verification interstitial.
Raises RuntimeError if Amazon serves a verification/captcha page, so the
caller can fall back to the raw product image.
"""

import asyncio
import logging
from pathlib import Path

from invisible_playwright.async_api import InvisiblePlaywright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "images"

# Selectors for the main product detail block on amazon.sa pages.
# Tried in order — first one that exists is screenshotted.
PRODUCT_BLOCK_SELECTORS = [
    "#dp-container",
    "#ppd",
    "#dp",
    "#centerCol",
]

# Markers that signal Amazon served the verification "continue shopping"
# interstitial or a captcha page instead of the real product page.
VERIFICATION_MARKERS_AR = [
    "تابع التسوق",
    "متابعة التسوق",
    "انقر فوق الزر أدناه",
]
VERIFICATION_MARKERS_EN = [
    "continue shopping",
    "click the button below",
    "type the characters",
    "robot check",
    "enter the characters you see",
]
VERIFICATION_URL_MARKERS = [
    "/errors/validateCaptcha",
    "/ap/cvf/",
    "/ax/claim/",
]


async def _is_verification_page(page) -> bool:
    """Return True if the current page is Amazon's bot-check interstitial."""
    url = (page.url or "").lower()
    if any(marker in url for marker in VERIFICATION_URL_MARKERS):
        return True

    # Real product pages always have #productTitle. If it's missing, look for
    # textual markers of the verification page.
    if await page.locator("#productTitle").count() > 0:
        return False

    try:
        body_text = (await page.locator("body").inner_text(timeout=3000)).lower()
    except Exception:
        return False

    if any(marker.lower() in body_text for marker in VERIFICATION_MARKERS_AR):
        return True
    if any(marker in body_text for marker in VERIFICATION_MARKERS_EN):
        return True
    return False


async def _capture_async(product_url: str, dest: Path) -> str:
    """Take the screenshot and return the full product title from the
    detail page (empty string if not found). Raises RuntimeError if Amazon
    serves a verification page."""
    async with InvisiblePlaywright(headless=True) as browser:
        page = await browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2500)

            # Reject the verification interstitial immediately — let the
            # caller fall back to raw image rather than post junk.
            if await _is_verification_page(page):
                logger.warning(f"Amazon verification page detected at {page.url}")
                raise RuntimeError("Amazon served verification page instead of product")

            # Wait for any of the product blocks to render.
            try:
                await page.wait_for_selector(
                    ", ".join(PRODUCT_BLOCK_SELECTORS),
                    timeout=15000,
                )
            except PlaywrightTimeoutError:
                # Double-check: maybe Amazon swapped in verification after
                # initial load. If so, raise so the caller can fall back.
                if await _is_verification_page(page):
                    raise RuntimeError("Amazon served verification page (late)")
                logger.warning("Product block selectors not found — capturing viewport.")
                await page.screenshot(path=str(dest), full_page=False)
                return ""

            # Grab the canonical full product title.
            full_title = ""
            title_locator = page.locator("#productTitle").first
            if await title_locator.count() > 0:
                try:
                    full_title = (await title_locator.inner_text(timeout=3000)).strip()
                except Exception:
                    full_title = ""

            # Find the first selector that actually has a visible element.
            block = None
            for selector in PRODUCT_BLOCK_SELECTORS:
                candidate = page.locator(selector).first
                if await candidate.count() > 0:
                    block = candidate
                    break

            if block is None:
                logger.warning("No product block matched — capturing viewport.")
                await page.screenshot(path=str(dest), full_page=False)
                return full_title

            await block.screenshot(path=str(dest))
            logger.info(f"Screenshot saved: {dest}")
            return full_title
        finally:
            pass


def build(product) -> Path:
    """Screenshot the Amazon product page. Returns the saved file path.

    Side effect: if the detail page exposes a fuller product title than what
    the search-result scraper captured, the product dict's `name` field is
    updated in place so downstream captions use the better title.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUTPUT_DIR / f"{product['asin']}.png"

    product_url = (
        product.get("link")
        or product.get("affiliate_link_saudi")
        or product.get("affiliate_link_us")
    )
    if not product_url:
        raise RuntimeError(f"Product {product['asin']} has no URL to screenshot")

    full_title = asyncio.run(_capture_async(product_url, dest))

    if full_title and len(full_title) > len(product.get("name", "")):
        logger.info(f"Updated product name from detail page: {full_title[:60]}…")
        product["name"] = full_title

    return dest
