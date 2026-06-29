"""
X (Twitter) Poster — posts tweets via Playwright using saved cookies.
Two modes:
  --login   : opens a browser, you log in manually, cookies are saved.
  (default) : uses saved cookies to post a tweet automatically.

Switched from invisible_playwright to plain playwright because
invisible_playwright is incompatible with the current Chromium DevTools
protocol on GitHub-Actions runners (Browser.setDefaultViewport rejects
its `isMobile: false` parameter).
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import load_config

logger = logging.getLogger(__name__)

COOKIES_PATH = Path(__file__).resolve().parent.parent / "x_cookies.json"
DEBUG_DIR = Path(__file__).resolve().parent.parent / "output" / "debug"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)
VIEWPORT = {"width": 1280, "height": 900}


def _save_cookies(cookies):
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f)


def _load_cookies():
    if COOKIES_PATH.exists():
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


async def _new_context(playwright_obj, headless: bool):
    """Build a browser context with a realistic user agent + viewport."""
    browser = await playwright_obj.chromium.launch(headless=headless)
    context = await browser.new_context(
        viewport=VIEWPORT,
        user_agent=USER_AGENT,
        locale="en-US",
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    return browser, context


# ── Manual login mode ────────────────────────────────────────────────────

async def _manual_login_async():
    """Open a visible browser for the user to log in manually."""
    async with async_playwright() as pw:
        browser, context = await _new_context(pw, headless=False)
        page = await context.new_page()
        try:
            await page.goto("https://x.com/login", timeout=120000)

            print("\n" + "=" * 60)
            print("  MANUAL LOGIN")
            print("  Log in to X in the browser window that just opened.")
            print("  When you see your home feed, come back here and")
            print("  press ENTER to save cookies.")
            print("=" * 60)

            input("\n>>> Press ENTER after you've logged in... ")

            current_url = page.url.lower()
            if "login" in current_url:
                print("WARNING: URL still shows login page. Saving cookies anyway.")

            cookies = await context.cookies()
            _save_cookies(cookies)
            print(f"\nCookies saved to {COOKIES_PATH}")
            print(f"Saved {len(cookies)} cookies.")
        finally:
            await context.close()
            await browser.close()


def manual_login():
    """Public function to run manual login."""
    asyncio.run(_manual_login_async())


# ── Automated posting ────────────────────────────────────────────────────

async def _compose_and_post(page, caption):
    """Compose a tweet and post it."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    await page.goto("https://x.com/compose/post", timeout=60000)
    await page.wait_for_timeout(5000)

    await page.screenshot(path=str(DEBUG_DIR / "x_compose.png"))
    logger.info(f"X: compose page. URL: {page.url}")

    if "login" in page.url.lower():
        raise RuntimeError(
            "X session expired. Run 'python -m posters.x_poster --login' to log in again."
        )

    # Try multiple selectors for the compose textarea
    compose = page.locator(
        '[data-testid="tweetTextarea_0"], '
        'div[role="textbox"][contenteditable="true"], '
        'div[aria-label*="Post text" i], '
        'div[aria-label*="happening" i]'
    )
    await compose.first.wait_for(timeout=20000)
    await compose.first.click()
    await page.wait_for_timeout(1000)

    await page.keyboard.type(caption, delay=30)
    await page.wait_for_timeout(2000)

    await page.screenshot(path=str(DEBUG_DIR / "x_before_post.png"))

    # Submit via keyboard shortcut (Ctrl+Enter) — more reliable than clicking
    await page.keyboard.press("Control+Enter")
    await page.wait_for_timeout(5000)

    await page.screenshot(path=str(DEBUG_DIR / "x_after_post.png"))
    logger.info("X: tweet posted successfully.")


async def _post_async(caption, headed=False):
    saved_cookies = _load_cookies()
    if not saved_cookies:
        raise RuntimeError(
            "No saved cookies found. Run 'python -m posters.x_poster --login' first."
        )

    async with async_playwright() as pw:
        browser, context = await _new_context(pw, headless=not headed)
        try:
            await context.add_cookies(saved_cookies)
            logger.info("X: loaded saved cookies.")

            page = await context.new_page()
            await _compose_and_post(page, caption)

            # Refresh saved cookies in case X rotated any.
            cookies = await context.cookies()
            _save_cookies(cookies)
        finally:
            await context.close()
            await browser.close()


def post(caption, headed=False):
    """Post a tweet using saved cookies."""
    try:
        asyncio.run(_post_async(caption, headed=headed))
    except Exception as e:
        logger.error(f"X posting failed: {e}")
        raise


# ── Standalone test ───────────────────────────────────────────────────────

if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if "--login" in sys.argv:
        print("Opening browser for manual X login...")
        manual_login()
        print("\nDone! Now you can post with: python -m posters.x_poster")
        sys.exit(0)

    test_caption = (
        "Test post from Amazon Affiliate Bot\n\n"
        "https://www.amazon.sa/dp/B0FW57V6M4?tag=tikshoping01-21"
    )

    headed = "--headed" in sys.argv

    print("Posting test tweet...")
    post(test_caption, headed=headed)
    print("SUCCESS — check your X account!")
