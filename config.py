import os
import sqlite3
import logging
from telethon import TelegramClient
from dotenv import load_dotenv

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except Exception as ex:
        print(f"Failed to load {path}: {ex}")

load_env_file()

# ================= PERSISTENT DATA DIR (RAILWAY VOLUME) =================
# On Railway (and most PaaS free tiers) the container filesystem is wiped on
# every redeploy/restart. This bot stores its SQLite DB *and* the sold
# Telegram account session files locally, so without this you lose your
# entire inventory + balances on every deploy.
#
# Fix: create a Railway Volume, mount it at e.g. /data, and set:
#   DATA_DIR=/data
# Everything below (db file, sessions/ folder) will then live on that volume
# and survive redeploys. Leave DATA_DIR unset to keep the old behavior.
DATA_DIR = os.getenv("DATA_DIR", "").strip()
if DATA_DIR:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.chdir(DATA_DIR)

def env_int(name, default=0):
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "": return default
    # Support comma-separated values — take the first one
    return int(str(raw).strip().split(",")[0].strip())

def env_list(name, default_csv):
    raw = os.getenv(name, default_csv)
    return [item.strip() for item in raw.split(",") if item.strip()]

API_ID = env_int("API_ID", 0)
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

bot = TelegramClient('bot_session', API_ID, API_HASH)
bot.parse_mode = 'html'

ADMIN_ID = env_int("ADMIN_ID", 0)

# CHANNELS
LOG_CHANNEL_ID = env_int("LOG_CHANNEL_ID", 0)
LOG_CHANNEL_ID_2 = env_int("LOG_CHANNEL_ID_2", 0)
LOG_CHANNELS = [ch for ch in [LOG_CHANNEL_ID, LOG_CHANNEL_ID_2] if ch]
CHECK_CHANNELS = env_list("CHECK_CHANNELS", "")
JOIN_URLS = env_list("JOIN_URLS", "")

# LINKS & MEDIA
TERMS_URL = os.getenv("TERMS_URL", "")
CWALLET_QR = os.getenv("CWALLET_QR", "")
CWALLET_ID = os.getenv("CWALLET_ID", "")

# UPI API DETAILS
UPI_MID = os.getenv("UPI_MID", "")
UPI_ID = os.getenv("UPI_ID", "")

OTP_REGEX = r"\b\d{4,8}\b"
AUTO_CANCEL_SECONDS = 600
OTPX_API_KEY = os.getenv("OTPX_API_KEY", "").strip()
OTPX_SERVICE = os.getenv("OTPX_SERVICE", "tg").strip() or "tg"

# Automatic account-stock intake. The automatic importer treats configured
# auto-prices or the fallback cost as the supplier/base price, then adds this
# fixed markup to the customer-facing stock price.
ACCOUNT_PROFIT = env_int("ACCOUNT_PROFIT", 7)
AUTO_STOCK_DEFAULT_COST = env_int("AUTO_STOCK_DEFAULT_COST", 28)
AUTO_STOCK_UPLOAD_ENABLED = os.getenv("AUTO_STOCK_UPLOAD_ENABLED", "1").strip().lower() not in {
    "0", "false", "no", "off"
}

# ================= PREMIUM EMOJIS =================
USE_PREMIUM_EMOJIS = os.getenv("USE_PREMIUM_EMOJIS", "1").strip().lower() not in {"0", "false", "no", "off"}
PREMIUM_EMOJIS = {
    "heart_fire": 5375125990118793401,
    "lightning": 5409271925014801629,
    "location": 5409119256107297715,
    "flower": 5408995930416362034,
    "check": 5409098988156629257,
    "crown": 5409166771330494453,
    "kiss": 5409380965644514142,
    "skull": 5409337058193847247,
    "xmas": 5409320020058584473,
    "monkey": 5408832111773757273,
    "gift": 5440627033111557670,
    "angel": 6203982793379154737,
    "devil": 6064310143380625195,
}

def tg_emoji(name, fallback):
    emoji_id = PREMIUM_EMOJIS.get(name)
    if USE_PREMIUM_EMOJIS and emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

PE_HEART = tg_emoji("heart_fire", "❤️‍🔥")
PE_LIGHTNING = tg_emoji("lightning", "⚡")
PE_LOCATION = tg_emoji("location", "📍")
PE_FLOWER = tg_emoji("flower", "🌸")
PE_CHECK = tg_emoji("check", "✅")
PE_CROWN = tg_emoji("crown", "👑")
PE_KISS = tg_emoji("kiss", "😘")
PE_SKULL = tg_emoji("skull", "💀")
PE_XMAS = tg_emoji("xmas", "🎄")
PE_MONKEY = tg_emoji("monkey", "🐵")
PE_GIFT = tg_emoji("gift", "🎁")
PE_ANGEL = tg_emoji("angel", "😇")
PE_DEVIL = tg_emoji("devil", "😈")

P_YES = PE_CHECK
P_NO = '❌'
P_PKG = '📦'
P_MONEY = '💰'
P_USDT = '💲'
P_INR = '₹'
P_TG = '✈️'
P_GIFT = PE_GIFT
P_STATS = '📊'
P_CARD = '💳'
P_USERS = '👥'
P_CAL = '📅'
P_PC = '💻'
P_EYE = '👁️'
P_UPI = '🏦'
P_CW = '👛'
P_ON = '🟢'
P_OFF = '🔴'
P_ID = '🆔'
P_KEY = '⌨️'
P_GLOBE = PE_LOCATION
P_CART = '🛒'
P_STORE = '🏬'
P_OTP = '🔢'
P_2FA = '🔐'
P_FLAG = '🏳️'
P_PHONE = '📱'
P_WAIT = '⏳'
P_TIME = '⏰'
P_WARN = '⚠️'
P_DOC = '📃'
P_SOS = '🆘'
P_ASST = '🤖'
P_ACC = '👤'
