import os
import asyncio
import time
import zipfile
import re
from telethon import events, Button, TelegramClient, types
from telethon.errors import MessageNotModifiedError
from database import cur, db, get_flag_by_country_name
from config import PE_LOCATION, PE_GIFT, PE_LIGHTNING, PE_CHECK, P_MONEY, P_PKG, P_CARD, P_WARN, P_NO, P_YES, P_INR, P_TIME, P_FLAG, P_OTP, P_2FA, P_PHONE, AUTO_CANCEL_SECONDS, OTP_REGEX, bot, logger, API_ID, API_HASH
from utils.keyboards import style_btn
from utils.states import active_orders, session_buy_state, get_user_lock

async def show_countries(event, mode, page):
    limit = 12
    offset = (page - 1) * limit
    rows = cur.execute("SELECT country_name, COUNT(*) FROM stock WHERE available=1 GROUP BY country_name").fetchall()
    total = len(rows)
    countries = rows[offset:offset+limit]
    
    if not countries:
        return await event.respond(f"{P_WARN} 𝐍ᴏ sᴛᴏᴄᴋ ᴀᴠᴀɪʟᴀʙʟᴇ ᴀᴛ ᴛʜᴇ ᴍᴏᴍᴇɴᴛ. 𝐏ʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ʙᴀᴄᴋ ʟᴀᴛᴇʀ!")

    btns = []
    for c_name, count in countries:
        flag = get_flag_by_country_name(c_name)
        btns.append(style_btn(f"{flag} {c_name} ({count})", f"bc|{mode}|{c_name}", "primary", icon=6154249597532248059))
        
    f_btns = [btns[i:i+2] for i in range(0, len(btns), 2)]
    
    nav = []
    if page > 1: nav.append(style_btn("𝐏ʀᴇᴠ", f"pg_c|{mode}|{page-1}", "primary", icon=6129627894349045589))
    if offset + limit < total: nav.append(style_btn("𝐍ᴇxᴛ", f"pg_c|{mode}|{page+1}", "primary", icon=6129732880529628243))
    if nav: f_btns.append(nav)
    
    msg = f"<blockquote>{PE_LOCATION} <b>𝐒ᴇʟᴇᴄᴛ ᴀ 𝐂ᴏᴜɴᴛʀʏ:</b> (𝐏ᴀɢᴇ {page})"
    if isinstance(event, events.CallbackQuery.Event):
        try: await event.edit(msg, buttons=f_btns)
        except MessageNotModifiedError: pass
    else: await event.respond(msg, buttons=f_btns)

async def show_years(event, mode, country):
    years = cur.execute("SELECT account_year, COUNT(*), price FROM stock WHERE country_name=? AND available=1 GROUP BY account_year, price", (country,)).fetchall()
    if not years: return await event.edit(f"{P_WARN} 𝐍ᴏ sᴛᴏᴄᴋ ʟᴇғᴛ ғᴏʀ {country}.")
    
    flag = get_flag_by_country_name(country)
    btns = []
    for y, count, price in years:
        btns.append([style_btn(f"{y} - {P_INR}{price} ({count} left)", f"by|{mode}|{country}|{y}|{price}", "primary", icon=5408995930416362034)])
    btns.append([style_btn("𝐁ᴀᴄᴋ", f"pg_c|{mode}|1", "danger", icon=6129812419028982717)])
    await event.edit(f"<blockquote>{flag} <b>𝐒ᴇʟᴇᴄᴛ 𝐘ᴇᴀʀ & 𝐏ʀɪᴄᴇ ғᴏʀ {country}:</b></blockquote>", buttons=btns)

async def confirm_purchase(event, country, year, price):
    msg = f"<blockquote>{PE_GIFT} <b>𝐂ᴏɴғɪʀᴍ 𝐏ᴜʀᴄʜᴀsᴇ</b>\n\n{P_FLAG} 𝐂ᴏᴜɴᴛʀʏ: {country}\n📆 𝐘ᴇᴀʀ: {year}\n{P_MONEY} 𝐏ʀɪᴄᴇ: {P_INR}{price}\n\n𝐀ʀᴇ ʏᴏᴜ sᴜʀᴇ?"
    btns = [
        [style_btn("𝐂ᴏɴғɪʀᴍ 𝐁ᴜʏ", f"buy_cf|{country}|{year}|{price}", "success", icon=5409320020058584473)],
        [style_btn("𝐂ᴀɴᴄᴇʟ", "cancel_action", "danger", icon=6129888444245089008)]
    ]
    await event.edit(msg, buttons=btns)

async def process_purchase(event, country, year, price_str):
    uid, price = event.sender_id, int(price_str)
    
    async with get_user_lock(uid):
        row = cur.execute("SELECT phone, session_file, twofa FROM stock WHERE country_name=? AND account_year=? AND price=? AND available=1 LIMIT 1", (country, int(year), price)).fetchone()
        if not row: return await event.answer("❌ Out of stock!", alert=True)
        
        phone, sess, twofa_pass = row
        
        disc_row = cur.execute("SELECT discount FROM users WHERE user_id=?", (uid,)).fetchone()
        discount = disc_row[0] if disc_row else 0
        final_price = price if discount == 0 else int(price * (100 - discount) / 100)
        
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ?", (final_price, uid, final_price))
        if cur.rowcount == 0: return await event.answer("❌ Insufficient Balance!", alert=True)
        
        cur.execute("UPDATE stock SET available=0 WHERE phone=?", (phone,))
        db.commit()

    await event.edit(f"{PE_LIGHTNING} <b>𝐏ʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴏʀᴅᴇʀ...</b>\n𝐏ʟᴇᴀsᴇ ᴡᴀɪᴛ ᴡʜɪʟᴇ ᴡᴇ ɪɴɪᴛɪᴀʟɪᴢᴇ ᴛʜᴇ sᴇssɪᴏɴ.")
    
    client = TelegramClient(sess, API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise Exception("Session expired or not authorized")
    except Exception as e:
        logger.error(f"Client init error: {e}")
        try: await client.disconnect()
        except: pass
        async with get_user_lock(uid):
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (final_price, uid))
            cur.execute("UPDATE stock SET available=1 WHERE phone=?", (phone,))
            db.commit()
        return await event.edit(f"{P_NO} <b>Error initializing account.</b> Money refunded.")

    c_icon = get_flag_by_country_name(country)
    actual_year = int(year)
    msg = (f"<blockquote expandable>{PE_LIGHTNING} <b>𝐎ʀᴅᴇʀ 𝐀ᴄᴛɪᴠᴇ!</b>\n\n"
           f"{P_PHONE} <b>𝐏ʜᴏɴᴇ:</b> <code>{phone}</code>\n"
           f"{P_FLAG} <b>𝐂ᴏᴜɴᴛʀʏ:</b> {c_icon} {country}\n\n"
           f"🔻 <b>𝐈ɴsᴛʀᴜᴄᴛɪᴏɴs:</b>\n"
           f"1. 𝐎ᴘᴇɴ 𝐓ᴇʟᴇɢʀᴀᴍ & 𝐀ᴅᴅ 𝐀ᴄᴄᴏᴜɴᴛ\n"
           f"2. 𝐄ɴᴛᴇʀ ᴛʜᴇ ɴᴜᴍʙᴇʀ ᴀʙᴏᴠᴇ.\n"
           f"3. ⏳ <b>𝐏ʟᴇᴀsᴇ ᴡᴀɪᴛ!</b> 𝐓ʜᴇ ʙᴏᴛ ɪs ᴀᴄᴛɪᴠᴇʟʏ ʟɪsᴛᴇɴɪɴɢ ғᴏʀ ʏᴏᴜʀ 𝐎𝐓𝐏 ᴀɴᴅ ᴡɪʟʟ sᴇɴᴅ ɪᴛ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴏɴᴄᴇ 𝐓ᴇʟᴇɢʀᴀᴍ ᴅᴇʟɪᴠᴇʀs ɪᴛ.\n\n"
           f"<i>𝐍ᴏᴛᴇ: 𝐈ғ ɴᴏ 𝐎𝐓𝐏 ɪs ʀᴇᴄᴇɪᴠᴇᴅ ᴡɪᴛʜɪɴ 10 ᴍɪɴᴜᴛᴇs, ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴀᴜᴛᴏ-ᴄᴀɴᴄᴇʟ ᴀɴᴅ ʀᴇғᴜɴᴅ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ.</i>")
    
    sent_msg = await event.edit(msg)
    
    active_orders[phone] = {
        'uid': uid, 'client': client, 'sess': sess, 'start_time': time.time(), 
        'paid': False, 'price': final_price, 'country': country, 'year': actual_year, 
        'c_icon': c_icon, 'twofa': twofa_pass, 'msg_id': sent_msg.id
    }
    asyncio.create_task(auto_otp_task(phone))

async def auto_otp_task(phone):
    if phone not in active_orders: return
    
    order = active_orders[phone]
    client = order['client']
    start_time = order['start_time']
    uid = order['uid']
    msg_id = order['msg_id']
    
    while time.time() - start_time < AUTO_CANCEL_SECONDS:
        if phone not in active_orders: return 
        try:
            try:
                peer = await client.get_input_entity(777000)
            except Exception:
                peer = types.InputPeerUser(user_id=777000, access_hash=0)
            msgs = await client.get_messages(peer, limit=5)
            code = None
            for m in msgs:
                if m.date.timestamp() > start_time - 10: 
                    if m.message and re.search(OTP_REGEX, m.message) and "Login detected" not in m.message:
                        code = re.search(OTP_REGEX, m.message).group()
                        break
            
            if code:
                if not order['paid']:
                    order['paid'] = True
                    async with get_user_lock(uid):
                        cur.execute("INSERT INTO orders (user_id, country, year, price, phone, otp) VALUES (?,?,?,?,?,?)", (uid, order['country'], order['year'], order['price'], phone, code))
                        cur.execute("DELETE FROM stock WHERE phone=?", (phone,))
                        db.commit()
                
                twofa_text = f"{P_2FA} <b>2FA:</b> <code>{order['twofa']}</code>" if order['twofa'] != "None" else f"🔓 <b>2FA:</b> <code>Disabled (No Password)</code>"
                msg_text = (f"<blockquote>{PE_CHECK} <b>𝐋ᴀᴛᴇsᴛ 𝐎𝐓𝐏 𝐅ᴇᴛᴄʜᴇᴅ!</b>\n\n"
                            f"{P_PHONE} <b>𝐏ʜᴏɴᴇ:</b> <code>{phone}</code>\n"
                            f"{P_FLAG} <b>𝐂ᴏᴜɴᴛʀʏ:</b> {order['c_icon']} {order['country']}\n"
                            f"{P_OTP} <b>𝐎𝐓𝐏:</b> <code><tg-spoiler>{code}</tg-spoiler>\n"
                            f"{twofa_text}</blockquote>")
                
                try: await bot.edit_message(uid, msg_id, msg_text, buttons=[[Button.inline("🔄 𝐆ᴇᴛ 𝐎𝐓𝐏 𝐀ɢᴀɪɴ", f"get_otp_again|{phone}")], [style_btn("🚪 𝐅ɪɴɪsʜ & 𝐋ᴏɢᴏᴜᴛ", f"logout_bot|{phone}", "danger", icon=6129627894349045589)]])
                except MessageNotModifiedError: pass
                return 
        except Exception as ex:
            logger.error(f"OTP fetch error for {phone}: {ex}")
        await asyncio.sleep(6) 
        
    if phone in active_orders and not active_orders[phone]['paid']:
        order = active_orders.pop(phone)
        try: await order['client'].disconnect()
        except: pass
        
        async with get_user_lock(uid):
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (order['price'], uid))
            cur.execute("UPDATE stock SET available=1 WHERE phone=?", (phone,))
            db.commit()
            
        try: await bot.edit_message(uid, msg_id, f"{P_TIME} <b>𝐎ʀᴅᴇʀ 𝐄xᴘɪʀᴇᴅ!</b>\n𝐓ʜᴇ 10-ᴍɪɴᴜᴛᴇ ʟɪᴍɪᴛ ғᴏʀ <code>{phone}</code> ʀᴀɴ ᴏᴜᴛ. 𝐘ᴏᴜʀ ᴍᴏɴᴇʏ ({P_INR}{order['price']}) ʜᴀs ʙᴇᴇɴ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ʀᴇғᴜɴᴅᴇᴅ.")
        except: pass

def register_buy(bot):
    @bot.on(events.NewMessage(pattern=r"(?i)^(🛒 𝐁ᴜʏ 𝐀ᴄᴄᴏᴜɴᴛ|🛒 Buy Account|📁 Buy Sessions)$"))
    async def msg_buy(e):
        mode = 'single' if 'Account' in e.text else 'bulk'
        await show_countries(e, mode, 1)

    @bot.on(events.CallbackQuery(pattern=r"^bc\|(.+)\|(.+)$"))
    async def cb_bc(e):
        p = e.pattern_match
        await show_years(e, p.group(1).decode(), p.group(2).decode())

    @bot.on(events.CallbackQuery(pattern=r"^pg_c\|(.+)\|(\d+)$"))
    async def cb_pg_c(e):
        p = e.pattern_match
        await show_countries(e, p.group(1).decode(), int(p.group(2).decode()))

    @bot.on(events.CallbackQuery(pattern=r"^by\|(.+)\|(.+)\|(\d+)\|(\d+)$"))
    async def cb_by_single(e):
        p = e.pattern_match
        await confirm_purchase(e, p.group(2).decode(), p.group(3).decode(), p.group(4).decode())
        
    @bot.on(events.CallbackQuery(pattern=r"^buy_cf\|(.+)\|(\d+)\|(\d+)$"))
    async def cb_buy_cf(e):
        p = e.pattern_match
        import config # dynamic import for API keys if needed
        await process_purchase(e, p.group(1).decode(), p.group(2).decode(), p.group(3).decode())

    @bot.on(events.CallbackQuery(pattern=r"^get_otp_again\|(.+)$"))
    async def cb_get_otp_again(e):
        phone = e.pattern_match.group(1).decode()
        if phone not in active_orders: return await e.answer("⚠️ Session expired.", alert=True)
        await e.answer("🔄 Fetching latest OTP...")
        order = active_orders[phone]
        client = order['client']
        uid = order['uid']
        msg_id = order['msg_id']
        try:
            try:
                peer = await client.get_input_entity(777000)
            except Exception:
                peer = types.InputPeerUser(user_id=777000, access_hash=0)
            msgs = await client.get_messages(peer, limit=5)
            code = None
            for m in msgs:
                if m.date.timestamp() > order['start_time'] - 10:
                    if m.message and re.search(OTP_REGEX, m.message) and "Login detected" not in m.message:
                        code = re.search(OTP_REGEX, m.message).group()
                        break
            if code:
                if not order['paid']:
                    order['paid'] = True
                    async with get_user_lock(uid):
                        cur.execute("INSERT INTO orders (user_id, country, year, price, phone, otp) VALUES (?,?,?,?,?,?)", (uid, order['country'], order['year'], order['price'], phone, code))
                        cur.execute("DELETE FROM stock WHERE phone=?", (phone,))
                        db.commit()
                twofa_text = f"{P_2FA} <b>2FA:</b> <code>{order['twofa']}</code>" if order['twofa'] != "None" else f"🔓 <b>2FA:</b> <code>Disabled (No Password)</code>"
                msg_text = (f"<blockquote>{PE_CHECK} <b>𝐋ᴀᴛᴇsᴛ 𝐎𝐓𝐏 𝐅ᴇᴛᴄʜᴇᴅ!</b>\n\n"
                            f"{P_PHONE} <b>𝐏ʜᴏɴᴇ:</b> <code>{phone}</code>\n"
                            f"{P_FLAG} <b>𝐂ᴏᴜɴᴛʀʏ:</b> {order['c_icon']} {order['country']}\n"
                            f"{P_OTP} <b>𝐎𝐓𝐏:</b> <code><tg-spoiler>{code}</tg-spoiler>\n"
                            f"{twofa_text}</blockquote>")
                try: await bot.edit_message(uid, msg_id, msg_text, buttons=[[Button.inline("🔄 𝐆ᴇᴛ 𝐎𝐓𝐏 𝐀ɢᴀɪɴ", f"get_otp_again|{phone}")], [style_btn("🚪 𝐅ɪɴɪsʜ & 𝐋ᴏɢᴏᴜᴛ", f"logout_bot|{phone}", "danger", icon=6129627894349045589)]])
                except MessageNotModifiedError: pass
            else:
                await e.answer("⚠️ No new OTP found yet. Try again in a few seconds.", alert=True)
        except Exception as ex:
            logger.error(f"Manual OTP fetch error for {phone}: {ex}")
            await e.answer("❌ Error fetching OTP. Check logs.", alert=True)
        
    @bot.on(events.CallbackQuery(pattern=r"^logout_bot\|(.+)$"))
    async def cb_logout_bot(e):
        phone = e.pattern_match.group(1).decode()
        if phone in active_orders:
            order = active_orders.pop(phone)
            try: await order['client'].log_out()
            except: pass
            try: await order['client'].disconnect()
            except: pass
            for ext in ['.session', '.session-wal', '.session-shm', '.session-journal']:
                if os.path.exists(order['sess'] + ext): os.remove(order['sess'] + ext)
            await e.edit(f"{P_YES} <b>Session Finished & Logged out successfully.</b>")
        else:
            await e.answer("⚠️ No active order found or already logged out.", alert=True)


