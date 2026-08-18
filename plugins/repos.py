#MADE_BY_MADARA
#TRUE LODA LOVE

import os
from telethon import events, Button
from telethon.errors import MessageNotModifiedError
from database import cur, db
from config import PE_LIGHTNING, PE_CHECK, PE_GIFT, P_MONEY, P_INR, P_NO, P_YES, P_WARN, P_PC, bot, logger
from utils.keyboards import style_btn
from utils.states import get_user_lock

async def show_repos(event):
    rows = cur.execute("SELECT id, name, description, price FROM repos WHERE available=1 ORDER BY id DESC").fetchall()
    if not rows:
        msg = (f"<blockquote>💻 <b>𝐁ᴏᴛ 𝐑ᴇᴘᴏs</b></blockquote>\n\n"
               f"<blockquote>{P_WARN} 𝐍ᴏ ʀᴇᴘᴏs ᴀᴠᴀɪʟᴀʙʟᴇ ʀɪɢʜᴛ ɴᴏᴡ. 𝐂ʜᴇᴄᴋ ʙᴀᴄᴋ ʟᴀᴛᴇʀ!</blockquote>")
        if isinstance(event, events.CallbackQuery.Event):
            try: return await event.edit(msg)
            except MessageNotModifiedError: pass
        else: return await event.respond(msg)
        return

    msg = (f"<blockquote>💻 <b>𝐁ᴏᴛ 𝐑ᴇᴘᴏs</b>\n\n"
           f"𝐒ᴇʟᴇᴄᴛ ᴀ ʀᴇᴘᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴘᴜʀᴄʜᴀsᴇ:</blockquote>")
    btns = []
    for rid, name, desc, price in rows:
        btns.append([style_btn(f"💻 {name} — {P_INR}{price}", f"repo_view|{rid}", "primary", icon=5409098988156629257)])

    if isinstance(event, events.CallbackQuery.Event):
        try: await event.edit(msg, buttons=btns)
        except MessageNotModifiedError: pass
    else:
        await event.respond(msg, buttons=btns)

async def show_repo_detail(event, repo_id):
    row = cur.execute("SELECT id, name, description, price FROM repos WHERE id=? AND available=1", (repo_id,)).fetchone()
    if not row:
        return await event.answer("❌ Repo not found or unavailable.", alert=True)
    rid, name, desc, price = row

    msg = (f"<blockquote>💻 <b>{name}</b>\n\n"
           f"📝 <b>𝐃ᴇsᴄʀɪᴘᴛɪᴏɴ:</b> {desc}\n\n"
           f"{P_MONEY} <b>𝐏ʀɪᴄᴇ:</b> {P_INR}{price}</blockquote>\n\n"
           f"<blockquote>📦 𝐏ᴜʀᴄʜᴀsᴇ ᴛʜɪs ʀᴇᴘᴏ ᴛᴏ ɪɴsᴛᴀɴᴛʟʏ ʀᴇᴄᴇɪᴠᴇ ᴛʜᴇ 𝐙𝐈𝐏 ғɪʟᴇ!</blockquote>")
    btns = [
        [style_btn(f"✅ 𝐁ᴜʏ ғᴏʀ {P_INR}{price}", f"repo_cf|{rid}", "success", icon=5409320020058584473)],
        [style_btn("🔙 𝐁ᴀᴄᴋ", b"repo_list", "danger", icon=6129812419028982717)]
    ]
    try: await event.edit(msg, buttons=btns)
    except MessageNotModifiedError: pass

async def process_repo_purchase(event, repo_id):
    uid = event.sender_id
    row = cur.execute("SELECT id, name, price, zip_file FROM repos WHERE id=? AND available=1", (repo_id,)).fetchone()
    if not row:
        return await event.answer("❌ Repo not found.", alert=True)
    rid, name, price, zip_file = row

    async with get_user_lock(uid):
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ?", (price, uid, price))
        if cur.rowcount == 0:
            return await event.answer("❌ Insufficient Balance!", alert=True)
        cur.execute("INSERT INTO repo_orders (user_id, repo_id, repo_name, price) VALUES (?,?,?,?)", (uid, rid, name, price))
        db.commit()

    await event.edit(f"{PE_LIGHTNING} <b>𝐏ʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴏʀᴅᴇʀ...</b>\n𝐏ʟᴇᴀsᴇ ᴡᴀɪᴛ ᴡʜɪʟᴇ ᴡᴇ sᴇɴᴅ ʏᴏᴜʀ ғɪʟᴇ.")

    try:
        if not zip_file or not os.path.exists(zip_file):
            async with get_user_lock(uid):
                cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (price, uid))
                db.commit()
            return await event.edit(f"{P_NO} <b>Repo file not found. Your balance has been refunded.</b>")

        caption = (f"<blockquote>{PE_CHECK} <b>𝐏ᴜʀᴄʜᴀsᴇ 𝐒ᴜᴄᴄᴇssғᴜʟ!</b>\n\n"
                   f"💻 <b>𝐑ᴇᴘᴏ:</b> {name}\n"
                   f"{P_MONEY} <b>𝐏ᴀɪᴅ:</b> {P_INR}{price}\n\n"
                   f"📦 𝐇ᴇʀᴇ ɪs ʏᴏᴜʀ ᴢɪᴘ ғɪʟᴇ! 𝐄ɴᴊᴏʏ 🎉</blockquote>")
        await bot.send_file(uid, zip_file, caption=caption)
        await event.edit(f"{PE_CHECK} <b>𝐏ᴜʀᴄʜᴀsᴇ 𝐒ᴜᴄᴄᴇssғᴜʟ!</b>\n💻 <b>{name}</b> ʜᴀs ʙᴇᴇɴ sᴇɴᴛ ᴛᴏ ʏᴏᴜ ᴠɪᴀ ᴅᴍ!")
    except Exception as ex:
        logger.error(f"Repo send error: {ex}")
        async with get_user_lock(uid):
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (price, uid))
            db.commit()
        await event.edit(f"{P_NO} <b>Failed to send repo. Your balance has been refunded.</b>")

def register_repos(bot):
    @bot.on(events.NewMessage(pattern=r"(?i)^(📁 𝐁ᴏᴛ 𝐑ᴇᴘᴏs|📁 Bot Repos)$"))
    async def msg_repos(e):
        await show_repos(e)

    @bot.on(events.CallbackQuery(pattern=b"^repo_list$"))
    async def cb_repo_list(e):
        await show_repos(e)

    @bot.on(events.CallbackQuery(pattern=r"^repo_view\|(\d+)$"))
    async def cb_repo_view(e):
        repo_id = int(e.pattern_match.group(1).decode())
        await show_repo_detail(e, repo_id)

    @bot.on(events.CallbackQuery(pattern=r"^repo_cf\|(\d+)$"))
    async def cb_repo_cf(e):
        repo_id = int(e.pattern_match.group(1).decode())
        await process_repo_purchase(e, repo_id)
