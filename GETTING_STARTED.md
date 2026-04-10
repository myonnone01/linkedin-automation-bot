# Getting Started — for non-technical users

This is the friendly walkthrough. If you've never installed Python or used a
terminal before, start here. Total time: about 20 minutes for the fast path,
or 45 minutes if you do every click yourself.

There are two ways to set up the tool:

- **Fast path (one PowerShell paste)** — recommended. One command does almost everything for you.
- **Manual path (every click yourself)** — if the fast path fails, or if you want full control.

---

## Fast path: one PowerShell paste

This handles installing Python, downloading the project, running setup, and
loading starter templates — all from one command.

### What you need first

- A Windows 10 or Windows 11 laptop you have admin rights on
- An internet connection
- 5–10 minutes

### How to run it

1. Press the **Windows key** on your keyboard
2. Type **PowerShell**
3. **Right-click** "Windows PowerShell" in the search results
4. Click **Run as administrator**
5. Click **Yes** on the User Account Control popup
6. Copy the line below and **right-click** inside the blue PowerShell window to paste it (Ctrl+V also works), then press Enter:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force; iwr https://raw.githubusercontent.com/myonnone01/linkedin-automation-bot/claude/linkedin-automation-tool-MGeGK/bootstrap.ps1 -UseBasicParsing -OutFile "$env:TEMP\li-bootstrap.ps1"; & "$env:TEMP\li-bootstrap.ps1"
```

7. Watch the script run. It will print colored progress messages for 9 steps. Most steps take a few seconds; setup.bat (step 6) takes 3-5 minutes because it downloads Chromium.

8. When you see `ALMOST DONE - 4 things you still need to do`, follow those four steps. They are:
   - Get an Anthropic API key
   - Fill in `.env` (Notepad will already be open for you)
   - Double-click `start.bat` in the project folder
   - On first run, log into LinkedIn in the Chromium window and click "Allow" on the firewall popup

That's it. Skip the rest of this document unless something goes wrong.

### If the fast path fails

- **"winget is not installed"** — install "App Installer" from the Microsoft Store at https://apps.microsoft.com/detail/9NBLGGH4NNS1, then re-run.
- **"Python installed but not yet on PATH for this session"** — close PowerShell, open a fresh PowerShell as administrator, and re-run the command.
- **"Download failed: 404"** — the repo might be private or the URL changed. Use the manual path below.
- **`setup.bat exited with code N`** — scroll up to find the actual error. Common: corporate VPN blocking pypi.org, or antivirus blocking the venv folder.
- **Anything else** — fall back to the manual path below.

---

## Manual path: every click yourself

Use this if the fast path failed, if you want to understand each step, or if you don't trust running scripts from the internet.

### 1. What this tool does (in plain English)

You point it at a Sales Navigator search result page. It logs into LinkedIn for you in a real browser window, opens each lead's profile, reads their job title and company, asks Claude (the AI) to write a personalized message, and sends it as a connection request, direct message, or InMail. You control everything from a webpage that runs on your laptop. Your iPhone can open the same webpage if it's on the same Wi-Fi.

### 2. What you need before starting

- A Windows 10 or Windows 11 laptop you control (you need to be able to install software)
- The LinkedIn email and password you normally use
- An Anthropic account with a payment method (~$5 prepay covers a lot)
- An iPhone on the same Wi-Fi as the laptop (optional, only if you want phone access)
- About 30-45 minutes for first-time setup

**Heads-up about LinkedIn:** automating LinkedIn is against their Terms of Service. The tool is designed to look human (small daily limits, randomized delays, real visible browser), but accounts can still be restricted. Use it on your own account, with realistic volume. Read the README for the full caveat.

### 3. Step 0 — Get the code onto your laptop

Easiest way (no git, just browser clicks):

1. Open Chrome or Edge
2. Go to:
   ```
   https://github.com/myonnone01/linkedin-automation-bot/tree/claude/linkedin-automation-tool-MGeGK
   ```
3. Click the green **"<> Code"** button on the right
4. In the dropdown, click **"Download ZIP"**
5. The ZIP downloads to your **Downloads** folder
6. Open File Explorer (Windows key + E) → click **Downloads**
7. **Right-click the ZIP file → Extract All...**
8. In the dialog, click **Browse** → select **Documents** → click **Select Folder** → click **Extract**
9. Open **Documents** in File Explorer
10. You'll see a folder with a long name like `linkedin-automation-bot-claude-linkedin-automation-tool-MGeGK`
11. **Right-click it → Rename** → type `linkedin-automation-bot` → press Enter

You should now have a folder at `Documents\linkedin-automation-bot` containing files like `setup.bat`, `start.bat`, `app.py`, `README.md`, plus folders like `automation` and `templates`.

### 4. Step 1 — Install Python

Python is the language the tool is written in. You need it installed before anything else will work.

1. Open Chrome or Edge
2. Go to https://www.python.org/downloads/windows/
3. Click the big yellow **"Download Python 3.x"** button at the top (any version 3.11 or newer is fine)
4. Open the file you just downloaded (it will be in your Downloads folder, named something like `python-3.12.x-amd64.exe`)
5. **CRITICAL:** in the installer window, look at the bottom. There is a checkbox labeled **"Add python.exe to PATH"**. **Tick it.** This is the single most important click in the whole setup. If you skip it, nothing else will work.
6. Click **"Install Now"**
7. Wait 1-2 minutes for it to finish
8. Click **"Close"**

To verify it worked:
1. Press the Windows key
2. Type **cmd**
3. Press Enter — a black window opens
4. Type `python --version` and press Enter
5. You should see something like `Python 3.12.3`

If you see `'python' is not recognized as an internal or external command`, you forgot the PATH checkbox. Uninstall Python from Settings → Apps, then reinstall and tick the checkbox this time.

### 5. Step 2 — Run setup.bat

This creates a private Python environment for the tool, downloads everything it needs (Flask, Playwright, the Claude SDK), downloads Chromium for browser automation, and creates a settings file you'll fill in next.

1. Open File Explorer
2. Navigate to `Documents\linkedin-automation-bot`
3. **Double-click `setup.bat`**
4. A black terminal window opens. **Don't close it.** It will go through these steps:
   - `[1/4] Creating virtual environment in .venv ...` — a few seconds
   - `[2/4] Activating virtual environment and upgrading pip ...` — quick
   - `[3/4] Installing dependencies from requirements.txt ...` — wall of text scrolling for 1-3 minutes (normal!)
   - `[3b/4] Installing Playwright Chromium ...` — downloads ~150 MB, takes 2-5 minutes depending on your internet
   - `[4/4] Checking for .env ...` — should say "Created .env from template"
   - `=== Setup complete ===`
   - `Press any key to continue . . .`
5. Press any key (the spacebar works). The window closes.

If something failed, the script will pause on the error. See the Troubleshooting table at the bottom of this document.

### 6. Step 3 — Get your Anthropic API key

Claude is the AI that writes the personalized messages. It runs on Anthropic's servers, and Anthropic charges a few cents per message. You need an API key.

1. Open Chrome or Edge
2. Go to https://console.anthropic.com
3. Click **Sign Up** (or Log In if you have an account)
4. The Google sign-in works fine if you have a Google account
5. Once logged in, in the left sidebar click **Settings**
6. Click **Billing**
7. Click **Add payment method** and add a card
8. Click **Buy credits** and prepay **$5** (this is enough for hundreds of messages)
9. In the left sidebar click **API Keys**
10. Click **Create Key**
11. Name it `linkedin-bot` and click **Create**
12. **Copy the key.** It starts with `sk-ant-`. **You only see it once** — Anthropic doesn't show it again. Paste it into a temporary Notepad window so you don't lose it.

### 7. Step 4 — Edit the .env settings file

`.env` is a plain text file containing your passwords and API key. It lives only on your laptop and never gets uploaded anywhere.

1. In File Explorer, in `Documents\linkedin-automation-bot`, find the file called `.env` (with a dot at the front)
2. **If you can't see it:** click the **View** tab in File Explorer → tick **File name extensions** and **Hidden items**
3. **Right-click `.env` → Open with → Notepad**
4. Find these three lines and replace the blank values with your real credentials:
   ```
   LINKEDIN_EMAIL=your-linkedin-email@example.com
   LINKEDIN_PASSWORD=your-linkedin-password-here
   ANTHROPIC_API_KEY=sk-ant-...
   ```
5. **Important formatting:** no quotes around the values, no spaces around the `=`. Just `KEY=value`.
6. **File → Save** (or Ctrl+S)
7. Close Notepad

Leave all the other settings (DAILY_LIMIT, delays, etc.) at their defaults.

### 8. Step 5 (optional) — Load starter templates and sequences

This saves you about 10 minutes of typing in the UI. It loads 5 example message angles (IT Director intro, VP Engineering value-prop, etc.) and 3 example sequences. You can edit or delete any of them later from the web UI.

1. Press the Windows key
2. Type **cmd** and press Enter
3. In the black window, type each of these and press Enter after each:
   ```
   cd %USERPROFILE%\Documents\linkedin-automation-bot
   .venv\Scripts\activate
   python seed.py
   ```
4. You should see output like:
   ```
   + template 'Warm connect (no note)'
   + template 'IT Director intro note'
   + sequence 'IT Director 4-step' (id=1)
   ```
5. Type `exit` and press Enter to close the window

If you skip this step, you'll just need to create at least one template and one sequence in the web UI before you can run the tool.

### 9. Step 6 — Run start.bat

1. In File Explorer, in `Documents\linkedin-automation-bot`, **double-click `start.bat`**
2. A black terminal window opens
3. Within a few seconds you should see:
   ```
   ============================================================
     LinkedIn Automation Bot is running

     Desktop:  http://localhost:5000
     Phone:    http://192.168.1.42:5000
   ============================================================
   ```
4. Your default browser opens automatically to the dashboard
5. **Important:** leave the terminal window open. Closing it stops the tool. You can minimize it.

If the browser doesn't open automatically, open Chrome and type `http://localhost:5000` in the address bar.

### 10. Step 7 — Allow the Windows firewall popup (first run only)

The very first time you run `start.bat`, Windows Defender Firewall will pop up a dialog asking if Python should be allowed through the firewall.

1. Tick the checkbox next to **"Private networks, such as my home or work network"**
2. Click **Allow access**

Without this, your iPhone won't be able to reach the dashboard.

### 11. Step 8 — Open the dashboard on your iPhone

1. Make sure your iPhone is on the **same Wi-Fi network** as the laptop (not cellular, not a different router/SSID)
2. Open Safari
3. Type the **Phone:** URL from the terminal banner (e.g. `http://192.168.1.42:5000` — yours will be different)
4. The dashboard loads

For one-tap access later: tap the **Share** button at the bottom (square with up-arrow) → scroll down → **Add to Home Screen** → name it `LI Bot` → Add. Now you have a tappable icon on your home screen.

### 12. Step 9 — Build your first template and sequence

**Skip this section if you ran seed.py — you already have starters.**

A **template** is the angle/goal you give to Claude. A **sequence** is a multi-step outreach plan that uses templates.

To create a template:
1. Click **Templates** in the left sidebar (or bottom tab on iPhone)
2. Fill in:
   - **Name:** e.g. `IT Director intro`
   - **Delivery method:** `Connection request with note`
   - **Target role keywords:** `director, head of it`
   - **Message angle:** `Reference any shared connection if present, otherwise lead with relevance to their role at {{company}}. Mention Presidio has helped similar IT orgs modernize. Under 300 characters.`
3. Click **Save template**

To create a sequence:
1. Click **Sequences** in the sidebar
2. Type a name like `IT Director 3-step`, click **Create sequence**
3. The sequence appears below. Add a step:
   - **Step #:** `1`
   - **Delay (days):** `0`
   - **Delivery:** `Connection note`
   - **Template:** pick the one you just created
   - Click **+ Add step**
4. Repeat for steps 2 and 3 with different delays (e.g. 3 days, 7 days)

### 13. Step 10 — Run your first session

1. Click **Dashboard** (or the home tab on iPhone)
2. In the **Sales Navigator URL** field, paste a Sales Navigator search URL or saved list URL. (To get one: do your normal Sales Nav search, then copy the URL from your browser's address bar.)
3. Pick your sequence from the **Sequence** dropdown
4. Leave **Daily limit** at 20 (don't push it higher until you're sure things are working)
5. Click **▶ Start**
6. A Chromium browser window opens (this is the visible browser the tool uses)
7. The live log on the dashboard will say `WAITING FOR 2FA` — **this is expected on the first run**
8. Switch to the Chromium window and log into LinkedIn manually:
   - Email
   - Password
   - Any 2FA code on your phone
   - Any "I am human" check
9. Once you reach Sales Navigator's home page, the tool takes over
10. The log feed shows each action as it happens. You can also watch this from your iPhone — both devices see the same feed in real time.
11. Click **■ Stop** anytime to cancel cleanly. The tool finishes its current action and closes the browser.

After this first login, your session cookies are saved. You won't have to log in manually again for several weeks.

### 14. Daily use after first setup

1. Double-click `start.bat`
2. Click Start in the dashboard (no manual login needed — cookies are still valid)
3. That's it. About 30 seconds of clicking per day.

### 15. Connect-only quick mode

If you just want to grow your network without sending any messages:

1. In the dashboard, paste a Sales Nav URL
2. **Tick the checkbox** next to "Connect only (no message, skips sequences and Claude)"
3. Click Start

The tool will send a plain connection request (no note, no AI message) to every lead it finds, up to your daily limit. No Claude calls = no API cost for this mode.

---

## Troubleshooting

### Setup errors

| What you see | What it means | What to do |
|---|---|---|
| `Python was not found` in setup.bat | You skipped the "Add to PATH" checkbox during Python install | Uninstall Python from Settings → Apps, reinstall, **tick the checkbox** |
| `pip install failed` red text | Internet is blocking pypi.org (often a corporate VPN or firewall) | Disconnect VPN, or run setup.bat from a personal Wi-Fi network |
| `Defender blocked .venv` | Antivirus quarantined the Python files | Add `Documents\linkedin-automation-bot` to Defender exclusions |

### Running errors

| What you see | What it means | What to do |
|---|---|---|
| Browser doesn't auto-open | Default browser not set, or Chromium took over your defaults | Manually open Chrome and type `http://localhost:5000` |
| iPhone can't reach the URL | Wi-Fi has client isolation, or firewall blocked Python | Check both devices on same Wi-Fi network. Click "Allow" on the firewall popup. Restart `start.bat`. |
| Log feed says `WAITING FOR 2FA` and never moves | You haven't completed the LinkedIn login in the Chromium window yet | Switch to the Chromium window and finish the login. You have 3 minutes. |
| `Claude API error: unauthorized` | Wrong API key or no Anthropic credit | Check `.env` for typos, check Billing page on console.anthropic.com |
| `Connect button not found` for every lead | LinkedIn updated their UI and the selectors are stale | Tell me — needs a one-line update in `automation/sales_nav.py` |
| Tool sends nothing, log shows `already_connected` | You're already 1st-degree connected with these leads | Use a different search filter, or use a `linkedin_message` step instead of `connection_note` |
| Tool sends nothing, log shows `credits_exhausted` | Sales Navigator InMail credits hit zero | Wait for the monthly refresh, or remove InMail steps from your sequences |
| Chromium window says "Restricted" or "Verify it's you" | LinkedIn flagged unusual activity | **Stop the tool immediately. Do not run for 24-48 hours.** Then run with a smaller daily limit (10 instead of 20). |

### "I want to start over completely"

1. Delete the folder `Documents\linkedin-automation-bot`
2. Delete `Documents\linkedin-automation-bot.backup-*` if any
3. Re-run the fast path or the manual path

This wipes everything: the database, the Playwright session cookies, the templates, the sequences. Your `.env` credentials are gone too — you'll re-enter them.

---

## Glossary

- **Sales Navigator** — LinkedIn's paid sales tool with better search filters
- **Saved list** — a collection of leads you've manually grouped in Sales Nav
- **TeamLink connection** — a Sales Nav feature showing when a colleague at your company is connected to a prospect
- **InMail** — Sales Navigator's paid messaging feature for contacting people you're not connected to
- **1st-degree connection** — someone you're directly connected to on LinkedIn
- **2FA** — two-factor authentication, the extra code LinkedIn texts or notifies for security
- **Sequence** — a multi-step outreach plan with delays between messages
- **Template** — an "angle" you give Claude to base each personalized message on
- **Connection note** — the short text you can include with a connect request (500-character limit)
- **Daily limit** — the cap on how many actions the tool will do in one session
- **Buying signal** — a hint that a lead might be interested (e.g. they viewed your profile, follow your company, or you share a TeamLink connection)
- **`.env`** — a plain text file with your secrets (passwords, API keys). Lives only on your laptop, git-ignored, never uploaded anywhere.
- **venv** — Python virtual environment, a private folder of Python packages just for this tool. Created by setup.bat in `.venv\`.
- **Chromium** — the open-source browser engine that powers Chrome and Edge. Playwright bundles its own copy.

---

## Where to find help

If something isn't covered here, check the README in the project folder for technical details, or ask whoever set this up for you.
