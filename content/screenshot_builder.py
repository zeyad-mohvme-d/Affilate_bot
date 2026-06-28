"""
Screenshot Builder — captures the top section of an Amazon product page
as the post image. Replaces the raw thumbnail with a richer visual that
includes product photo + name + price + rating + Prime badge — the
"natural Amazon product card" look.

Uses Playwright (already a project dependency).
"""

import asyncio
import logging
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

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


async def _capture_async(product_url: str, dest: Path) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="ar-SA",
            timezone_id="Asia/Riyadh",
            viewport={"width": 1280, "height": 1600},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "ar-SA,ar;q=0.9,en;q=0.6"},
        )
        page = await context.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=45000)

            # Wait for any of the product blocks to render.
            try:
                await page.wait_for_selector(
                    ", ".join(PRODUCT_BLOCK_SELECTORS),
                    timeout=15000,
                )
            except PlaywrightTimeoutError:
                logger.warning("Product block selectors not found — capturing viewport.")
                await page.screenshot(path=str(dest), full_page=False)
                return

            # Let lazy-loaded images settle.
            await page.wait_for_timeout(2500)

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
                return

            await block.screenshot(path=str(dest))
            logger.info(f"Screenshot saved: {dest}")
        finally:
            await context.close()
            await browser.close()


def build(product) -> Path:
    """Screenshot the Amazon product page. Returns the saved file path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUTPUT_DIR / f"{product['asin']}.png"

    product_url = (
        product.get("link")
        or product.get("affiliate_link_saudi")
        or product.get("affiliate_link_us")
    )
    if not product_url:
        raise RuntimeError(f"Product {product['asin']} has no URL to screenshot")

    asyncio.run(_capture_async(product_url, dest))
    return dest
