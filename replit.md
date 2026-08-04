# NUMBOTT TELETHON

A modular Telegram account shop bot built with Python and Telethon (MTProto).

## How to run

The bot starts automatically via the **Start application** workflow:
```
python main.py
```

## Stack

- **Language:** Python 3.10+
- **Telegram framework:** Telethon (MTProto)
- **Database:** SQLite3 (`otp_bot_final.db`)
- **Entry point:** `main.py`

## Required secrets (set in Replit Secrets)

| Key | Description |
|---|---|
| `API_ID` | Telegram API ID from https://my.telegram.org |
| `API_HASH` | Telegram API Hash from https://my.telegram.org |
| `BOT_TOKEN` | Bot token from @BotFather |
| `ADMIN_ID` | Your Telegram user ID (primary admin). Supports comma-separated for multiple owners — first ID is used as primary |
| `LOG_CHANNEL_ID` | Main log channel ID (negative number, e.g. -1001234567890) |
| `LOG_CHANNEL_ID_2` | Secondary log channel ID (can be same as LOG_CHANNEL_ID) |
| `CHECK_CHANNELS` | Comma-separated channel IDs for must-join verification (leave blank to disable) |
| `JOIN_URLS` | Comma-separated invite links matching CHECK_CHANNELS order |
| `CWALLET_ID` | CWallet wallet address/ID for crypto deposits |
| `UPI_ID` | UPI address for Indian payments (e.g. name@bank) |

### Optional secrets

| Key | Description |
|---|---|
| `TERMS_URL` | URL to your Terms & Conditions page |
| `CWALLET_QR` | CWallet QR code image URL |
| `UPI_MID` | UPI merchant ID |
| `USE_PREMIUM_EMOJIS` | Set to `0` to disable Telegram premium emoji (default: `1`) |

## Project structure

```
main.py              — Entry point
config.py            — All env var loading + Telethon client init
database.py          — SQLite setup + helper functions
plugins/
  start.py           — /start command, must-join check, terms flow
  buy.py             — Account purchase flow + auto OTP delivery
  deposit.py         — Deposit menu, payment proof handling, admin approval
  admin.py           — Admin panel
  profile.py         — User profile, stats, purchase history
  callbacks.py       — Shared button callbacks (balance, stock, orders, refer, support)
  admin_actions.py   — Admin action handlers
utils/
  helpers.py         — Channel join checks
  keyboards.py       — Button builders
  states.py          — In-memory state tracking (active orders, deposit inputs)
assets/
  image.jpg          — Bot welcome image
```

## Notes

- All payments are **manually verified** — no automatic payment confirmation. Admin approves/rejects via the log channel.
- The bot must be added as **admin** to all log channels and must-join channels.
- Session files for stock accounts should be stored in the `sessions/` directory.
