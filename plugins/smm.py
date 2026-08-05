import os
import aiohttp
import asyncio
import html
from telethon import events, Button
from telethon.errors import MessageNotModifiedError
from database import cur, db
from config import PE_LIGHTNING, PE_CHECK, PE_GIFT, P_MONEY, P_INR, P_NO, P_YES, P_WARN, P_CART, P_STATS, bot, logger
from utils.keyboards import style_btn
from utils.states import get_user_lock

FANSMM_URL = "https://fansmm.in/api/v2"

def get_api_key():
    return os.getenv("FANSMM_API_KEY", "")

async def fansmm_request(params: dict):
    """Make a POST request to FanSMM API."""
    api_key = get_api_key()
    if not api_key:
        raise Exception("FANSMM_API_KEY not configured")
    params["key"] = api_key
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(FANSMM_URL, data=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                return await resp.json()
    except Exception as e:
        logger.error(f"FanSMM API error: {e}")
        raise

# ── Category browsing ──

async def show_smm_categories(event):
    rows = cur.execute("SELECT DISTINCT category FROM smm_services WHERE available=1 ORDER BY category").fetchall()
    if not rows:
        msg = (f"<blockquote>📊 <b>𝐒𝐌𝐌 𝐒ᴇʀᴠɪᴄᴇs</b></blockquote>\n\n"
               f"<blockquote>{P_WARN} 𝐍ᴏ sᴇʀᴠɪᴄᴇs ᴀᴠᴀɪʟᴀʙʟᴇ ʏᴇᴛ. 𝐂ʜᴇᴄᴋ ʙᴀᴄᴋ ʟᴀᴛᴇʀ!</blockquote>")
        if isinstance(event, events.CallbackQuery.Event):
            try: return await event.edit(msg)
            except MessageNotModifiedError: pass
        else: return await event.respond(msg)
        return

    btns = []
    for (cat,) in rows:
        count = cur.execute("SELECT COUNT(*) FROM smm_services WHERE category=? AND available=1", (cat,)).fetchone()[0]
        btns.append([style_btn(f"📌 {cat} ({count})", f"smm_cat|{cat}", "primary", icon=5409098988156629257)])

    msg = (f"<blockquote>📊 <b>𝐒𝐌𝐌 𝐒ᴇʀᴠɪᴄᴇs</b>\n\n"
           f"⚡ 𝐈ɴsᴛᴀɴᴛ ᴅᴇʟɪᴠᴇʀʏ | 🔒 𝐒ᴀғᴇ & 𝐑ᴇʟɪᴀʙʟᴇ\n\n"
           f"𝐒ᴇʟᴇᴄᴛ ᴀ ᴄᴀᴛᴇɢᴏʀʏ ʙᴇʟᴏᴡ:</blockquote>")

    if isinstance(event, events.CallbackQuery.Event):
        try: await event.edit(msg, buttons=btns)
        except MessageNotModifiedError: pass
    else:
        await event.respond(msg, buttons=btns)

async def show_smm_services(event, category):
    rows = cur.execute(
        "SELECT id, name, min_qty, max_qty, price_per_1000 FROM smm_services WHERE category=? AND available=1 ORDER BY id",
        (category,)
    ).fetchall()
    if not rows:
        return await event.answer("No services in this category.", alert=True)

    btns = []
    for sid, name, min_q, max_q, price in rows:
        cost_min = round(min_q * price / 1000, 2)
        btns.append([style_btn(f"⚡ {name[:35]} — {P_INR}{price}/1K", f"smm_svc|{sid}", "primary", icon=5409271925014801629)])
    btns.append([style_btn("🔙 𝐁ᴀᴄᴋ", b"smm_cats", "danger", icon=6129812419028982717)])

    msg = f"<blockquote>📌 <b>{category}</b>\n\n𝐒ᴇʟᴇᴄᴛ ᴀ sᴇʀᴠɪᴄᴇ:</blockquote>"
    try: await event.edit(msg, buttons=btns)
    except MessageNotModifiedError: pass

async def show_smm_service_detail(event, svc_id):
    row = cur.execute(
        "SELECT id, name, category, min_qty, max_qty, price_per_1000, description FROM smm_services WHERE id=? AND available=1",
        (svc_id,)
    ).fetchone()
    if not row:
        return await event.answer("Service not found.", alert=True)
    sid, name, cat, min_q, max_q, price, desc = row

    msg = (f"<blockquote>⚡ <b>{name}</b>\n\n"
           f"📌 <b>𝐂ᴀᴛᴇɢᴏʀʏ:</b> {cat}\n"
           f"{P_MONEY} <b>𝐏ʀɪᴄᴇ:</b> {P_INR}{price} / 1000\n"
           f"📉 <b>𝐌ɪɴ:</b> {min_q} | 📈 <b>𝐌ᴀx:</b> {max_q}</blockquote>\n\n"
           f"<blockquote>📝 {desc}</blockquote>\n\n"
           f"<blockquote>💬 𝐓ᴀᴘ <b>𝐎ʀᴅᴇʀ</b> ᴀɴᴅ sᴇɴᴅ ʏᴏᴜʀ <b>ʟɪɴᴋ</b> + <b>ǫᴜᴀɴᴛɪᴛʏ</b>.</blockquote>")
    btns = [
        [style_btn(f"🛒 𝐎ʀᴅᴇʀ 𝐍ᴏᴡ", f"smm_order|{sid}", "success", icon=5409320020058584473)],
        [style_btn("🔙 𝐁ᴀᴄᴋ", f"smm_cat|{cat}", "danger", icon=6129812419028982717)]
    ]
    try: await event.edit(msg, buttons=btns)
    except MessageNotModifiedError: pass

# ── Order states ──
smm_order_state = {}

async def start_smm_order(event, svc_id):
    uid = event.sender_id
    row = cur.execute("SELECT id, name, min_qty, max_qty, price_per_1000 FROM smm_services WHERE id=? AND available=1", (svc_id,)).fetchone()
    if not row:
        return await event.answer("Service not found.", alert=True)
    sid, name, min_q, max_q, price = row
    smm_order_state[uid] = {"step": "link", "svc_id": sid, "name": name, "min_q": min_q, "max_q": max_q, "price": price}
    await event.edit(
        f"<blockquote>⚡ <b>{name}</b></blockquote>\n\n"
        f"<blockquote>🔗 <b>𝐒ᴛᴇᴘ 1:</b> 𝐒ᴇɴᴅ ʏᴏᴜʀ <b>ʟɪɴᴋ</b> (ᴇ.ɢ. ɪɴsᴛᴀɢʀᴀᴍ ᴘʀᴏғɪʟᴇ ᴏʀ ᴘᴏsᴛ ᴜʀʟ):</blockquote>",
        buttons=[[Button.inline("❌ 𝐂ᴀɴᴄᴇʟ", b"smm_cancel")]]
    )

def register_smm(bot):
    @bot.on(events.NewMessage(pattern=r"(?i)^(📊 𝐒𝐌𝐌 𝐒ᴇʀᴠɪᴄᴇs|📊 SMM Services)$"))
    async def msg_smm(e):
        await show_smm_categories(e)

    @bot.on(events.CallbackQuery(pattern=b"^smm_cats$"))
    async def cb_smm_cats(e):
        await show_smm_categories(e)

    @bot.on(events.CallbackQuery(pattern=r"^smm_cat\|(.+)$"))
    async def cb_smm_cat(e):
        cat = e.pattern_match.group(1).decode()
        await show_smm_services(e, cat)

    @bot.on(events.CallbackQuery(pattern=r"^smm_svc\|(\d+)$"))
    async def cb_smm_svc(e):
        svc_id = int(e.pattern_match.group(1).decode())
        await show_smm_service_detail(e, svc_id)

    @bot.on(events.CallbackQuery(pattern=r"^smm_order\|(\d+)$"))
    async def cb_smm_order(e):
        svc_id = int(e.pattern_match.group(1).decode())
        await start_smm_order(e, svc_id)

    @bot.on(events.CallbackQuery(pattern=b"^smm_cancel$"))
    async def cb_smm_cancel(e):
        uid = e.sender_id
        smm_order_state.pop(uid, None)
        try: await e.delete()
        except: pass
        await e.answer("Cancelled.", alert=False)

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in smm_order_state))
    async def msg_smm_flow(e):
        uid = e.sender_id
        st = smm_order_state.get(uid)
        if not st: return
        text = (e.text or "").strip()
        if text.lower() == "/cancel":
            smm_order_state.pop(uid, None)
            return await e.reply(f"{P_NO} Cancelled.")

        if st["step"] == "link":
            if not text.startswith("http"):
                return await e.reply(f"{P_WARN} Please send a valid URL starting with <code>http</code>.")
            st["link"] = text
            st["step"] = "qty"
            smm_order_state[uid] = st
            return await e.reply(
                f"<blockquote>📊 <b>𝐒ᴛᴇᴘ 2:</b> 𝐄ɴᴛᴇʀ <b>ǫᴜᴀɴᴛɪᴛʏ</b>:\n\n"
                f"📉 𝐌ɪɴ: <b>{st['min_q']}</b> | 📈 𝐌ᴀx: <b>{st['max_q']}</b></blockquote>",
                buttons=[[Button.inline("❌ 𝐂ᴀɴᴄᴇʟ", b"smm_cancel")]]
            )

        if st["step"] == "qty":
            try:
                qty = int(text)
            except ValueError:
                return await e.reply(f"{P_WARN} Please enter a valid number.")
            if qty < st["min_q"] or qty > st["max_q"]:
                return await e.reply(f"{P_WARN} Quantity must be between <b>{st['min_q']}</b> and <b>{st['max_q']}</b>.")
            total_cost = round(qty * st["price"] / 1000)
            if total_cost < 1:
                total_cost = 1
            st["qty"] = qty
            st["total_cost"] = total_cost
            st["step"] = "confirm"
            smm_order_state[uid] = st

            confirm_msg = (
                f"<blockquote>{PE_GIFT} <b>𝐎ʀᴅᴇʀ 𝐒ᴜᴍᴍᴀʀʏ</b>\n\n"
                f"⚡ <b>𝐒ᴇʀᴠɪᴄᴇ:</b> {st['name']}\n"
                f"🔗 <b>𝐋ɪɴᴋ:</b> <code>{html.escape(st['link'])}</code>\n"
                f"📊 <b>𝐐ᴛʏ:</b> {qty}\n"
                f"{P_MONEY} <b>𝐂ᴏsᴛ:</b> {P_INR}{total_cost}</blockquote>\n\n"
                f"<blockquote>✅ 𝐂ᴏɴғɪʀᴍ ᴛᴏ ᴘʟᴀᴄᴇ ʏᴏᴜʀ ᴏʀᴅᴇʀ!</blockquote>"
            )
            return await e.reply(confirm_msg, buttons=[
                [style_btn(f"✅ 𝐂ᴏɴғɪʀᴍ ({P_INR}{total_cost})", b"smm_confirm", "success", icon=5409320020058584473)],
                [style_btn("❌ 𝐂ᴀɴᴄᴇʟ", b"smm_cancel", "danger", icon=6129888444245089008)]
            ])

    @bot.on(events.CallbackQuery(pattern=b"^smm_confirm$"))
    async def cb_smm_confirm(e):
        uid = e.sender_id
        st = smm_order_state.get(uid)
        if not st or st.get("step") != "confirm":
            return await e.answer("Session expired. Please start again.", alert=True)

        svc_row = cur.execute(
            "SELECT fansmm_service_id FROM smm_services WHERE id=? AND available=1", (st["svc_id"],)
        ).fetchone()
        if not svc_row:
            smm_order_state.pop(uid, None)
            return await e.answer("Service no longer available.", alert=True)

        total_cost = st["total_cost"]
        async with get_user_lock(uid):
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ?", (total_cost, uid, total_cost))
            if cur.rowcount == 0:
                return await e.answer("❌ Insufficient Balance!", alert=True)
            db.commit()

        smm_order_state.pop(uid, None)
        await e.edit(f"{PE_LIGHTNING} <b>𝐏ʟᴀᴄɪɴɢ ʏᴏᴜʀ ᴏʀᴅᴇʀ...</b>")

        try:
            result = await fansmm_request({
                "action": "add",
                "service": svc_row[0],
                "link": st["link"],
                "quantity": st["qty"]
            })
            fansmm_order_id = result.get("order", "N/A")
            error = result.get("error")
            if error:
                raise Exception(error)

            cur.execute(
                "INSERT INTO smm_orders (user_id, service_id, service_name, link, quantity, price, fansmm_order_id, status) VALUES (?,?,?,?,?,?,?,?)",
                (uid, st["svc_id"], st["name"], st["link"], st["qty"], total_cost, str(fansmm_order_id), "pending")
            )
            db.commit()
            await e.edit(
                f"<blockquote>{PE_CHECK} <b>𝐎ʀᴅᴇʀ 𝐏ʟᴀᴄᴇᴅ!</b>\n\n"
                f"⚡ <b>𝐒ᴇʀᴠɪᴄᴇ:</b> {st['name']}\n"
                f"📊 <b>𝐐ᴛʏ:</b> {st['qty']}\n"
                f"{P_MONEY} <b>𝐏ᴀɪᴅ:</b> {P_INR}{total_cost}\n"
                f"🆔 <b>𝐎ʀᴅᴇʀ 𝐈𝐃:</b> <code>{fansmm_order_id}</code>\n\n"
                f"<i>Your order is being processed. Use /smm_status {fansmm_order_id} to check status.</i></blockquote>"
            )
        except Exception as ex:
            logger.error(f"SMM order error: {ex}")
            async with get_user_lock(uid):
                cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (total_cost, uid))
                db.commit()
            await e.edit(f"{P_NO} <b>Order failed: {html.escape(str(ex))}\nYour balance has been refunded.</b>")

    @bot.on(events.NewMessage(pattern=r"^/smm_status (\d+)$"))
    async def cmd_smm_status(e):
        order_id = e.pattern_match.group(1)
        uid = e.sender_id
        row = cur.execute("SELECT service_name, quantity, price, status FROM smm_orders WHERE fansmm_order_id=? AND user_id=?", (order_id, uid)).fetchone()
        if not row:
            return await e.reply(f"{P_WARN} Order not found.")
        svc_name, qty, price, status = row
        try:
            result = await fansmm_request({"action": "status", "order": order_id})
            live_status = result.get("status", status)
            remains = result.get("remains", "?")
            cur.execute("UPDATE smm_orders SET status=? WHERE fansmm_order_id=?", (live_status, order_id))
            db.commit()
            await e.reply(
                f"<blockquote>📊 <b>𝐎ʀᴅᴇʀ 𝐒𝐭𝐚𝐭𝐮𝐬</b>\n\n"
                f"🆔 <b>ID:</b> <code>{order_id}</code>\n"
                f"⚡ <b>𝐒ᴇʀᴠɪᴄᴇ:</b> {svc_name}\n"
                f"📊 <b>𝐐ᴛʏ:</b> {qty} | 🔄 𝐑ᴇᴍᴀɪɴs: {remains}\n"
                f"{P_MONEY} <b>𝐏ᴀɪᴅ:</b> {P_INR}{price}\n"
                f"✅ <b>𝐒𝐭𝐚𝐭𝐮𝐬:</b> {live_status}</blockquote>"
            )
        except Exception as ex:
            await e.reply(f"{P_WARN} Could not fetch live status. Last known: <b>{status}</b>")
