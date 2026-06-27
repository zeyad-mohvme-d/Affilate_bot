"""
Pinterest Poster — creates Pins via Playwright browser automation.
Logs in, creates a Pin with image + caption + affiliate link.
Saves cookies to avoid re-login on every run.
All credentials come from config.json.
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

COOKIES_PATH = Path(__file__).resolve().parent.parent / "pinterest_cookies.json"
DEBUG_DIR = Path(__file__).resolve().parent.parent / "output" / "debug"


def _save_cookies(cookies):
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f)


def _load_cookies():
    if COOKIES_PATH.exists():
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


async def _login(page, email, password):
    """Log in to Pinterest with email and password."""
    await page.goto("https://www.pinterest.com/login/", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(5000)

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(DEBUG_DIR / "pinterest_login_page.png"))
    logger.info(f"Pinterest: login page loaded. URL: {page.url}")

    # Enter email
    email_input = page.locator('input#email')
    await email_input.wait_for(timeout=15000)
    await email_input.click()
    await page.wait_for_timeout(300)
    await email_input.fill(email)
    await page.wait_for_timeout(500)

    # Enter password
    password_input = page.locator('input#password')
    await password_input.wait_for(timeout=10000)
    await password_input.click()
    await page.wait_for_timeout(300)
    await password_input.fill(password)
    await page.wait_for_timeout(1000)

    await page.screenshot(path=str(DEBUG_DIR / "pinterest_before_submit.png"))

    # Click Log in — try multiple selectors
    login_button = page.locator(
        'button[type="submit"], '
        'div[data-test-id="registerFormSubmitButton"] button, '
        'button:has-text("Log in")'
    )
    await login_button.first.click()
    await page.wait_for_timeout(8000)

    await page.screenshot(path=str(DEBUG_DIR / "pinterest_after_login.png"))
    logger.info(f"Pinterest: after login. URL: {page.url}")

    if "login" not in page.url.lower():
        logger.info("Pinterest: login successful.")
        return True

    # Check for error messages on page
    error_text = await page.locator('div[role="alert"], .errorMessage, .error').all_inner_texts()
    if error_text:
        logger.error(f"Pinterest login error: {error_text}")

    raise RuntimeError("Pinterest login failed. Check debug screenshots.")


async def _create_pin(page, image_path, caption, link, board_name):
    """Create a new Pin with image, caption, and destination link."""
    await page.goto("https://www.pinterest.com/pin-creation-tool/", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(5000)

    await page.screenshot(path=str(DEBUG_DIR / "pinterest_pin_creation.png"))
    logger.info(f"Pinterest: pin creation page. URL: {page.url}")

    # Upload image
    file_input = page.locator('input[type="file"]')
    await file_input.first.wait_for(timeout=15000, state="attached")
    await file_input.first.set_input_files(image_path)
    await page.wait_for_timeout(4000)
    logger.info("Pinterest: image uploaded.")

    await page.screenshot(path=str(DEBUG_DIR / "pinterest_after_upload.png"))

    # Title
    title_input = page.get_by_placeholder("Tell everyone what your Pin is about")
    if await title_input.count() == 0:
        title_input = page.get_by_placeholder("Add a title")
    if await title_input.count() > 0:
        await title_input.first.click()
        await title_input.first.fill(caption[:100])
        await page.wait_for_timeout(500)
        logger.info("Pinterest: title filled.")

    # Description
    desc_area = page.get_by_placeholder("Describe your Pin")
    if await desc_area.count() == 0:
        desc_area = page.locator('div[aria-label="Describe your Pin"]')
    if await desc_area.count() > 0:
        await desc_area.first.click()
        await page.wait_for_timeout(500)
        await page.keyboard.type(caption[:500], delay=15)
        await page.wait_for_timeout(500)
        logger.info("Pinterest: description filled.")

    # Link — "Add a link" input
    link_input = page.locator('input[placeholder="Add a link"]')
    if await link_input.count() > 0:
        await link_input.first.click()
        await link_input.first.fill(link)
        await page.wait_for_timeout(500)
        logger.info("Pinterest: link filled.")

    # Scroll down to reveal Board field
    await page.evaluate("window.scrollBy(0, 500)")
    await page.wait_for_timeout(1500)

    await page.screenshot(path=str(DEBUG_DIR / "pinterest_scrolled.png"))

    # Board — find and click the dropdown
    # The Board section contains "Choose a board" or "Board" text with a dropdown arrow
    board_clicked = False
    for selector in [
        'button:has-text("Choose a board")',
        '[data-test-id="board-dropdown-select-button"]',
        'div[aria-label="Board"] >> visible=true',
    ]:
        el = page.locator(selector)
        if await el.count() > 0:
            try:
                await el.first.click(timeout=5000)
                board_clicked = True
                break
            except Exception:
                continue

    if not board_clicked:
        # Fallback: use JavaScript to find and click the Board dropdown
        await page.evaluate("""
            const allDivs = document.querySelectorAll('div, button, span');
            for (const el of allDivs) {
                if (el.textContent.trim() === 'Choose a board') {
                    el.click();
                    break;
                }
            }
        """)
        board_clicked = True

    await page.wait_for_timeout(2000)
    await page.screenshot(path=str(DEBUG_DIR / "pinterest_board_dropdown.png"))
    logger.info("Pinterest: board dropdown opened.")

    # Look for existing board
    board_option = page.get_by_text(board_name, exact=True)
    if await board_option.count() > 0:
        await board_option.first.click()
        logger.info(f"Pinterest: selected board '{board_name}'.")
    else:
        # Create new board
        create_board = page.get_by_text("Create board")
        if await create_board.count() > 0:
            await create_board.first.click()
            await page.wait_for_timeout(1500)

            await page.screenshot(path=str(DEBUG_DIR / "pinterest_create_board.png"))

            # Fill board name
            board_input = page.locator('input[type="text"]:visible')
            await board_input.first.fill(board_name)
            await page.wait_for_timeout(500)

            create_btn = page.get_by_role("button", name="Create")
            await create_btn.first.click()
            await page.wait_for_timeout(2000)
            logger.info(f"Pinterest: created board '{board_name}'.")

    await page.wait_for_timeout(1000)

    await page.screenshot(path=str(DEBUG_DIR / "pinterest_before_publish.png"))

    # Click Publish — exact match avoids picking "Publish at scheduled time" etc.
    # Pinterest's button stays disabled until board is selected + form valid; wait for it.
    publish_button = page.get_by_role("button", name="Publish", exact=True).first
    try:
        await publish_button.wait_for(state="visible", timeout=15000)
        # Poll for the button to become enabled (Playwright's click auto-waits but
        # Pinterest keeps the button in DOM as disabled until validation passes).
        for _ in range(40):
            if await publish_button.is_enabled():
                break
            await page.wait_for_timeout(500)
        await publish_button.click(timeout=10000)
    except Exception as e:
        logger.error(f"Pinterest: publish button click failed: {e}")
        await page.screenshot(path=str(DEBUG_DIR / "pinterest_publish_failed.png"))
        raise

    # Wait for navigation away from the pin creation page — this confirms the
    # pin was actually published (not just saved as draft).
    try:
        await page.wait_for_url(
            lambda url: "/pin-creation-tool" not in url,
            timeout=30000,
        )
    except Exception:
        await page.screenshot(path=str(DEBUG_DIR / "pinterest_publish_no_nav.png"))
        current_url = page.url
        raise RuntimeError(
            f"Pinterest: publish click did not navigate away from creation page. "
            f"URL is still {current_url} — pin likely saved as draft."
        )

    await page.wait_for_timeout(2000)
    await page.screenshot(path=str(DEBUG_DIR / "pinterest_after_publish.png"))
    logger.info(f"Pinterest: pin published successfully. URL: {page.url}")


async def _post_async(image_path, caption, link, headed=False):
    config = load_config()
    p_config = config["pinterest"]
    email = p_config["email"]
    password = p_config["password"]
    board_name = p_config.get("default_board", "Deals")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not headed)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
        )

        # Load saved cookies
        saved_cookies = _load_cookies()
        if saved_cookies:
            await context.add_cookies(saved_cookies)
            logger.info("Pinterest: loaded saved cookies.")

        page = await context.new_page()

        try:
            needs_login = True

            if saved_cookies:
                await page.goto("https://www.pinterest.com/", wait_until="commit", timeout=60000)
                await page.wait_for_timeout(4000)
                if "login" not in page.url.lower():
                    needs_login = False
                    logger.info("Pinterest: already logged in via cookies.")

            if needs_login:
                logger.info("Pinterest: logging in...")
                await _login(page, email, password)
                cookies = await context.cookies()
                _save_cookies(cookies)
                logger.info("Pinterest: cookies saved.")

            await _create_pin(page, image_path, caption, link, board_name)

        finally:
            await context.close()
            await browser.close()


def post(image_path, caption, link, headed=False):
    """Create a Pin with image, caption, and affiliate link."""
    try:
        asyncio.run(_post_async(image_path, caption, link, headed=headed))
    except Exception as e:
        logger.error(f"Pinterest posting failed: {e}")
        raise


# ── Standalone test ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    config = load_config()
    p = config["pinterest"]

    if "PUT_" in p.get("email", "PUT_"):
        print("ERROR: Fill in your Pinterest email and password in config.json first.")
        sys.exit(1)

    # Build a test image
    test_image = Path(__file__).resolve().parent.parent / "output" / "images" / "test.jpg"
    if not test_image.exists():
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1080, 1080), color=(41, 128, 185))
        draw = ImageDraw.Draw(img)
        draw.text((540, 500), "Pinterest Test", fill="white", anchor="mm")
        test_image.parent.mkdir(parents=True, exist_ok=True)
        img.save(test_image)

    test_caption = "Amazing Deal - Test Pin from Amazon Affiliate Bot"
    test_link = "https://www.amazon.sa/dp/B0FW57V6M4?tag=electron039ae-20"

    headed = "--headed" in sys.argv

    print("Posting test pin to Pinterest...")
    if headed:
        print("(Visible browser mode)")
    post(str(test_image), test_caption, test_link, headed=headed)
    print("SUCCESS — check your Pinterest account!")
