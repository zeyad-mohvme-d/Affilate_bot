# Amazon Affiliate Auto-Posting Bot — User Guide

> 🇸🇦 **بالعربية:** [README.ar.md](README.ar.md)

Welcome! This is your bot's user manual. It covers how it works day-to-day, what you can customize, and how to fix common problems.

---

## Table of Contents
1. [What this bot does](#1-what-this-bot-does)
2. [Daily schedule](#2-daily-schedule)
3. [How to access the bot](#3-how-to-access-the-bot)
4. [How to check if it's working](#4-how-to-check-if-its-working)
5. [What you can customize](#5-what-you-can-customize)
   - [5.1 Change the promotional lines (bank code + channel code)](#51-change-the-promotional-lines-bank-code--channel-code)
   - [5.2 Change the Pinterest board](#52-change-the-pinterest-board)
   - [5.3 Change how many products per day](#53-change-how-many-products-per-day)
   - [5.4 Change what products the bot scrapes](#54-change-what-products-the-bot-scrapes)
   - [5.5 Change the posting times](#55-change-the-posting-times)
6. [Maintenance: refreshing login cookies](#6-maintenance-refreshing-login-cookies)
7. [Troubleshooting](#7-troubleshooting)
8. [Understanding the file structure](#8-understanding-the-file-structure)

---

## 1. What this bot does

The bot runs entirely on GitHub's servers — you do NOT need to keep any computer on. Every day, it automatically:

1. Scrapes fresh products from **amazon.com** (once daily at 5 AM Riyadh time).
2. At each of 10 scheduled times per day, picks the next product from the queue.
3. Downloads a screenshot of the Amazon product page (or the raw high-res product image as a backup).
4. Builds a short 15-second video for TikTok.
5. Writes an Arabic marketing caption with your promo codes and the affiliate link.
6. Publishes:
   - **Telegram** → image + video + caption to your channel
   - **X (Twitter)** → image + caption
   - **Pinterest** → pin with image + caption + affiliate link
7. All affiliate links use your US tag (`electron039ae-20`) and point to real amazon.com product pages — commissions will track properly.

---

## 2. Daily schedule

Posts go out at these **Riyadh times** (UTC+3):

```
09:00 · 10:00 · 12:00 · 14:00 · 16:00 · 17:00 · 18:00 · 20:00 · 21:00 · 22:00
```

Once daily at **05:00 Riyadh**, a separate task refills the product queue with 10 fresh products.

---

## 3. How to access the bot

The bot lives on GitHub at:
```
https://github.com/YOUR_USERNAME/Affilate_bot
```

- Log in with the GitHub account you were transferred ownership to.
- Everything you need is in one place — code, workflows, monitoring, and secrets.

---

## 4. How to check if it's working

1. Go to your repo → click the **"Actions"** tab (top of the page).
2. You'll see two workflows in the left sidebar:
   - **"Post — publish next product to all 3 platforms"**
   - **"Scrape — refill product queue"**
3. Click either one to see recent runs — green checkmarks = success, red X = failure.
4. Click any run to see detailed logs.

**GitHub will also email you automatically if any run fails**, so you don't have to check regularly.

---

## 5. What you can customize

You can edit files directly on GitHub — you don't need to install anything on your computer.

**How to edit any file on GitHub:**
1. Open the file in your repo (click on it).
2. Click the pencil icon ✏️ at the top right.
3. Edit the text.
4. Scroll down → click the green **"Commit changes"** button.
5. Confirm — the next scheduled run will use your new values.

---

### 5.1 Change the promotional lines (bank code + channel code)

**File:** `config.example.json`

The bot puts two customizable lines in every post caption. By default they say:
```
فعّل خصم بنك الراجحي 25% ⬅️
فعّل كود القناة 15% ⬅️
```

To change them, edit these two lines in `config.example.json`:
```json
"captions": {
  "language": "ar",
  "bank_discount_line": "فعّل خصم بنك الراجحي 25% ⬅️",
  "channel_code_line": "فعّل كود القناة 15% ⬅️"
}
```

- Change the text inside the quotes to whatever you want.
- To **hide a line completely**, set its value to empty: `"channel_code_line": ""`
- You can use Arabic, English, or a mix — anything that goes in quotes will appear in the caption.

### 5.2 Change the Pinterest board

**File:** `config.example.json`

Look for:
```json
"pinterest": {
  ...
  "default_board": "for amazon"
}
```

Change `"for amazon"` to any board name that exists on your Pinterest account. If the board doesn't exist, the bot will create it for you on the next run.

### 5.3 Change how many products per day

**File:** `config.example.json`

Look for:
```json
"products_per_day": 10,
```

Change `10` to any number. The daily scrape task will collect that many products for the next day's posts.

⚠️ **Note:** the posting schedule has 10 fixed times (see section 5.5). If you set `products_per_day` lower (e.g., 5), the bot will run out of products before the day ends.

### 5.4 Change what products the bot scrapes

**File:** `scraper/categories.json`

This file has the categories the bot cycles through. Structure:
```json
{
  "groups": [
    {
      "id": "group_1",
      "name": "Your group name",
      "categories": [
        { "name": "Clothing", "query": "clothing" },
        { "name": "Shoes",    "query": "shoes" }
      ]
    }
  ]
}
```

- The **`query`** field is what actually gets searched on amazon.com — write it in English.
- **`name`** is just a label for your own reference.
- Add, remove, or reorder as you like.

Alternatively, to skip categories entirely and always use one search URL, edit `config.example.json`:
```json
"amazon": {
  "source_url": "https://www.amazon.com/s?k=home+improvement"
}
```

Change `home+improvement` to any keywords (use `+` instead of spaces).

### 5.5 Change the posting times

**File:** `.github/workflows/post.yml`

This is a slightly technical file, but you can edit the cron schedule. Look for the `schedule:` block:

```yaml
schedule:
  # 09:00 Riyadh = 06:00 UTC
  - cron: "0 6 * * *"
  # 10:00 Riyadh = 07:00 UTC
  - cron: "0 7 * * *"
  # (etc.)
```

- Each `- cron:` line is one posting time, in **UTC**.
- To convert Riyadh time to UTC, subtract 3 hours (Riyadh 09:00 = UTC 06:00).
- Format: `"MINUTE HOUR * * *"` — `0 6 * * *` = 06:00 UTC daily.
- Delete a line to remove that time. Add a new `- cron:` line to add one.

---

## 6. Maintenance: refreshing login cookies

**The only recurring task.** Your X and Pinterest login sessions expire every **1–3 months**. When they do, X and/or Pinterest posts will fail (Telegram keeps working — it uses a different login system).

If GitHub emails you about a failure, or you notice missing posts on X or Pinterest, you (or the developer) need to refresh cookies.

**Simple version:** ask the developer to help — this needs Python installed on a computer.

**Do-it-yourself version:** follow the technical guide below.

<details>
<summary>Click to expand: how to refresh cookies yourself</summary>

1. **Install Python** on any computer (Windows, Mac, Linux): https://www.python.org/downloads/
2. **Download the project** from GitHub → Code button → Download ZIP → extract.
3. In a terminal/PowerShell, go into the folder and install dependencies:
   ```
   pip install -r requirements.txt
   python -m playwright install chromium
   ```
4. **Copy `config.example.json` to a new file called `config.json`** and fill in your Pinterest email + password.

**For X:**
```
python -m posters.x_poster --login
```
A browser opens → log in to X → press Enter in the terminal → cookies get saved to `x_cookies.json`.

**For Pinterest:**
```
python -m posters.pinterest_poster --headed
```
A browser opens → auto-logs in → posts a small test pin (you can delete it) → cookies saved to `pinterest_cookies.json`.

**Update the GitHub Secrets:**
1. On GitHub → your repo → Settings → Secrets and variables → Actions.
2. Click ✏️ next to `X_COOKIES_JSON` → paste the entire contents of your local `x_cookies.json` → Update.
3. Click ✏️ next to `PINTEREST_COOKIES_JSON` → paste the entire contents of `pinterest_cookies.json` → Update.

Trigger the Post workflow manually (Actions → Post → Run workflow) to verify.

</details>

---

## 7. Troubleshooting

### One of my platforms isn't posting

1. Go to **Actions tab** on GitHub.
2. Click the failed run (has a red X).
3. Expand the failed step → read the error at the bottom.
4. Common causes:
   - **"session expired" or login page redirect** → cookies expired → see [Section 6](#6-maintenance-refreshing-login-cookies).
   - **"Queue is empty"** → the daily scrape didn't run → trigger it manually: Actions → Scrape → Run workflow.
   - **"chat not found" (Telegram)** → the bot got removed from your channel as admin → re-add it.

### The affiliate link doesn't work (404)

The bot should always build clean `amazon.com/dp/ASIN?tag=electron039ae-20` links. If you see something else (like `/sspa/click`), something went wrong — contact the developer.

### I changed a config file and now the bot is broken

Go to the Actions tab → find your commit in the history → your commit should show green if it built correctly. If the run failed, read the error, then go back to your file, click the pencil ✏️, and revert your change or fix the syntax.

### Pinterest saves posts as drafts instead of publishing

Usually caused by Pinterest UI changes or image size issues. Contact the developer.

---

## 8. Understanding the file structure

You don't have to touch most of these — but here's a map so nothing is a mystery:

| File / Folder | What it does |
|---|---|
| `main.py` | The main orchestrator — decides scrape vs post |
| `config.example.json` | **YOUR MAIN SETTINGS FILE** — edit this to customize the bot |
| `scraper/amazon_scraper.py` | Reads amazon.com and pulls products |
| `scraper/categories.json` | List of product categories the bot cycles through |
| `content/caption.py` | Builds the marketing caption for each post |
| `content/screenshot_builder.py` | Takes a screenshot of the Amazon product page |
| `content/video_builder.py` | Builds the TikTok-ready video |
| `posters/telegram_poster.py` | Sends posts to Telegram |
| `posters/x_poster.py` | Posts to X (Twitter) |
| `posters/pinterest_poster.py` | Posts to Pinterest |
| `core/config.py` | Loads config + secrets |
| `state/queue.json` | Today's product queue (auto-managed) |
| `state/posted.json` | History of posted product IDs (prevents duplicates) |
| `.github/workflows/post.yml` | The schedule for posting |
| `.github/workflows/scrape.yml` | The schedule for the daily scrape |
| `assets/fonts/` | Arabic-capable font used in images/videos |
| `requirements.txt` | Python packages the bot needs |

---

## License

MIT — see [LICENSE](LICENSE).

---

**Made for you by your developer. Questions? Bugs? Reach out anytime.**
