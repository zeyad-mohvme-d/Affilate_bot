# Amazon Affiliate Automation & Multi-Platform Publishing System

> Automated product discovery, content generation, state management, and scheduled publishing across Telegram, X, and Pinterest.

## Overview

This project automates an Amazon affiliate content workflow from product discovery to multi-platform distribution.

The system:

- Scrapes product listings from Amazon using Playwright.
- Extracts product metadata such as ASIN, title, price, image, and discount information.
- Filters duplicate products using persistent posting history.
- Maintains a daily product queue in JSON state files.
- Generates Arabic promotional captions using reusable templates.
- Builds branded square product images and short vertical videos.
- Publishes content independently to Telegram, X, and Pinterest.
- Runs automatically through GitHub Actions on a scheduled basis.
- Preserves queue state and posting history between workflow runs.

This is an automation system rather than an LLM-based application. The caption layer is template-driven and does not currently call an LLM API.

## Architecture

```text
                    ┌─────────────────────┐
                    │     GitHub Actions  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Daily Scrape Job   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Amazon Scraper    │
                    │     Playwright      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Product Queue       │
                    │   state/queue.json  │
                    └──────────┬──────────┘
                               │
                     scheduled posting
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Content Pipeline   │
                    │  • Arabic caption   │
                    │  • Product image    │
                    │  • Short video      │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
             Telegram          X         Pinterest
                 │             │             │
                 └─────────────┼─────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Posted History      │
                    │ state/posted.json   │
                    └─────────────────────┘
```

## Workflow

### 1. Product discovery

The scrape workflow runs once per day and collects fresh products from configured Amazon search categories.

The scraper validates required fields, skips duplicate ASINs, detects discount information, and generates clean affiliate URLs from product ASINs.

### 2. Queue management

Fresh products are stored in a persistent queue. Before insertion, previously posted ASINs are filtered out.

The queue decouples product discovery from publishing, so scraping and posting can run as separate scheduled jobs.

### 3. Content generation

For each queued product, the system generates:

- Arabic marketing copy using rotating templates.
- A branded 1080×1080 product image.
- A short 1080×1920 vertical video.

Platform-specific affiliate links are selected during caption generation.

### 4. Multi-platform publishing

The posting workflow processes the next queued product and attempts publication independently on:

- Telegram
- X
- Pinterest

A failed platform does not automatically prevent the system from attempting the other platforms.

The queue item is removed only when at least one publication succeeds. Otherwise, it remains available for retry.

### 5. Persistent state

Two JSON files provide lightweight state management:

- `state/queue.json` — pending products.
- `state/posted.json` — previously posted ASINs.

GitHub Actions commits state changes back to the repository after workflow execution.

## Automation & Scheduling

GitHub Actions runs two workflows:

### Scrape workflow

Runs daily to refill the queue.

```text
05:00 Riyadh / 02:00 UTC
```

### Post workflow

Runs at the configured publishing times throughout the day.

The current workflow contains 10 scheduled runs between 09:00 and 22:00 Riyadh time, plus manual `workflow_dispatch` support.

## Tech Stack

| Area | Technology |
|---|---|
| Language | Python 3.11 |
| Browser automation | Playwright |
| Image generation | Pillow |
| Video generation | MoviePy |
| Arabic text rendering | arabic-reshaper, python-bidi |
| Telegram | python-telegram-bot |
| X / Pinterest | Playwright-based browser automation |
| Scheduling / CI | GitHub Actions |
| State persistence | JSON |

## Project Structure

```text
.
├── main.py
├── core/
│   └── config.py
├── scraper/
│   ├── amazon_scraper.py
│   └── categories.json
├── content/
│   ├── caption.py
│   ├── image_builder.py
│   └── video_builder.py
├── posters/
│   ├── telegram_poster.py
│   ├── x_poster.py
│   └── pinterest_poster.py
├── state/
│   ├── queue.json
│   └── posted.json
├── .github/
│   └── workflows/
│       ├── scrape.yml
│       └── post.yml
├── config.example.json
└── requirements.txt
```

## Security & Configuration

Runtime credentials are supplied through environment variables / GitHub Actions secrets rather than committed credentials.

Do not commit:

- `config.json`
- `x_cookies.json`
- `pinterest_cookies.json`
- Real affiliate identifiers
- Real runtime queue/history data when they contain operational tracking data

For portfolio use, replace real affiliate IDs with placeholders in example configuration.

## Local Setup

```bash
git clone https://github.com/zeyad-mohvme-d/Affilate_bot.git
cd Affilate_bot

python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

Create `config.json` from `config.example.json` and provide the required runtime values through environment variables or local configuration.

### Run the scraper

```bash
python main.py --scrape
```

### Run the posting pipeline

```bash
python main.py --post
```

## Reliability Features

The project includes several practical reliability mechanisms:

- Duplicate detection using ASIN.
- Required-field validation during scraping.
- Robot / CAPTCHA page detection.
- Debug HTML, screenshots, and reports for scraper failures.
- Independent publishing attempts per platform.
- Queue retention when all platforms fail.
- Persistent posting history to reduce duplicate content.
- GitHub Actions concurrency control for shared state updates.
- Manual workflow dispatch for operational recovery.

## Notes

Amazon and social-platform interfaces can change over time. Browser automation selectors and authenticated sessions may require maintenance.

This repository is presented as a technical portfolio project demonstrating Python automation, browser automation, media generation, workflow orchestration, state management, and scheduled CI/CD.

## License

MIT
