# Grok Bot stranger onboarding

This is the happy path when someone installs the **LG Laundry Specialist** template and the public repo.

## 1. Install the bot template
Add the public Grok Bot template. Open that chat.

## 2. Bootstrap the engine (bot does this, or user does)
```bash
git clone https://github.com/bryan-lmm/lg-thinq-grok-bot.git
cd lg-thinq-grok-bot
./scripts/bootstrap.sh
```
Always use the venv. Bare `pip install` on many Linux boxes fails with `externally-managed-environment` (PEP 668). That is **not** an LG auth error.

## 3. LG login (OAuth)
Bot runs `thinq-specialty login` and opens the printed URL (or hands the desktop).

**Tell the user before they sign in:**
- After LG sign-in the browser often shows the **login box again**. That is normal.
- Do not keep typing the password.
- When the address bar URL contains `access_token`, hit **I'm done** (or copy the full URL).
- Bot finishes with `thinq-specialty login --callback-url '...'`.

## 4. Store secrets
Put `THINQ_REFRESH_TOKEN` (and keep `THINQ_CLIENT_ID`) in a **secret card** / gitignored env. Never paste tokens into chat. Never commit them.

## 5. Discover then chat
```bash
thinq-specialty devices
thinq-specialty courses --device DEVICE_ID
```
Then natural language: “delicate underwear”, “towels ready by 3:30”. Starts are dry-run until the user says execute. Remote Start must be on the machine.

## Known limits (say them early)
- Official ThinQ Connect PAT cannot set specialty courses.
- Mid-cycle remote cancel/drain is not available (pause / panel only).
- LG may 400 if you rotate `THINQ_CLIENT_ID` too often — keep the one from login.
