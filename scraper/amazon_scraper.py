"""
Amazon Scraper — scrapes products from Amazon.com search pages using Playwright.
Reads settings from config.json. Adds the US affiliate tag. Detects discounts.
"""

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse, parse_qs, urlencode
from urllib.request import Request, urlopen

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))
from core.config import load_config

logger = logging.getLogger(__name__)

BASE_URL = "https://www.amazon.com"
CATEGORIES_PATH = PROJECT_DIR / "scraper" / "categories.json"
OUTPUT_DIR = PROJECT_DIR / "output"

RESULT_CARD_SELECTOR = (
    '.s-result-item[data-asin], [data-component-type="s-search-result"][data-asin]'
)


# ── Helpers ───────────────────────────────────────────────────────────────

def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def safe_filename(value: str, fallback: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")[:70]
    return value or fallback


def amazon_search_url(query: str) -> str:
    return f"{BASE_URL}/s?k={quote_plus(query)}"


def build_affiliate_link(product_url: str, tag: str) -> str:
    """Build a clean short affiliate link: amazon.com/dp/ASIN?tag=..."""
    parsed = urlparse(product_url)

    asin_match = re.search(r"/dp/([A-Z0-9]{10})", parsed.path)
    if asin_match:
        asin = asin_match.group(1)
        return f"https://{parsed.netloc}/dp/{asin}?tag={tag}"

    return f"https://{parsed.netloc}{parsed.path}?tag={tag}"


# ── Categories ────────────────────────────────────────────────────────────

def load_category_targets(categories_file: Path = CATEGORIES_PATH) -> list[dict[str, str]]:
    data = json.loads(categories_file.read_text(encoding="utf-8"))
    targets: list[dict[str, str]] = []

    for group in data.get("groups", []):
        group_id = clean_text(group.get("id"))
        group_name = clean_text(group.get("name"))
        for category in group.get("categories", []):
            category_name = clean_text(category.get("name"))
            query = clean_text(category.get("query") or category_name)
            if not category_name or not query:
                continue
            targets.append(
                {
                    "group_id": group_id,
                    "group_name": group_name,
                    "category": category_name,
                    "query": query,
                    "url": clean_text(category.get("url")) or amazon_search_url(query),
                }
            )

    if not targets:
        raise RuntimeError(f"No categories found in {categories_file}")

    return targets


# ── Anti-bot detection ────────────────────────────────────────────────────

def is_robot_or_captcha_page(text: str, title: str) -> bool:
    haystack = f"{title}\n{text}".lower()
    markers = [
        "robot check",
        "captcha",
        "enter the characters you see below",
        "sorry, we just need to make sure you're not a robot",
    ]
    return any(marker in haystack for marker in markers)


# ── Page interaction ──────────────────────────────────────────────────────

async def slow_scroll(page: Any) -> None:
    for _ in range(4):
        await page.mouse.wheel(0, 900)
        await page.wait_for_timeout(900)
    await page.mouse.wheel(0, -3600)
    await page.wait_for_timeout(700)


# ── Product extraction ────────────────────────────────────────────────────

async def extract_products(page: Any, limit: int) -> tuple[list[dict], list[str]]:
    cards = page.locator(RESULT_CARD_SELECTOR)
    count = await cards.count()
    products: list[dict] = []
    seen_asins: set[str] = set()
    skipped: list[str] = []

    for index in range(count):
        if len(products) >= limit:
            break

        card = cards.nth(index)
        item = await card.evaluate(
            """
            (node) => {
                const clean = (value) => (value || "").trim().replace(/\\s+/g, " ");
                const text = (selector) => {
                    const el = node.querySelector(selector);
                    return el ? clean(el.textContent) : "";
                };
                const attr = (selector, name) => {
                    const el = node.querySelector(selector);
                    return el ? clean(el.getAttribute(name)) : "";
                };
                const first = (selectors, mapper) => {
                    for (const selector of selectors) {
                        const el = node.querySelector(selector);
                        if (!el) continue;
                        const value = clean(mapper(el));
                        if (value) return value;
                    }
                    return "";
                };
                const firstSrcFromSrcset = (srcset) => {
                    if (!srcset) return "";
                    const firstCandidate = srcset.split(",")[0] || "";
                    return clean(firstCandidate.trim().split(/\\s+/)[0]);
                };
                const imageFrom = (el) => {
                    const src =
                        el.currentSrc ||
                        el.getAttribute("src") ||
                        el.getAttribute("data-src") ||
                        firstSrcFromSrcset(el.getAttribute("srcset")) ||
                        firstSrcFromSrcset(el.getAttribute("data-srcset"));
                    return src && !src.startsWith("data:") ? src : "";
                };

                const title = first(
                    [
                        "[data-cy='title-recipe'] h2 span",
                        "h2 a span",
                        "h2 span",
                        "a.a-link-normal span.a-text-normal",
                        ".a-size-medium.a-color-base.a-text-normal",
                        ".a-size-base-plus.a-color-base.a-text-normal"
                    ],
                    (el) => el.innerText || el.textContent
                ) || attr("img.s-image", "alt") || attr("img", "alt");

                const href = first(
                    [
                        "a.a-link-normal.s-no-outline",
                        "h2 a.a-link-normal",
                        "a[href*='/dp/']",
                        "a[href*='/gp/aw/d/']",
                        "a.a-link-normal"
                    ],
                    (el) => el.getAttribute("href")
                );

                const image = first(
                    [
                        "img.s-image",
                        "img[data-image-latency]",
                        "img[data-src]",
                        "img"
                    ],
                    imageFrom
                );

                // Current price
                const price =
                    text(".a-price .a-offscreen") ||
                    text("[data-a-color='base'] .a-offscreen") ||
                    text(".a-price-whole") ||
                    text(".a-color-price");

                // Original price (before discount) — strikethrough price
                const oldPrice =
                    text(".a-price[data-a-strike='true'] .a-offscreen") ||
                    text("span.a-price.a-text-price .a-offscreen") ||
                    text(".a-text-price .a-offscreen") ||
                    "";

                return {
                    asin: node.getAttribute("data-asin") || "",
                    title,
                    price,
                    old_price: oldPrice,
                    link: href,
                    image_url: image
                };
            }
            """
        )

        asin = clean_text(item.get("asin"))
        title = clean_text(item.get("title"))
        link = clean_text(item.get("link"))
        image_url = clean_text(item.get("image_url"))
        price = clean_text(item.get("price")) or "Price not shown"
        old_price = clean_text(item.get("old_price"))

        missing = [
            field
            for field, value in {
                "asin": asin,
                "title": title,
                "link": link,
                "image_url": image_url,
            }.items()
            if not value
        ]
        if asin and asin in seen_asins:
            skipped.append(f"card {index + 1}: duplicate ASIN {asin}")
            continue
        if missing:
            skipped.append(f"card {index + 1}: missing {', '.join(missing)}")
            continue

        has_discount = bool(old_price and old_price != price)

        seen_asins.add(asin)
        products.append(
            {
                "asin": asin,
                "name": title,
                "price": price,
                "old_price": old_price if has_discount else "",
                "has_discount": has_discount,
                "link": urljoin(BASE_URL, link),
                "image_url": image_url,
                "group_id": "",
                "group_name": "",
                "category": "",
                "query": "",
                "source_url": "",
            }
        )

    return products, skipped


# ── Debug ─────────────────────────────────────────────────────────────────

async def save_debug_artifacts(
    page: Any,
    reason: str,
    skipped: list[str] | None = None,
) -> None:
    debug_dir = OUTPUT_DIR / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    html_path = debug_dir / "amazon_debug.html"
    screenshot_path = debug_dir / "amazon_debug.png"
    report_path = debug_dir / "amazon_debug_report.txt"

    html_path.write_text(await page.content(), encoding="utf-8")
    await page.screenshot(path=str(screenshot_path), full_page=True)

    report_lines = [reason]
    if skipped:
        report_lines.append("")
        report_lines.append("Skipped cards:")
        report_lines.extend(skipped[:50])
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    logger.warning(f"Debug artifacts saved to {debug_dir}")


# ── Single page scrape ────────────────────────────────────────────────────

async def scrape_page(
    page: Any,
    target: dict[str, str],
    limit: int = 10,
    timeout: int = 30000,
) -> list[dict]:
    await page.goto(target["url"], wait_until="domcontentloaded", timeout=timeout)
    await page.wait_for_timeout(2500)

    title = await page.title()
    body_text = await page.locator("body").inner_text(timeout=5000)
    if is_robot_or_captcha_page(body_text, title):
        logger.error("Amazon returned a robot/captcha page.")
        return []

    try:
        await page.wait_for_selector(RESULT_CARD_SELECTOR, timeout=timeout)
    except PlaywrightTimeoutError:
        await save_debug_artifacts(
            page,
            f"No search result cards found for {target['category']}.",
        )
        logger.error(f"No search results found for {target['category']}.")
        return []

    await slow_scroll(page)
    products, skipped = await extract_products(page, limit)

    if not products:
        await save_debug_artifacts(
            page,
            f"No complete products extracted for {target['category']}.",
            skipped,
        )
        return []

    for product in products:
        product["group_id"] = target["group_id"]
        product["group_name"] = target["group_name"]
        product["category"] = target["category"]
        product["query"] = target["query"]
        product["source_url"] = target["url"]

    if skipped:
        logger.info(f"Skipped {len(skipped)} incomplete cards for {target['category']}")

    return products


# ── Public API (called by main.py) ────────────────────────────────────────

def get_products(
    limit: int = 10,
    use_categories: bool = True,
    max_categories: int = 0,
    headed: bool = False,
) -> list[dict]:
    """
    Scrape products from Amazon.com. Reads config.json for source_url and tag.
    Adds the US affiliate link to each product.

    Returns a list of product dicts with keys:
        asin, name, price, old_price, has_discount,
        link, affiliate_link_us,
        image_url, group_id, group_name, category, query, source_url
    """
    config = load_config()
    amazon_config = config["amazon"]
    tag_us = amazon_config["tag_us"]

    if use_categories and CATEGORIES_PATH.exists():
        targets = load_category_targets()
        if max_categories:
            targets = targets[:max_categories]
    else:
        targets = [
            {
                "group_id": "",
                "group_name": "",
                "category": "default",
                "query": "",
                "url": amazon_config["source_url"],
            }
        ]

    all_products = asyncio.run(
        _scrape_all(targets, limit=limit, headed=headed)
    )

    for product in all_products:
        product["affiliate_link_us"] = build_affiliate_link(product["link"], tag_us)

    if config.get("prioritize_discounts"):
        all_products.sort(key=lambda p: (not p["has_discount"], p["asin"]))

    return all_products


async def _scrape_all(
    targets: list[dict[str, str]],
    limit: int = 10,
    headed: bool = False,
    delay: int = 2000,
) -> list[dict]:
    all_products: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not headed)
        context = await browser.new_context(
            locale="en-US",
            timezone_id="America/New_York",
            viewport={"width": 1365, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        page = await context.new_page()

        try:
            for index, target in enumerate(targets, start=1):
                logger.info(
                    f"[{index}/{len(targets)}] Scraping {target['category']} "
                    f"({target['query']})"
                )
                products = await scrape_page(page, target, limit=limit)
                all_products.extend(products)
                if index < len(targets):
                    await page.wait_for_timeout(delay)
        finally:
            await context.close()
            await browser.close()

    return all_products


# ── Standalone test ───────────────────────────────────────────────────────

if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("Scraping 2 products from 1 category (quick test)...")
    products = get_products(limit=2, use_categories=False, headed=False)

    print(f"\nFound {len(products)} products:\n")
    for p in products:
        print(f"  [{p['asin']}] {p['name'][:60]}")
        print(f"    Price: {p['price']}")
        if p["has_discount"]:
            print(f"    Old price: {p['old_price']} (DISCOUNT)")
        print(f"    Link: {p['affiliate_link_us'][:80]}...")
        print()
