import os
import csv
import zipfile
import shutil
import html
import time
from telethon import events, Button, TelegramClient
from telethon.tl.functions.account import GetPasswordRequest
from telethon.errors import SessionPasswordNeededError
from database import cur, db, is_bot_online, is_admin, has_perm, ADMIN_ID, get_flag_by_country_name, get_country_info, update_balance
from config import PE_CROWN, PE_LOCATION, PE_LIGHTNING, P_USERS, P_PKG, P_WAIT, P_ON, P_YES, P_NO, P_WARN, P_DOC, P_FLAG, P_MONEY, P_PHONE, P_GLOBE, P_2FA, P_CAL, P_OTP, P_CARD, P_TG, P_ACC, P_USDT, P_UPI, P_CART, P_GIFT, P_STATS, P_OFF, API_ID, API_HASH, bot
from utils.keyboards import style_btn

async def admin_panel_handler(event):
    uid = event.sender_id
    if not is_admin(uid): return
    
    status_text = "🟢 Bot is ON" if is_bot_online() else "🔴 Bot is OFF"
    total_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_stock = cur.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()[0]
    pending_deposits = cur.execute("SELECT COUNT(*) FROM deposits WHERE status='pending'").fetchone()[0]
    btns = []
    
    if uid == ADMIN_ID or has_perm(uid, 'p_settings'):
        btns.append([style_btn(f"Status: {status_text}", "adm_togglebot", "primary", icon=5409098988156629257)])
        
    r1 = []
    if uid == ADMIN_ID or has_perm(uid, 'p_add_stock'):
        r1.extend([style_btn("Add Single Acc", "adm_addstock", "primary", icon=6129732880529628243), style_btn("Add ZIP", "adm_addzip", "primary", icon=5355292788923593967)])
    if r1: btns.append(r1)

    r2 = []
    if uid == ADMIN_ID or has_perm(uid, 'p_manage_stock'):
        r2.extend([style_btn("Manage Stock", "adm_managestock", "success", icon=6129731974291527294), style_btn("Auto Price", "adm_autoprice", "primary", icon=5409098988156629257)])
    if r2: btns.append(r2)

    r_repo = []
    if uid == ADMIN_ID or has_perm(uid, 'p_add_stock'):
        r_repo.extend([style_btn("➕ Add Repo", "adm_addrepo", "success", icon=5409271925014801629), style_btn("💻 Manage Repos", "adm_managerepos", "primary", icon=5409098988156629257)])
    if r_repo: btns.append(r_repo)

    r_smm = []
    if uid == ADMIN_ID or has_perm(uid, 'p_add_stock'):
        r_smm.extend([style_btn("➕ Add SMM Service", "adm_addsmm", "success", icon=5409098988156629257), style_btn("📊 Manage SMM", "adm_managesmm", "primary", icon=5409271925014801629)])
    if r_smm: btns.append(r_smm)

    r3 = []
    if uid == ADMIN_ID or has_perm(uid, 'p_stats'):
        r3.extend([style_btn("Statistics", "adm_stats", "primary", icon=5409098988156629257), style_btn("Broadcast", "adm_bcast", "primary", icon=5409098988156629257)])
        r3.append(style_btn("User Info", "adm_userinfo", "primary", icon=5409098988156629257))
    if r3: btns.append(r3)

    r4 = []
    if uid == ADMIN_ID or has_perm(uid, 'p_bal'):
        r4.extend([style_btn("Change Balance", "adm_bal", "primary", icon=6129888444245089008), style_btn("Ban User", "adm_ban", "danger", icon=5408832111773757273)])
    if r4: btns.append(r4)

    r5 = []
    if uid == ADMIN_ID or has_perm(uid, 'p_settings'):
        r5.extend([style_btn("Discount", "adm_discount", "primary", icon=5409098988156629257), style_btn("Ref %", "adm_refpct", "primary", icon=5409098988156629257)])
        btns.append(r5)
        btns.append([style_btn("Support URL", "adm_supporturl", "primary", icon=5409098988156629257), style_btn("Payments", "adm_payments", "primary", icon=5409098988156629257)])
        btns.append([style_btn("Set USDT Rate", "adm_usdtrate", "primary", icon=5409098988156629257)])
        btns.append([style_btn("𝐁ᴀᴄᴋup Users", "adm_backupusr", "primary", icon=5409098988156629257), style_btn("Restore Users", "adm_restoreusr", "primary", icon=5409098988156629257)])

    if uid == ADMIN_ID:
        btns.append([style_btn("Manage Admins", "adm_manageadmins", "primary", icon=5409098988156629257)])

    header = (f"<blockquote>{PE_CROWN} <b>𝐀ᴅᴠᴀɴᴄᴇᴅ 𝐀ᴅᴍɪɴ 𝐃ᴀsʜʙᴏᴀʀᴅ</b>\n\n"
              f"{P_USERS} 𝐔sᴇʀs: <b>{total_users}</b>\n"
              f"{P_PKG} 𝐀ᴠᴀɪʟᴀʙʟᴇ 𝐒ᴛᴏᴄᴋ: <b>{total_stock}</b>\n"
              f"{P_WAIT} 𝐏ᴇɴᴅɪɴɢ 𝐃ᴇᴘᴏsɪᴛs: <b>{pending_deposits}</b>")
    try: await event.edit(header, buttons=btns)
    except: await bot.send_message(event.chat_id, header, buttons=btns)

def register_admin(bot):
    @bot.on(events.NewMessage(pattern=r"(?i)^(🔐 𝐀ᴅᴍɪɴ 𝐏ᴀɴᴇʟ|🔐 Admin Panel)$"))
    async def msg_admin(e):
        await admin_panel_handler(e)
