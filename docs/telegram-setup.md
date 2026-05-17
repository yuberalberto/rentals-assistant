# Telegram Bot Setup Guide

## 1. Prerequisites
- A Telegram account on your phone or desktop

## 2. Create Your Bot via @BotFather
- Open Telegram, search for @BotFather
- Send `/newbot`
- Choose a display name (e.g. "My Rentals Bot")
- Choose a username ending in `_bot` (e.g. `my_rentals_bot`)
- Copy the token: looks like `110201543:AAHdqTcvCH1vGWJxfSeofSs4tDW5jene2Z4`

## 3. Get Your chat_id via @userinfobot
- Search for @userinfobot in Telegram
- Send any message to it
- It replies with your chat_id (a number like `123456789`)

## 4. Configure .env
```dotenv
TELEGRAM_TOKEN=<paste token from step 2>
TELEGRAM_CHAT_ID=<paste chat_id from step 3>
```

## 5. Validate Your Setup (smoke test)
Run a curl to verify the token is accepted:
```bash
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```
Expected: JSON with `"ok": true`

Or run the notifier test:
```bash
.venv/Scripts/python.exe -m pytest tests/test_notifier.py -v
```

## 6. Troubleshooting
- **"Unauthorized"** → token is wrong or has a space; copy again from BotFather
- **"chat not found"** → you haven't messaged the bot yet; send it `/start` first
- **"Bad Request"** → `TELEGRAM_CHAT_ID` may have wrong format; must be a plain integer
