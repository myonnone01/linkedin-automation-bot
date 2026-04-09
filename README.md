# LinkedIn Sales Navigator Automation Bot

Personal sales-outreach automation tool for LinkedIn Sales Navigator. Runs on
your Windows laptop, controlled from either the laptop or your iPhone via a
responsive web UI on your local network.

## What it does

- Logs into Sales Navigator in a real (visible) Chromium browser
- Scrapes lead and account data from Sales Nav search results or saved lists
- Detects buying signals (viewed your profile, followed your company, TeamLink)
- Generates personalized outreach messages via the Anthropic Claude API
- Sends connection requests (with or without a note), LinkedIn messages, or InMails
- Runs multi-step sequences with automatic reply detection
- Respects InMail credit balance and daily/weekly limits

## Important: LinkedIn Terms of Service

Automating LinkedIn activity (scraping, auto-messaging, auto-connecting) is
against LinkedIn's User Agreement and **can result in temporary or permanent
account restrictions**. This tool:

- Caps volume to 25 actions per session
- Randomizes delays (3-8s between clicks, 30-60s between profiles)
- Runs a real, visible Chromium browser (not headless)
- Uses a persistent browser profile so your normal session is preserved

Use at your own risk, on your own account, with realistic volume.

## Quick Start (Windows)

1. Double-click **`setup.bat`**. This creates a virtual env, installs
   dependencies, installs Playwright's Chromium, and copies `.env.example` to
   `.env`.
2. Open **`.env`** in Notepad and fill in your LinkedIn email/password and your
   `ANTHROPIC_API_KEY`.
3. Double-click **`start.bat`**. The server starts, prints access URLs, and
   opens the dashboard in your default browser.
4. On your iPhone (same Wi-Fi), open Safari to the phone URL printed in the
   terminal, e.g. `http://192.168.1.42:5000`.
5. In the Templates tab, create one or more prompt templates. In the Sequences
   tab, build a sequence (e.g. Day 0 connect → Day 3 message → Day 7 follow-up).
6. On the Dashboard, paste a Sales Navigator search URL or saved list URL, pick
   a sequence, and click **Start**.
7. The first time you run it, a Chromium window will open. Log into LinkedIn
   manually (including any 2FA). On subsequent runs the session is reused.

## Architecture

- **Backend:** Flask (single process, background worker thread)
- **Automation:** Playwright (Chromium, headed, persistent context)
- **AI:** Anthropic Claude API (`claude-sonnet-4-6` by default)
- **DB:** SQLite (file-based, zero-config)
- **Frontend:** Jinja2 + Tailwind via CDN, no build step
- **Live logs:** Server-Sent Events (works in iPhone Safari and all desktop browsers)

## File layout

```
app.py                   Flask entrypoint, LAN banner, auto-open browser
config.py                dotenv loading + constants
db.py                    SQLite schema and repo helpers
logger.py                Thread-safe log bus for SSE fan-out
ai/claude_client.py      Claude message generation + char-limit enforcement
automation/browser.py    Playwright persistent context launcher
automation/sales_nav.py  Login, search, profile scrape, InMail credits
automation/messaging.py  connect/note/message/inmail senders
automation/humanize.py   Randomized delays + mouse jitter
sequences/engine.py      "who is due" sweep, state transitions, reply detection
routes/*.py              Flask blueprints
templates/*.html         Jinja2 + Tailwind UI
static/app.js            EventSource + fetch helpers
```

## Safety notes

- Never run two sessions simultaneously (enforced with a thread lock).
- If you get a "Restricted" warning from LinkedIn, stop immediately for 24-48h.
- The `.pw_profile/` directory contains your real LinkedIn session cookies.
  Treat it like a password — don't commit it, don't share it.
