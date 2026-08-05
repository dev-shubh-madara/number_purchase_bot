import os
import re
import time
import asyncio
import csv
import zipfile
import shutil
import html
from telethon import events, Button, TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError, UserIsBlockedError, InputUserDeactivatedError
from telethon.tl.functions.account import GetPasswordRequest
from database import cur, db, is_admin, has_perm, ADMIN_ID, get_usdt_rate, COUNTRY_CODES, get_flag_by_country_name, get_country_info, update_balance, is_bot_online
from config import *
from utils.keyboards import style_btn
from utils.states import admin_state
from plugins.admin import admin_panel_handler

async def detect_account_year(client):
    """Detect account creation year from earliest dialog/message."""
    try:
        me = await client.get_me()
        # Try using the user's own ID creation date approximation
        # Get the earliest message in Saved Messages
        async for msg in client.iter_messages('me', limit=1, reverse=True):
            if msg.date:
                return msg.date.year
        # Fallback: check earliest dialog
        async for dialog in client.iter_dialogs(limit=5):
            if dialog.date:
                return dialog.date.year
    except Exception:
        pass
    from datetime import datetime
    return datetime.now().year

async def manage_admins_menu(event):
    rows = cur.execute("SELECT user_id FROM admins").fetchall()
    msg = f"{PE_CROWN} <b>Manage Sub-Admins</b>\n\n"
    for r in rows: msg += f"{P_ACC} <code>{r[0]}</code>\n"
    btns = [[style_btn("Add Admin", "adm_addadmin", "primary", icon=5409098988156629257), style_btn("Edit Admin", "adm_editadminreq", "primary", icon=5409098988156629257)],
            [style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)]]
    await event.edit(msg, buttons=btns)

async def edit_admin_menu(event, target_id):
    row = cur.execute("SELECT p_add_stock, p_manage_stock, p_stats, p_bal, p_settings FROM admins WHERE user_id=?", (target_id,)).fetchone()
    if not row: return await event.answer("Admin not found", alert=True)
    p = ["✅" if x==1 else "❌" for x in row]
    
    btns = [
        [style_btn(f"Add Stock: {p[0]}", f"adm_tglperm|{target_id}|p_add_stock", "primary", icon=5409098988156629257)],
        [style_btn(f"Manage Stock: {p[1]}", f"adm_tglperm|{target_id}|p_manage_stock", "primary", icon=5409098988156629257)],
        [style_btn(f"Stats & Bcast: {p[2]}", f"adm_tglperm|{target_id}|p_stats", "primary", icon=5409098988156629257)],
        [style_btn(f"Bal & Users: {p[3]}", f"adm_tglperm|{target_id}|p_bal", "primary", icon=5409098988156629257)],
        [style_btn(f"Settings: {p[4]}", f"adm_tglperm|{target_id}|p_settings", "primary", icon=5409098988156629257)],
        [style_btn("Remove Admin", f"adm_deladmin|{target_id}", "danger", icon=6129888444245089008)],
        [style_btn("Back", "adm_manageadmins", "danger", icon=6129888444245089008)]
    ]
    await event.edit(f"✏️ <b>Editing Admin:</b> <code>{target_id}</code>", buttons=btns)

async def send_manage_stock_page(event, page):
    limit = 10
    offset = (page - 1) * limit
    rows = cur.execute("SELECT DISTINCT country_name FROM stock ORDER BY country_name").fetchall()
    total = len(rows)
    countries = rows[offset:offset+limit]
    
    btns = []
    for (c,) in countries: 
        flag = get_flag_by_country_name(c)
        btns.append([style_btn(f"{flag} {c}", f"adm_msc|{c}", "primary", icon=5409098988156629257)])
    
    nav = []
    if page > 1: nav.append(style_btn("Prev", f"adm_mspg|{page-1}", "primary", icon=5409098988156629257))
    if offset + limit < total: nav.append(style_btn("Next", f"adm_mspg|{page+1}", "primary", icon=5409098988156629257))
    if nav: btns.append(nav)
    btns.append([style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)])
    await event.edit(f"{PE_LOCATION} <b>Manage Stock</b> (Page {page})\nSelect a country to edit its properties:", buttons=btns)

async def send_manage_stock_country(event, c_name):
    years = cur.execute("SELECT DISTINCT account_year FROM stock WHERE country_name=? ORDER BY account_year DESC", (c_name,)).fetchall()
    flag = get_flag_by_country_name(c_name)
    btns = [
        [style_btn("Edit Country Name", f"adm_msedit|name|{c_name}", "primary", icon=5409098988156629257), style_btn("Edit Flag", f"adm_msedit|flag|{c_name}", "primary", icon=5409098988156629257)],
        [style_btn("Edit Common Price (All Years)", f"adm_msedit|cprice|{c_name}", "primary", icon=5409098988156629257)]
    ]
    y_btns = []
    for (y,) in years: y_btns.append(style_btn(f"{y}", f"adm_msedit|yprice|{c_name}|{y}", "primary", icon=5409098988156629257))
    
    for i in range(0, len(y_btns), 3): btns.append(y_btns[i:i+3])
    btns.append([style_btn("Back", "adm_mspg|1", "danger", icon=6129888444245089008)])
    await event.edit(f"{flag} <b>Managing: {c_name}</b>\nSelect an option to edit:", buttons=btns)

async def send_autoprice_page(event, page):
    limit = 10
    offset = (page - 1) * limit
    c_list = set([c[0] for c in COUNTRY_CODES.values()])
    db_countries = cur.execute("SELECT DISTINCT country_name FROM stock").fetchall()
    for (c,) in db_countries: c_list.add(c)
    
    custom_countries = cur.execute("SELECT DISTINCT name FROM custom_countries").fetchall()
    for (c,) in custom_countries: c_list.add(c)

    c_list = sorted(list(c_list))
    total = len(c_list)
    countries = c_list[offset:offset+limit]
    
    btns = []
    for c in countries: 
        flag = get_flag_by_country_name(c)
        btns.append([style_btn(f"{flag} {c}", f"adm_apc|{c}", "primary", icon=5409098988156629257)])
        
    nav = []
    if page > 1: nav.append(style_btn("Prev", f"adm_appg|{page-1}", "primary", icon=5409098988156629257))
    if offset + limit < total: nav.append(style_btn("Next", f"adm_appg|{page+1}", "primary", icon=5409098988156629257))
    if nav: btns.append(nav)
    btns.append([style_btn("Add Custom Country", "adm_ap_add_country", "primary", icon=5409098988156629257)])
    btns.append([style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)])
    await event.edit(f"{PE_LIGHTNING} <b>Auto Price Setup</b> (Page {page})\nSelect a country to set fixed prices:", buttons=btns)

async def send_autoprice_country(event, c_name):
    flag = get_flag_by_country_name(c_name)
    btns = [[style_btn("Set Common Price", f"adm_apset|{c_name}|Common", "primary", icon=5409098988156629257)]]
    y_btns = []
    for y in range(2024, 1999, -1): y_btns.append(style_btn(f"{y}", f"adm_apset|{c_name}|{y}", "primary", icon=5409098988156629257))
    for i in range(0, len(y_btns), 4): btns.append(y_btns[i:i+4])
    btns.append([style_btn("Back", "adm_appg|1", "danger", icon=6129888444245089008)])
    await event.edit(f"{flag} <b>Auto Price: {c_name}</b>\nSelect 'Common' for default price, or specific years:", buttons=btns)

async def admin_actions(event):
    data_full = event.data.decode()
    if not data_full.startswith("adm_"): return
    uid = event.sender_id
    action_data = data_full[4:]
    chat = event.chat_id
    
    if action_data == "adminmain":
        await event.delete()
        class FakeEvent: chat_id = chat; sender_id = uid
        return await admin_panel_handler(FakeEvent())

    if action_data == "togglebot" and has_perm(uid, 'p_settings'):
        new_status = 'off' if is_bot_online() else 'on'
        cur.execute("UPDATE settings SET value=? WHERE key='bot_status'", (new_status,))
        db.commit()
        await event.answer(f"Bot turned {new_status.upper()}", alert=True)
        class FakeEvent: chat_id = chat; sender_id = uid
        await admin_panel_handler(FakeEvent())
        await event.delete()
        return

    elif action_data == "stats" and has_perm(uid, 'p_stats'):
        u_row = cur.execute("SELECT COUNT(*) FROM users").fetchone()
        u = u_row[0] if u_row else 0
        s_row = cur.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()
        s = s_row[0] if s_row else 0
        r_row = cur.execute("SELECT value FROM settings WHERE key='upi_revenue'").fetchone()
        r = r_row[0] if r_row else "0"
        bal_row = cur.execute("SELECT SUM(balance) FROM users").fetchone()
        total_bal = bal_row[0] if bal_row and bal_row[0] else 0
        o_row = cur.execute("SELECT COUNT(*), SUM(price) FROM orders").fetchone()
        total_orders = o_row[0] if o_row else 0
        total_spent = o_row[1] if o_row and o_row[1] else 0
        
        msg = (f"{P_STATS} <b>ADVANCED STATS</b>\n\n{P_USERS} <b>Total Users:</b> {u}\n{P_PKG} <b>Accounts in Stock:</b> {s}\n"
               f"{P_MONEY} <b>Total UPI Revenue:</b> {P_INR}{r}\n\n{P_CARD} <b>Overall Users Balance:</b> {P_INR}{total_bal}\n"
               f"{P_CART} <b>Total Accounts Sold:</b> {total_orders}\n{P_USDT} <b>Overall Sales Amount:</b> {P_INR}{total_spent}")
        return await event.edit(msg, buttons=[[style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)]])

    elif action_data == "payments" and has_perm(uid, 'p_settings'):
        btns = [
            [style_btn("Add Payment Method", "adm_addpay", "primary", icon=5409098988156629257)],
            [style_btn("Remove Payment Method", "adm_delpay", "danger", icon=6129888444245089008)],
            [style_btn("Back to Admin", "adm_adminmain", "danger", icon=6129888444245089008)]
        ]
        return await event.edit(f"{P_CARD} <b>Manage Payment Methods</b>", buttons=btns)

    elif action_data == "manageadmins" and uid == ADMIN_ID:
        return await manage_admins_menu(event)

    elif action_data.startswith("tglperm|") and uid == ADMIN_ID:
        _, t_id, p_name = action_data.split("|")
        cur.execute(f"UPDATE admins SET {p_name} = CASE WHEN {p_name}=1 THEN 0 ELSE 1 END WHERE user_id=?", (t_id,))
        db.commit()
        return await edit_admin_menu(event, t_id)
        
    elif action_data.startswith("deladmin|") and uid == ADMIN_ID:
        t_id = action_data.split("|")[1]
        cur.execute("DELETE FROM admins WHERE user_id=?", (t_id,))
        db.commit()
        await event.answer("✅ Admin Removed", alert=True)
        return await manage_admins_menu(event)

    elif action_data == "managesmm" and has_perm(uid, 'p_add_stock'):
        rows = cur.execute("SELECT id, name, category, price_per_1000, available FROM smm_services ORDER BY category, id").fetchall()
        if not rows:
            return await event.edit("📊 <b>Manage SMM Services</b>\n\nNo services added yet.",
                                    buttons=[[style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)]])
        btns = []
        for sid, name, cat, price, avail in rows:
            status = "✅" if avail else "❌"
            btns.append([style_btn(f"{status} [{cat}] {name[:30]} — {P_INR}{price}/1K", f"adm_delsmm|{sid}", "danger", icon=6129888444245089008)])
        btns.append([style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)])
        return await event.edit("📊 <b>Manage SMM Services</b>\n\n<i>Tap a service to delete it:</i>", buttons=btns)

    elif action_data.startswith("delsmm|") and has_perm(uid, 'p_add_stock'):
        sid = int(action_data.split("|")[1])
        row = cur.execute("SELECT name FROM smm_services WHERE id=?", (sid,)).fetchone()
        if row:
            cur.execute("DELETE FROM smm_services WHERE id=?", (sid,))
            db.commit()
            await event.answer(f"✅ Service '{row[0]}' deleted!", alert=True)
        rows = cur.execute("SELECT id, name, category, price_per_1000, available FROM smm_services ORDER BY category, id").fetchall()
        if not rows:
            return await event.edit("📊 <b>Manage SMM Services</b>\n\nNo services remaining.",
                                    buttons=[[style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)]])
        btns = []
        for r_id, name, cat, price, avail in rows:
            status = "✅" if avail else "❌"
            btns.append([style_btn(f"{status} [{cat}] {name[:30]} — {P_INR}{price}/1K", f"adm_delsmm|{r_id}", "danger", icon=6129888444245089008)])
        btns.append([style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)])
        return await event.edit("📊 <b>Manage SMM Services</b>\n\n<i>Tap a service to delete it:</i>", buttons=btns)

    elif action_data == "managerepos" and has_perm(uid, 'p_add_stock'):
        rows = cur.execute("SELECT id, name, price, available FROM repos ORDER BY id DESC").fetchall()
        if not rows:
            return await event.edit(f"💻 <b>𝐌ᴀɴᴀɢᴇ 𝐁ᴏᴛ 𝐑ᴇᴘᴏs</b>\n\nNo repos added yet.",
                                    buttons=[[style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)]])
        btns = []
        for rid, name, price, avail in rows:
            status = "✅" if avail else "❌"
            btns.append([style_btn(f"{status} {name} — {P_INR}{price}", f"adm_delrepo|{rid}", "danger", icon=6129888444245089008)])
        btns.append([style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)])
        return await event.edit(f"💻 <b>𝐌ᴀɴᴀɢᴇ 𝐁ᴏᴛ 𝐑ᴇᴘᴏs</b>\n\n<i>Tap any repo to delete it:</i>", buttons=btns)

    elif action_data.startswith("delrepo|") and has_perm(uid, 'p_add_stock'):
        rid = int(action_data.split("|")[1])
        row = cur.execute("SELECT name, zip_file FROM repos WHERE id=?", (rid,)).fetchone()
        if row:
            if row[1] and os.path.exists(row[1]):
                os.remove(row[1])
            cur.execute("DELETE FROM repos WHERE id=?", (rid,))
            db.commit()
            await event.answer(f"✅ Repo '{row[0]}' deleted!", alert=True)
        rows = cur.execute("SELECT id, name, price, available FROM repos ORDER BY id DESC").fetchall()
        if not rows:
            return await event.edit(f"💻 <b>𝐌ᴀɴᴀɢᴇ 𝐁ᴏᴛ 𝐑ᴇᴘᴏs</b>\n\nNo repos remaining.",
                                    buttons=[[style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)]])
        btns = []
        for r_id, name, price, avail in rows:
            status = "✅" if avail else "❌"
            btns.append([style_btn(f"{status} {name} — {P_INR}{price}", f"adm_delrepo|{r_id}", "danger", icon=6129888444245089008)])
        btns.append([style_btn("Back", "adm_adminmain", "danger", icon=6129888444245089008)])
        return await event.edit(f"💻 <b>𝐌ᴀɴᴀɢᴇ 𝐁ᴏᴛ 𝐑ᴇᴘᴏs</b>\n\n<i>Tap any repo to delete it:</i>", buttons=btns)

    elif action_data == "managestock" and has_perm(uid, 'p_manage_stock'): return await send_manage_stock_page(event, 1)
    elif action_data.startswith("mspg|") and has_perm(uid, 'p_manage_stock'): return await send_manage_stock_page(event, int(action_data.split("|")[1]))
    elif action_data.startswith("msc|") and has_perm(uid, 'p_manage_stock'): return await send_manage_stock_country(event, action_data.split("|")[1])
    elif action_data == "autoprice" and has_perm(uid, 'p_manage_stock'): return await send_autoprice_page(event, 1)
    elif action_data.startswith("appg|") and has_perm(uid, 'p_manage_stock'): return await send_autoprice_page(event, int(action_data.split("|")[1]))
    elif action_data.startswith("apc|") and has_perm(uid, 'p_manage_stock'): return await send_autoprice_country(event, action_data.split("|")[1])
        
    elif action_data == "backupusr" and has_perm(uid, 'p_settings'):
        cur.execute("SELECT * FROM users")
        with open("users_backup.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow([i[0] for i in cur.description]); w.writerows(cur.fetchall())
        await bot.send_file(chat, "users_backup.csv", caption=f"{P_USERS} <b>Users Backup CSV</b>")
        os.remove("users_backup.csv")
        return await event.answer("✅ Backup Generated!", alert=True)

    async with bot.conversation(chat, timeout=600) as conv:
        async def get_reply(txt):
            await conv.send_message(txt + "\n\n<i>(Type /cancel to abort)</i>")
            resp = await conv.get_response()
            if resp.text == "/cancel": raise ValueError("Cancelled")
            return resp

        try:
            if action_data == "ap_add_country" and has_perm(uid, 'p_manage_stock'):
                code = (await get_reply(f"{P_PHONE} <b>Enter Country Calling Code (without +):</b>\n<i>Example: 91</i>")).text.replace("+", "").strip()
                flag = html.escape((await get_reply(f"{P_FLAG} <b>Enter Country Flag Emoji:</b>\n<i>Example: 🇮🇳</i>")).text.strip())
                name = html.escape((await get_reply(f"{P_GLOBE} <b>Enter Country Name:</b>\n<i>Example: India</i>")).text.strip())
                
                cur.execute("INSERT OR REPLACE INTO custom_countries (code, name, flag) VALUES (?,?,?)", (code, name, flag))
                db.commit()
                await conv.send_message(f"{P_YES} <b>Custom Country Added Successfully!</b>\n{flag} {name} (+{code})\n\n<i>It will now automatically be recognized when adding stock!</i>")

            elif action_data == "userinfo" and has_perm(uid, 'p_stats'):
                t_uid = int((await get_reply(f"{P_ACC} <b>Enter User ID:</b>")).text)
                u_row = cur.execute("SELECT balance, total_deposited, joined_date, banned, discount FROM users WHERE user_id=?", (t_uid,)).fetchone()
                if not u_row: return await conv.send_message(f"{P_NO} User not found.")
                
                o_row = cur.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE user_id=?", (t_uid,)).fetchone()
                up_row = cur.execute("SELECT SUM(amount) FROM upi_orders WHERE user_id=? AND status='success'", (t_uid,)).fetchone()
                
                bal, dep, joined, is_banned, disc = u_row
                o_count = o_row[0] if o_row else 0
                o_spent = o_row[1] if o_row and o_row[1] else 0
                u_upi = up_row[0] if up_row and up_row[0] else 0
                
                msg = (f"{P_ACC} <b>USER INFO:</b> <code>{t_uid}</code>\n\n"
                       f"{P_MONEY} Balance: {P_INR}{bal}\n"
                       f"{P_CARD} Total Deposited: {P_INR}{dep}\n"
                       f"{P_UPI} UPI Deposited: {P_INR}{u_upi}\n"
                       f"{P_CART} Total Orders: {o_count}\n"
                       f"{P_USDT} Total Spent: {P_INR}{o_spent}\n"
                       f"{P_GIFT} Discount: {disc}%\n"
                       f"{P_CAL} Joined: {joined}\n"
                       f"{P_OFF} Banned: {'Yes' if is_banned else 'No'}")
                await conv.send_message(msg)

            elif action_data == "addadmin" and uid == ADMIN_ID:
                new_ad = int((await get_reply(f"{P_ACC} <b>Enter User ID for new Admin:</b>")).text)
                cur.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_ad,))
                db.commit()
                await conv.send_message(f"{P_YES} Admin added!")
                class FakeEvent: 
                    async def edit(self, text, buttons): await bot.send_message(chat, text, buttons=buttons)
                    async def answer(self, txt, alert): pass
                await edit_admin_menu(FakeEvent(), new_ad)
                
            elif action_data == "editadminreq" and uid == ADMIN_ID:
                t_id = int((await get_reply(f"{P_ACC} <b>Enter User ID to edit:</b>")).text)
                class FakeEvent: 
                    async def edit(self, text, buttons): await bot.send_message(chat, text, buttons=buttons)
                    async def answer(self, txt, alert): pass
                await edit_admin_menu(FakeEvent(), t_id)

            elif action_data.startswith("msedit|") and has_perm(uid, 'p_manage_stock'):
                parts = action_data.split("|")
                action, c_name = parts[1], parts[2]
                
                if action == "name":
                    new_name = html.escape((await get_reply(f"{P_DOC} <b>Enter NEW Name for {c_name}:</b>")).text)
                    cur.execute("UPDATE stock SET country_name=? WHERE country_name=?", (new_name, c_name))
                    cur.execute("UPDATE auto_prices SET country=? WHERE country=?", (new_name, c_name))
                    db.commit()
                    await conv.send_message(f"{P_YES} Country '{c_name}' successfully renamed to '{new_name}'!")
                    
                elif action == "flag":
                    new_flag = html.escape((await get_reply(f"{P_FLAG} <b>Enter NEW Flag Emoji for {c_name}:</b>")).text)
                    cur.execute("UPDATE stock SET country_icon=? WHERE country_name=?", (new_flag, c_name))
                    db.commit()
                    await conv.send_message(f"{P_YES} Flag updated to {new_flag} for '{c_name}'!")
                    
                elif action == "cprice":
                    new_p = int((await get_reply(f"{P_MONEY} <b>Enter NEW Common Price for all {c_name} accounts:</b>")).text)
                    cur.execute("UPDATE stock SET price=? WHERE country_name=?", (new_p, c_name))
                    db.commit()
                    await conv.send_message(f"{P_YES} All existing '{c_name}' accounts updated to {P_INR}{new_p}!")
                    
                elif action == "yprice":
                    year = parts[3]
                    new_p = int((await get_reply(f"{P_MONEY} <b>Enter NEW Price for {c_name} ({year}):</b>")).text)
                    cur.execute("UPDATE stock SET price=? WHERE country_name=? AND account_year=?", (new_p, c_name, year))
                    db.commit()
                    await conv.send_message(f"{P_YES} All existing '{c_name}' ({year}) accounts updated to {P_INR}{new_p}!")
                    
            elif action_data.startswith("apset|") and has_perm(uid, 'p_manage_stock'):
                parts = action_data.split("|")
                c_name, year = parts[1], parts[2]
                new_p = int((await get_reply(f"{P_ASST} <b>Enter Auto-Price for {c_name} ({year}):</b>\n<i>(Enter 0 to remove this auto-price)</i>")).text)
                if new_p == 0:
                    cur.execute("DELETE FROM auto_prices WHERE country=? AND year=?", (c_name, year))
                    await conv.send_message(f"{P_YES} Auto-Price for {c_name} ({year}) removed!")
                else:
                    cur.execute("INSERT OR REPLACE INTO auto_prices (country, year, price) VALUES (?,?,?)", (c_name, year, new_p))
                    await conv.send_message(f"{P_YES} Auto-Price for {c_name} ({year}) set to {P_INR}{new_p}! Incoming accounts will use this price automatically.")
                db.commit()

            elif action_data == "addpay" and has_perm(uid, 'p_settings'):
                name = html.escape((await get_reply(f"{P_CARD} <b>Enter Payment Method Name:</b>\n<i>(e.g., Binance Pay, TRX)</i>")).text)
                qr_msg = await get_reply(f"📸 <b>Send QR Code Image:</b>\n<i>(Or type <code>skip</code> if no QR needed)</i>")
                qr_path = ""
                if qr_msg.photo:
                    qr_path = f"qr_{int(time.time())}.jpg"
                    await bot.download_media(qr_msg, qr_path)
                
                cap_msg = (await get_reply(f"{P_DOC} <b>Enter Payment Caption:</b>\n<i>(Use <code>text</code> to make wallet IDs or UPI copyable)</i>")).text
                cap_msg = html.escape(cap_msg).replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
                cur.execute("INSERT INTO custom_payments (name, caption, qr_file_id) VALUES (?,?,?)", (name, cap_msg, qr_path))
                db.commit()
                await conv.send_message(f"{P_YES} Payment Method '{name}' added successfully!")

            elif action_data == "delpay" and has_perm(uid, 'p_settings'):
                rows = cur.execute("SELECT id, name FROM custom_payments").fetchall()
                if not rows: return await conv.send_message(f"{P_NO} No custom payment methods.")
                msg = f"{P_DOC} <b>Reply with the ID of the method to delete:</b>\n\n"
                for r in rows: msg += f"ID: {r[0]} - {r[1]}\n"
                del_id = (await get_reply(msg)).text
                try:
                    del_id = int(del_id)
                    file_path = cur.execute("SELECT qr_file_id FROM custom_payments WHERE id=?", (del_id,)).fetchone()
                    if file_path and file_path[0] and os.path.exists(file_path[0]): os.remove(file_path[0])
                    cur.execute("DELETE FROM custom_payments WHERE id=?", (del_id,))
                    db.commit()
                    await conv.send_message(f"{P_YES} Deleted!")
                except: await conv.send_message(f"{P_NO} Invalid ID.")

            elif action_data == "addsmm" and has_perm(uid, 'p_add_stock'):
                name = html.escape((await get_reply(
                    f"📊 <b>Enter Service Name:</b>\n<i>(e.g., Instagram Followers [High Quality])</i>"
                )).text.strip())
                category = html.escape((await get_reply(
                    f"📌 <b>Enter Category:</b>\n<i>(e.g., Instagram, YouTube, TikTok, Telegram)</i>"
                )).text.strip())
                fansmm_id = (await get_reply(
                    f"🆔 <b>Enter FanSMM Service ID:</b>\n<i>Find it on fansmm.in → Services list</i>"
                )).text.strip()
                min_qty = int((await get_reply(f"📉 <b>Enter Minimum Quantity:</b>")).text.strip())
                max_qty = int((await get_reply(f"📈 <b>Enter Maximum Quantity:</b>")).text.strip())
                price_per_1000 = int((await get_reply(
                    f"{P_MONEY} <b>Enter Our Price per 1000 (₹):</b>\n<i>Set higher than fansmm cost for profit</i>"
                )).text.strip())
                desc = html.escape((await get_reply(
                    f"📝 <b>Enter Description:</b>\n<i>(Shown to buyers — quality, speed, etc.)</i>"
                )).text.strip())
                cur.execute(
                    "INSERT INTO smm_services (name, category, fansmm_service_id, min_qty, max_qty, price_per_1000, description, available) VALUES (?,?,?,?,?,?,?,1)",
                    (name, category, fansmm_id, min_qty, max_qty, price_per_1000, desc)
                )
                db.commit()
                await conv.send_message(
                    f"{P_YES} <b>SMM Service Added!</b>\n\n"
                    f"📊 <b>{name}</b>\n"
                    f"📌 Category: {category}\n"
                    f"🆔 FanSMM ID: <code>{fansmm_id}</code>\n"
                    f"{P_MONEY} Price: {P_INR}{price_per_1000}/1000\n"
                    f"📉 Min: {min_qty} | 📈 Max: {max_qty}"
                )

            elif action_data == "addrepo" and has_perm(uid, 'p_add_stock'):
                name = html.escape((await get_reply(f"💻 <b>Enter Repo Name:</b>\n<i>(e.g., Session Spammer Bot)</i>")).text.strip())
                desc = html.escape((await get_reply(f"📝 <b>Enter Repo Description:</b>\n<i>(Brief description shown to buyers)</i>")).text.strip())
                price = int((await get_reply(f"{P_MONEY} <b>Enter Price ({P_INR}):</b>")).text.strip())
                zip_msg = await get_reply(f"📦 <b>Send the ZIP file for this repo:</b>")
                if not zip_msg.file or not (zip_msg.file.name or "").endswith('.zip'):
                    return await conv.send_message(f"{P_NO} Invalid file. Please send a <code>.zip</code> file.")
                os.makedirs("repos", exist_ok=True)
                safe_name = name[:20].replace(' ', '_').replace('/', '_')
                zip_path = f"repos/repo_{int(time.time())}_{safe_name}.zip"
                await bot.download_media(zip_msg, zip_path)
                cur.execute("INSERT INTO repos (name, description, price, zip_file, available) VALUES (?,?,?,?,1)", (name, desc, price, zip_path))
                db.commit()
                await conv.send_message(f"{P_YES} <b>Repo Added!</b>\n💻 <b>{name}</b>\n{P_MONEY} Price: {P_INR}{price}\n📦 File saved. Users can now buy it!")

            elif action_data == "addzip" and has_perm(uid, 'p_add_stock'):
                resp = await get_reply(f"{P_PKG} <b>Send the ZIP file containing <code>.session</code> files:</b>")
                if not resp.file or not resp.file.name.endswith('.zip'): return await conv.send_message(f"{P_NO} Invalid file.")
                
                await conv.send_message(f"{P_WAIT} <b>Extracting & Scanning Accounts...</b>")
                zip_path = await bot.download_media(resp, "temp_sessions.zip")
                extracted_dir = f"temp_extracted_{int(time.time())}"
                os.makedirs(extracted_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(extracted_dir)

                groups = {}
                for file in os.listdir(extracted_dir):
                    if not file.endswith(".session"): continue
                    sess_path = os.path.join(extracted_dir, file)
                    clean_path = sess_path[:-8]
                    try:
                        client = TelegramClient(clean_path, API_ID, API_HASH)
                        await client.connect()
                        if not await client.is_user_authorized(): await client.disconnect(); continue
                        me = await client.get_me()
                        phone = getattr(me, 'phone', None)
                        if not phone: await client.disconnect(); continue
                        
                        c_name, c_icon = get_country_info(phone)
                        pwd = await client(GetPasswordRequest())
                        has_2fa = pwd.has_password
                        year = await detect_account_year(client)
                        await client.disconnect()

                        key = (c_name, year, has_2fa)
                        if key not in groups: groups[key] = []
                        groups[key].append({"phone": phone, "path": clean_path, "c_icon": c_icon})
                    except Exception as e: logger.error(f"Scan error: {e}")

                for key in list(groups.keys()):
                    if key[0] == "Unknown":
                        sample_phone = groups[key][0]["phone"]
                        await conv.send_message(f"{P_WARN} <b>Country not recognized for +{sample_phone}!</b>")
                        new_icon = html.escape((await get_reply(f"{P_FLAG} <b>Enter Country Flag Emoji:</b>\n<i>Example: 🇮🇳</i>")).text)
                        new_name = html.escape((await get_reply(f"{P_GLOBE} <b>Enter Country Name:</b>\n<i>Example: India</i>")).text)
                        new_key = (new_name, key[1], key[2])
                        groups[new_key] = groups.pop(key)
                        for acc in groups[new_key]: acc["c_icon"] = new_icon

                success = 0
                for (c_name, year, has_2fa), accs in groups.items():
                    c_icon = accs[0]["c_icon"]
                    twofa_pass = "None"
                    if has_2fa: twofa_pass = html.escape((await get_reply(f"{P_2FA} <b>Enter 2FA Password for {len(accs)}x {c_name} accounts:</b>")).text)

                    auto_row = cur.execute("SELECT price FROM auto_prices WHERE country=? AND year=?", (c_name, str(year))).fetchone()
                    if not auto_row: auto_row = cur.execute("SELECT price FROM auto_prices WHERE country=? AND year='Common'", (c_name,)).fetchone()

                    if auto_row:
                        price = auto_row[0]
                        await conv.send_message(f"⚡ <b>Auto-Price Applied:</b> {len(accs)}x {c_name} ({year}) at {P_INR}{price}.")
                    else:
                        existing_price = cur.execute("SELECT price FROM stock WHERE country_name=? LIMIT 1", (c_name,)).fetchone()
                        if existing_price:
                            price = existing_price[0]
                            await conv.send_message(f"⚡ <b>Auto-Added:</b> {len(accs)}x {c_name} at {P_INR}{price} (Copied from DB).")
                        else:
                            price = int((await get_reply(f"📌 Found {len(accs)}x {c_name} ({year}).\n{P_MONEY} Enter Price (₹):")).text)

                    for acc in accs:
                        perm_base = f"sessions/{acc['phone']}"
                        for ext in ['.session', '.session-wal', '.session-shm', '.session-journal']:
                            if os.path.exists(acc['path'] + ext): shutil.move(acc['path'] + ext, perm_base + ext)
                        cur.execute("INSERT OR REPLACE INTO stock (phone, session_file, country_name, country_icon, account_year, category, price, available, twofa) VALUES (?,?,?,?,?,?,?,?,?)", 
                                    (acc['phone'], perm_base + ".session", c_name, c_icon, year, 'Good', price, 1, twofa_pass))
                        success += 1
                db.commit()
                os.remove(zip_path); shutil.rmtree(extracted_dir)
                await conv.send_message(f"{P_YES} <b>Bulk Interactive Upload Complete!</b>\n{P_ON} Added: {success}")

            elif action_data == "addstock" and has_perm(uid, 'p_add_stock'):
                phone = (await get_reply(f"{P_PHONE} Enter Phone (+919999...):")).text.replace(" ", "").replace("+", "")
                sp = f"sessions/{phone}"
                client = TelegramClient(sp, API_ID, API_HASH)
                await client.connect()
                sreq = await client.send_code_request(phone)
                
                twofa_pass = "None"
                try: 
                    await client.sign_in(phone, (await get_reply(f"{P_OTP} OTP:")).text, phone_code_hash=sreq.phone_code_hash)
                except SessionPasswordNeededError: 
                    twofa_pass = html.escape((await get_reply(f"{P_2FA} 2FA Pass required. Enter it now:")).text)
                    await client.sign_in(password=twofa_pass)
                
                c_name, c_icon = get_country_info(phone)
                
                if c_name == "Unknown":
                    await conv.send_message(f"{P_WARN} <b>Country not recognized for +{phone}!</b>")
                    c_icon = html.escape((await get_reply(f"{P_FLAG} <b>Enter Country Flag Emoji:</b>\n<i>Example: 🇮🇳</i>")).text)
                    c_name = html.escape((await get_reply(f"{P_GLOBE} <b>Enter Country Name:</b>\n<i>Example: India</i>")).text)
                
                auto_year = await detect_account_year(client)
                await client.disconnect()
                
                year = int((await get_reply(f"{P_CAL} Detected Year: <b>{auto_year}</b>\nReply with Year to confirm or change:")).text)
                auto_row = cur.execute("SELECT price FROM auto_prices WHERE country=? AND year=?", (c_name, str(year))).fetchone()
                if not auto_row: auto_row = cur.execute("SELECT price FROM auto_prices WHERE country=? AND year='Common'", (c_name,)).fetchone()

                if auto_row:
                    price = auto_row[0]
                    await conv.send_message(f"⚡ <b>Auto-Price Applied:</b> {P_INR}{price} for {c_name} ({year})")
                else:
                    existing_price = cur.execute("SELECT price FROM stock WHERE country_name=? LIMIT 1", (c_name,)).fetchone()
                    if existing_price:
                        price = existing_price[0]
                        await conv.send_message(f"⚡ <b>Auto-detected Price:</b> {P_INR}{price} for {c_name}")
                    else: price = int((await get_reply(f"{P_MONEY} Price (₹):")).text)
                
                cur.execute("INSERT OR REPLACE INTO stock (phone, session_file, country_name, country_icon, account_year, category, price, available, twofa) VALUES (?,?,?,?,?,?,?,?,?)", 
                            (phone, sp + ".session", c_name, c_icon, year, 'Good', price, 1, twofa_pass))
                db.commit()
                await conv.send_message(f"{P_YES} Added!")

            elif action_data == "supporturl" and has_perm(uid, 'p_settings'):
                url = (await get_reply("🔗 Enter new Support URL (must start with http:// or https://):")).text
                if not url.startswith("http"): url = "https://" + url.replace("@", "t.me/")
                cur.execute("UPDATE settings SET value=? WHERE key='support_url'", (url,))
                db.commit()
                await conv.send_message(f"{P_YES} Support URL updated.")

            elif action_data == "bcast" and has_perm(uid, 'p_stats'):
                txt = (await get_reply(f"{P_DOC} <b>Message (Supports HTML & tg-emoji tags):</b>")).text
                btn_name = (await get_reply(f"🔘 <b>Button Name (or 'skip'):</b>")).text
                url = (await get_reply("🔗 <b>URL:</b>")).text if btn_name.lower() != 'skip' else None
                btns = [[Button.url(btn_name, url)]] if url else None
                users = cur.execute("SELECT user_id FROM users").fetchall()
                s, f = 0, 0
                total = len(users)
                status_msg = await conv.send_message(f"{P_TG} Broadcasting to {total} users...")
                for idx, (u_id,) in enumerate(users):
                    try: 
                        await bot.send_message(int(u_id), txt, buttons=btns, parse_mode='html')
                        s += 1
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                        try:
                            await bot.send_message(int(u_id), txt, buttons=btns, parse_mode='html')
                            s += 1
                        except Exception:
                            f += 1
                    except (UserIsBlockedError, InputUserDeactivatedError):
                        f += 1
                    except Exception:
                        f += 1
                    if (idx + 1) % 50 == 0:
                        try: await status_msg.edit(f"{P_TG} Broadcasting... {idx+1}/{total} (✅ {s} | ❌ {f})")
                        except: pass
                    await asyncio.sleep(0.05) 
                await conv.send_message(f"{P_YES} Done! Sent: {s} | Failed: {f} | Total: {total}")

            elif action_data == "bal" and has_perm(uid, 'p_bal'):
                t_uid = int((await get_reply(f"{P_ACC} <b>User ID:</b>")).text)
                amt = int((await get_reply(f"{P_MONEY} <b>Amount (Negative to deduct):</b>")).text)
                update_balance(t_uid, amt)
                await conv.send_message(f"{P_YES} Added {P_INR}{amt} to {t_uid}.")
                
            elif action_data == "discount" and has_perm(uid, 'p_settings'):
                t_uid = int((await get_reply(f"{P_ACC} <b>User ID:</b>")).text)
                pct = int((await get_reply(f"{P_GIFT} <b>Discount % (0 to remove):</b>")).text)
                cur.execute("UPDATE users SET discount=? WHERE user_id=?", (pct, t_uid))
                db.commit()
                await conv.send_message(f"{P_YES} User {t_uid} has {pct}% discount.")
                
            elif action_data == "refpct" and has_perm(uid, 'p_settings'):
                pct = int((await get_reply(f"{P_USERS} <b>New Referral %:</b>")).text)
                cur.execute("UPDATE settings SET value=? WHERE key='ref_percent'", (str(pct),))
                db.commit()
                await conv.send_message(f"{P_YES} Ref revenue set to {pct}%.")

            elif action_data == "usdtrate" and has_perm(uid, 'p_settings'):
                r = float((await get_reply(f"{P_USDT} <b>New USDT Rate (INR):</b>")).text)
                cur.execute("UPDATE settings SET value=? WHERE key='usdt_rate'", (str(r),))
                db.commit()
                await conv.send_message(f"{P_YES} Rate set to {r}.")

            elif action_data == "restoreusr" and has_perm(uid, 'p_settings'):
                resp = await get_reply(f"📤 <b>Send the <code>users_backup.csv</code> file:</b>")
                if not resp.file or not resp.file.name.endswith('.csv'): return await conv.send_message(f"{P_NO} Invalid file.")
                await bot.download_media(resp, "temp_restore.csv")
                with open("temp_restore.csv", "r", encoding="utf-8") as f:
                    reader = csv.reader(f); next(reader); count = 0
                    for row in reader:
                        try:
                            cur.execute("INSERT OR REPLACE INTO users (user_id, balance, referred_by, total_deposited, joined_date, banned, discount, terms_accepted) VALUES (?,?,?,?,?,?,?,?)", 
                                        (int(row[0]), int(row[1]), row[2] if row[2] else None, int(row[3]), row[4], int(row[5]), int(row[6]), int(row[7])))
                            count += 1
                        except: pass
                db.commit()
                os.remove("temp_restore.csv")
                await conv.send_message(f"{P_YES} Restored {count} users.")

            elif action_data == "ban" and has_perm(uid, 'p_bal'):
                t_uid = int((await get_reply(f"{P_ACC} <b>User ID:</b>")).text)
                is_ban = cur.execute("SELECT banned FROM users WHERE user_id=?", (t_uid,)).fetchone()
                if not is_ban: return await conv.send_message(f"{P_NO} User not found.")
                ns = 0 if is_ban[0] == 1 else 1
                cur.execute("UPDATE users SET banned=? WHERE user_id=?", (ns, t_uid))
                db.commit()
                await conv.send_message(f"User {t_uid} is {'Banned 🚫' if ns == 1 else 'Unbanned ✅'}.")

        except ValueError: await conv.send_message(f"{P_NO} Cancelled.")
        except Exception as e: await conv.send_message(f"{P_NO} Error: {e}")

def register_admin_actions(bot):
    @bot.on(events.CallbackQuery(pattern=r"^adm_"))
    async def cb_admin_actions(e):
        if is_admin(e.sender_id):
            await admin_actions(e)
