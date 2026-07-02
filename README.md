# Amazon Affiliate Auto-Posting Bot

> 🇸🇦 **بالعربية:** [README.ar.md](README.ar.md)

Automated bot that scrapes products from **Amazon.sa**, builds a branded image + short video, and posts to **Telegram**, **X (Twitter)**, and **Pinterest** at 10 fixed times every day — fully on autopilot, hosted free on GitHub Actions.

---

## Table of Contents
1. [What this bot does](#1-what-this-bot-does)
2. [Daily schedule](#2-daily-schedule)
3. [Accounts you need](#3-accounts-you-need)
4. [One-time setup](#4-one-time-setup)
   - [4.1 Create a GitHub account](#41-create-a-github-account)
   - [4.2 Accept the repo transfer](#42-accept-the-repo-transfer)
   - [4.3 Install Python on your computer](#43-install-python-on-your-computer)
   - [4.4 Download the project to your computer](#44-download-the-project-to-your-computer)
   - [4.5 Install the project's libraries](#45-install-the-projects-libraries)
   - [4.6 Create your Telegram bot](#46-create-your-telegram-bot)
   - [4.7 Capture X (Twitter) cookies](#47-capture-x-twitter-cookies)
   - [4.8 Capture Pinterest cookies](#48-capture-pinterest-cookies)
   - [4.9 Add all secrets to GitHub](#49-add-all-secrets-to-github)
   - [4.10 First test run](#410-first-test-run)
5. [Daily operation](#5-daily-operation)
6. [Maintenance (cookie refresh)](#6-maintenance-cookie-refresh)
7. [Troubleshooting](#7-troubleshooting)
8. [Configuration reference](#8-configuration-reference)

---

## 1. What this bot does

Every scheduled time (10 times per day), the bot:

1. Picks the next product from a daily queue of 10 Amazon.sa products.
2. Builds a branded **1080×1080 image** (product photo + name + price + CTA button).
3. Builds a **1080×1920 vertical video** for TikTok.
4. Generates a marketing **caption in Arabic** with rotating templates so posts don't look identical.
5. Adds the **Saudi affiliate tag** (`tikshoping01-21`) for Telegram + X, or the **US affiliate tag** (`electron039ae-20`) for Pinterest.
6. Posts:
   - **Telegram** → image + video + caption (channel is the central archive)
   - **X (Twitter)** → image + short caption
   - **Pinterest** → image + caption + destination link
7. Marks the product as posted (so no duplicates).

Once per day at **05:00 Riyadh time**, a separate workflow refills the queue with 10 fresh products.

---

## 2. Daily schedule

Posts go out at these **Riyadh times** (UTC+3):

```
09:00 · 10:00 · 12:00 · 14:00 · 16:00 · 17:00 · 18:00 · 20:00 · 21:00 · 22:00
```

(The schedule lives in `.github/workflows/post.yml` if you ever want to change it — see [Configuration reference](#8-configuration-reference).)

---

## 3. Accounts you need

Before starting, make sure you have:

- [ ] **GitHub** account — free. (Step 4.1 below.)
- [ ] **Telegram channel** + a Telegram **bot** attached to it. (Step 4.6.)
- [ ] **X (Twitter)** account.
- [ ] **Pinterest** account with a board ready (default: "for amazon").
- [ ] **Amazon Associates** account with two tracking tags:
   - One Saudi tag (ends in `-21`)
   - One US tag (ends in `-20`)
- [ ] A **computer** (Windows / Mac / Linux) — used **only once** during setup to capture login cookies. After setup, the bot runs entirely on GitHub's servers.

---

## 4. One-time setup

Estimated time: **30–45 minutes**, if you follow the steps in order.

### 4.1 Create a GitHub account

1. Go to https://github.com/signup
2. Use any email address. Pick a username and password.
3. Verify the email.
4. **Send your GitHub username** to the developer who handed you this project — they will transfer the repo to your account.

> 💡 Free GitHub plan is enough. The bot uses ~50 minutes/month, far below the 2,000-minute free limit.

### 4.2 Accept the repo transfer

After the developer transfers the repo:

1. You'll receive an email from GitHub: *"You have been added as the owner of …"*
2. Click the link → click **Accept** → done. The repo now lives at `https://github.com/YOUR_USERNAME/Affilate_bot`.

### 4.3 Install Python on your computer

You only need Python during the **one-time setup** to capture cookies — after that, you can uninstall it if you want.

**Windows:**
1. Go to https://www.python.org/downloads/
2. Download the latest Python 3.x installer.
3. Run it. **Important:** check the box "**Add Python to PATH**" at the bottom of the first screen.
4. Click "Install Now".
5. Open PowerShell and type `python --version`. You should see `Python 3.x.x`.

**Mac:**
- Open Terminal → run `brew install python3` (or download from python.org).

### 4.4 Download the project to your computer

Two ways — pick one:

**Option A (easy, no Git):**
1. Open your repo on GitHub.
2. Click the green **Code** button → **Download ZIP**.
3. Extract the ZIP somewhere easy to find (e.g., `Desktop\Affilate_bot`).

**Option B (with Git, recommended):**
1. Install Git: https://git-scm.com/downloads
2. Open PowerShell → navigate to where you want the project (e.g. `cd Desktop`).
3. Run: `git clone https://github.com/YOUR_USERNAME/Affilate_bot.git`

### 4.5 Install the project's libraries

In PowerShell, navigate **into** the project folder, then install dependencies:

```powershell
cd path\to\Affilate_bot
pip install -r requirements.txt
python -m playwright install chromium
```

The first command installs Python packages. The second installs the headless browser the bot uses for X and Pinterest. Both might take a few minutes.

### 4.6 Create your Telegram bot

1. Open Telegram → search for **@BotFather** → start a chat.
2. Send `/newbot` → follow the prompts:
   - Bot's display name (e.g., "Smart Deals Bot").
   - Bot's username (must end in `bot`, e.g., `smart_deals_bot`).
3. BotFather replies with a **token** that looks like `1234567890:AAH...`. **Save this — you'll need it later.**
4. Open your channel in Telegram → tap the channel name at top → **Administrators** → **Add Admin** → search for your bot's username → add it → enable "**Post Messages**" → save.

### 4.7 Capture X (Twitter) cookies

The bot needs to be logged in to X to post. You log in once on your computer, save the login state, and upload it as a GitHub Secret.

1. **Create a local config file.** Inside the project folder, find `config.example.json`, copy it, and rename the copy to `config.json`. This file stays on your computer only — never uploaded.

2. In PowerShell, from inside the project folder, run:
   ```powershell
   python -m posters.x_poster --login
   ```

3. A browser window will open showing the X login page.

4. **Log in with your X account.** Complete any 2FA or phone verification X asks for.

5. Once you see the X home feed (you're fully logged in), switch back to PowerShell and **press Enter** as instructed.

6. You'll see `Cookies saved to ...x_cookies.json` and `Saved N cookies.` Done — the file `x_cookies.json` now contains your session.

### 4.8 Capture Pinterest cookies

1. Open `config.json` (the one you copied in step 4.7) in a text editor like Notepad.

2. In the `pinterest` section, replace the placeholders with your real Pinterest email and password:
   ```json
   "pinterest": {
     "email": "your_email@example.com",
     "password": "your_password",
     "default_board": "for amazon"
   },
   ```
   Save the file.

3. Delete any existing cookies file:
   ```powershell
   Remove-Item pinterest_cookies.json -ErrorAction SilentlyContinue
   ```

4. Run the Pinterest poster in headed mode:
   ```powershell
   python -m posters.pinterest_poster --headed
   ```

5. A browser opens, the bot auto-logs in with your email + password, then posts a small **test pin** on your account. (You can delete that test pin afterwards — it's just a placeholder.)

6. After the run finishes, the file `pinterest_cookies.json` now contains your session.

> ℹ️ If Pinterest asks for a verification code or CAPTCHA, you'll see the browser pause — complete it manually, and the script will continue.

### 4.9 Add all secrets to GitHub

This is the most important step — these are what the bot uses on the cloud.

1. On GitHub, go to your repo → **Settings** (top right) → **Secrets and variables** → **Actions**.

2. For each row in this table, click **New repository secret**, fill in the name **exactly**, and paste the value:

   | Secret name | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | The token from BotFather (step 4.6) |
   | `TELEGRAM_CHANNEL_ID` | Your channel's @username, e.g. `@LunaDealsAd` |
   | `PINTEREST_EMAIL` | Your Pinterest email |
   | `PINTEREST_PASSWORD` | Your Pinterest password |
   | `X_COOKIES_JSON` | The **entire contents** of `x_cookies.json` (open with Notepad → Ctrl+A → Ctrl+C → paste) |
   | `PINTEREST_COOKIES_JSON` | The **entire contents** of `pinterest_cookies.json` |

3. After all 6 are saved, you should see 6 rows on the page.

> ⚠️ Don't put quotes around the values. Just paste the raw text.

### 4.10 First test run

1. On GitHub, click the **Actions** tab.
2. In the left sidebar, click **"Post — publish next product to all 3 platforms"**.
3. On the right side, click **Run workflow** → leave branch on `main` → click the green **Run workflow** button.
4. Wait ~5 seconds → refresh. A new run appears. Click it to watch live.
5. After ~3–5 minutes, all steps should be green ✅.
6. Open Telegram, X, and Pinterest — you should see a fresh post on all three.

If anything failed, check [Troubleshooting](#7-troubleshooting).

---

## 5. Daily operation

Once setup is done, the bot runs itself:

- **05:00 Riyadh daily** — refills the queue with 10 fresh products.
- **10 times daily** (see [schedule](#2-daily-schedule)) — posts one product to all 3 platforms.

You don't need to do anything. Just check that posts are going out (Telegram is the easiest place to verify).

**GitHub will email you** automatically if any run fails.

---

## 6. Maintenance (cookie refresh)

Login cookies for X and Pinterest **expire every 1–3 months**. When they do, the bot will start failing those platforms (Telegram will still work).

**To refresh:**

1. On your computer, repeat **step 4.7** for X and **step 4.8** for Pinterest. Fresh cookies will be saved.
2. Go to GitHub → Settings → Secrets → Actions → click the pencil ✏️ next to `X_COOKIES_JSON` (or `PINTEREST_COOKIES_JSON`) → paste the new contents → Update.
3. Run the Post workflow manually (step 4.10) to verify.

Takes about 5 minutes.

---

## 7. Troubleshooting

### A run failed — how do I see why?

1. GitHub repo → **Actions** tab → click the failed run.
2. Click the failed job → expand the step with the ❌.
3. Read the error message at the bottom.
4. Scroll to the bottom of the run page for **"Artifacts"** — failed posts upload debug screenshots there.

### Telegram says "chat not found" or "not enough rights"

The bot isn't an admin in your channel. Redo step 4.6 part 2: open channel → Administrators → Add Admin → search the bot → enable "Post Messages".

### X / Pinterest says "session expired" or "login redirect"

Cookies expired. Refresh them — see [Maintenance](#6-maintenance-cookie-refresh).

### Amazon returned a CAPTCHA / robot check

Rare but happens. Re-run the workflow — Amazon usually clears it. If it persists, wait an hour.

### Queue is empty

The scrape workflow didn't run today. Trigger it manually: **Actions** → "Scrape — refill product queue" → **Run workflow**.

---

## 8. Configuration reference

Most things you might want to change live in **`config.example.json`** (which becomes `config.json` on the runner). Edit this file in the repo, commit + push, and the next run picks it up.

| Field | What it does |
|---|---|
| `schedule_times` | Display-only; the actual schedule is in `.github/workflows/post.yml` |
| `products_per_day` | How many products the daily scrape collects (default 10) |
| `prioritize_discounts` | If `true`, discounted products are posted first |
| `amazon.source_url` | Fallback search URL if no categories are loaded |
| `amazon.tag_us` | US Amazon Associates tag applied to every link (all platforms) |
| `pinterest.default_board` | Which Pinterest board to post to |
| `captions.hashtags` | Hashtags appended to every caption |

To change **what times** the bot posts: edit the `cron:` lines in `.github/workflows/post.yml`. Times are in UTC — subtract 3 hours from Riyadh time.

To change **which product categories** are scraped: edit `scraper/categories.json`.

---

## License

MIT — see [LICENSE](LICENSE).
