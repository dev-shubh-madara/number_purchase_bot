#MADE_BY_MADARA
#TRUE LODA LOVE

import os
import re
import html
import urllib.parse
import io
from telethon import events, Button
from telethon.errors import MessageNotModifiedError
from database import cur, db, get_usdt_rate, update_balance, to_usd
from config import PE_GIFT, PE_LIGHTNING, P_MONEY, P_CARD, P_UPI, P_CW, P_NO, P_YES, P_WARN, P_INR, P_USDT, P_KEY, PE_CHECK, P_ACC, P_ID, LOG_CHANNEL_ID, LOG_CHANNELS, ADMIN_ID, CWALLET_QR, CWALLET_ID, UPI_ID, bot, logger
from utils.keyboards import style_btn
from utils.states import deposit_input, waiting_proof, admin_dep_state, custom_dep_amt, get_user_lock

async def deposit_menu(event):
    btns = [[style_btn(f"𝐀ᴅᴅ 𝐅ᴜɴᴅs by UPI", "depm_UPI", "success", icon=5409271925014801629)],
            [style_btn(f"𝐂ᴡᴀʟʟᴇᴛ (5% 𝐁𝐎𝐍𝐔𝐒)", "depm_Cwallet", "primary", icon=5440627033111557670)]]
    
    customs = cur.execute("SELECT name FROM custom_payments").fetchall()
    for c in customs:
        btns.append([style_btn(f"{c[0]}", f"depm_{c[0]}", "primary", icon=5408832111773757273)])
        
    msg = f"<blockquote>{PE_GIFT} <b>𝐀ᴅᴅ 𝐅ᴜɴᴅs</b>\n\n𝐂ʜᴏᴏsᴇ ʏᴏᴜʀ ᴘʀᴇғᴇʀʀᴇᴅ ᴘᴀʏᴍᴇɴᴛ ᴍᴇᴛʜᴏᴅ ʙᴇʟᴏᴡ:"
    if isinstance(event, events.CallbackQuery.Event):
        try: await event.edit(msg, buttons=btns)
        except MessageNotModifiedError: pass
    else: await event.respond(msg, buttons=btns)

async def manual_deposit_init(event, method):
    uid = event.sender_id
    deposit_input[uid] = {'step': 'wait_amt', 'method': method}
    await event.edit(f"{P_MONEY} <b>𝐄ɴᴛᴇʀ 𝐃ᴇᴘᴏsɪᴛ 𝐀ᴍᴏᴜɴᴛ (ɪɴ {P_INR}):</b>\n\n<i>𝐌ɪɴɪᴍᴜᴍ ᴅᴇᴘᴏsɪᴛ ɪs {P_INR}10.</i>", buttons=[[Button.inline("❌ 𝐂ᴀɴᴄᴇʟ", "cancel_action")]])

async def process_referral_bonus(user_id, amt):
    try:
        row = cur.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row[0]: return
        ref_id = row[0]
        
        pct_row = cur.execute("SELECT value FROM settings WHERE key='ref_percent'").fetchone()
        pct = int(pct_row[0]) if pct_row else 3
        
        bonus = int(amt * (pct / 100))
        if bonus <= 0: return
        
        async with get_user_lock(ref_id):
            update_balance(ref_id, bonus)
            db.commit()
            
        try: await bot.send_message(int(ref_id), f"{PE_GIFT} <b>Referral Bonus!</b>\nYour friend deposited {P_INR}{amt}. You received <b>{P_INR}{bonus}</b> ({pct}%) in your balance!")
        except: pass
    except Exception as e: logger.error(f"Ref bonus error: {e}")

def get_admin_custom_keypad(dep_id):
    return [
        [style_btn("1", f"dkp|{dep_id}|1", "primary", icon=5375125990118793401), style_btn("2", f"dkp|{dep_id}|2", "primary", icon=5409098988156629257), style_btn("3", f"dkp|{dep_id}|3", "primary", icon=6154249597532248059)],
        [style_btn("4", f"dkp|{dep_id}|4", "primary", icon=5796170975699544141), style_btn("5", f"dkp|{dep_id}|5", "primary", icon=5409320020058584473), style_btn("6", f"dkp|{dep_id}|6", "primary", icon=5409098988156629257)],
        [style_btn("7", f"dkp|{dep_id}|7", "primary", icon=6129779562529168023), style_btn("8", f"dkp|{dep_id}|8", "primary", icon=5355292788923593967), style_btn("9", f"dkp|{dep_id}|9", "primary", icon=5408832111773757273)],
        [style_btn("Del", f"dkp|{dep_id}|del", "danger", icon=6129732880529628243), style_btn("0", f"dkp|{dep_id}|0", "primary", icon=6154249597532248059), style_btn("Confirm", f"dkp|{dep_id}|conf", "success", 5409098988156629257, icon=5409320020058584473)],
        [style_btn("𝐂ᴀɴᴄᴇʟ", f"dkp|{dep_id}|cancel", "danger", icon=6129888444245089008)]
    ]

# We will skip the automated UPI part in this script to save space if needed, 
# or I can port it directly. The user had a keypad logic for UPI amounts.
def get_keypad():
    return [
        [style_btn("1", b"kp_1", style_type="primary", icon=5408832111773757273), style_btn("2", b"kp_2", style_type="primary", icon=5408832111773757273), style_btn("3", b"kp_3", style_type="primary", icon=6129888444245089008)],
        [style_btn("4", b"kp_4", style_type="primary", icon=6064275556008989746), style_btn("5", b"kp_5", style_type="primary", icon=6129627894349045589), style_btn("6", b"kp_6", style_type="primary", icon=5409320020058584473)],
        [style_btn("7", b"kp_7", style_type="primary", icon=5375125990118793401), style_btn("8", b"kp_8", style_type="primary", icon=6129731974291527294), style_btn("9", b"kp_9", style_type="primary", icon=6170048080679801421)],
        [style_btn("Del", b"kp_del", style_type="danger", icon=6203982793379154737), style_btn("0", b"kp_0", style_type="primary", icon=5408832111773757273), style_btn("Confirm", b"kp_done", style_type="success", icon=6064310143380625195)],
        [style_btn("𝐂ᴀɴᴄᴇʟ", b"cancel_action", style_type="danger", icon=5796170975699544141)]
    ]

def register_deposit(bot):
    @bot.on(events.NewMessage(pattern=r"(?i)^(💳 𝐃ᴇᴘᴏsɪᴛ|💳 Deposit)$"))
    async def msg_deposit(e):
        await deposit_menu(e)

    @bot.on(events.CallbackQuery(pattern=r"^depm_(.+)$"))
    async def cb_manual_dep(e):
        method = e.pattern_match.group(1).decode()
        await manual_deposit_init(e, method)

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in deposit_input and deposit_input[e.sender_id]['step'] == 'wait_amt'))
    async def msg_wait_amt(e):
        uid = e.sender_id
        text = e.text or ""
        try:
            amt = int(re.sub(r'[^\d]', '', text))
            if amt < 10: return await e.reply(f"{P_WARN} Minimum Deposit is ₹10.")
            method = deposit_input[uid]['method']
            waiting_proof[uid] = {'amount': amt, 'method': method}
            deposit_input.pop(uid)
            
            rate = get_usdt_rate()
            usdt_amt = round(amt / rate, 2)
            rate_text = f"<blockquote>{P_MONEY} <b>𝐀ᴍᴏᴜɴᴛ ᴛᴏ 𝐏ᴀʏ:</b> {P_INR}{amt} (~{P_USDT}{usdt_amt} USDT)\n💱 <i>𝐄xᴄʜᴀɴɢᴇ 𝐑ᴀᴛᴇ: {P_INR}{rate} = $1</i></blockquote>"
            
            if method == "Cwallet":
                msg = (f"<blockquote>{P_CARD} <b>𝐌ᴇᴛʜᴏᴅ:</b> {method}\n\n🚀 <b>𝐀ᴅᴅʀᴇss / 𝐈𝐃:</b>\n<code>{CWALLET_ID}</code></blockquote>\n"
                       f"{rate_text}\n"
                       f"<blockquote>👉 <b>𝐒ᴇɴᴅ 𝐏ʀᴏᴏғ:</b>\n𝐏ʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ 𝐓ʀᴀɴsᴀᴄᴛɪᴏɴ 𝐇ᴀsʜ (𝐋ɪɴᴋ) ᴏʀ ᴀ 𝐒ᴄʀᴇᴇɴsʜᴏᴛ ᴏғ ᴛʜᴇ ᴘᴀʏᴍᴇɴᴛ ɴᴏᴡ.</blockquote>")
                try: await bot.send_file(uid, CWALLET_QR, caption=msg, buttons=[[Button.inline("❌ 𝐂ᴀɴᴄᴇʟ", "cancel_action")]])
                except Exception: await bot.send_message(uid, msg + f"\n\n🔗 QR Link: {CWALLET_QR}", buttons=[[Button.inline("❌ 𝐂ᴀɴᴄᴇʟ", "cancel_action")]])
            elif method == "UPI":
                upi_url = f"upi://pay?pa={UPI_ID}&am={amt}"
                msg = (f"<blockquote>{P_UPI} <b>𝐌ᴇᴛʜᴏᴅ:</b> UPI\n\n🆔 <b>UPI ID:</b>\n<code>{UPI_ID}</code></blockquote>\n"
                       f"{rate_text}\n"
                       f"<blockquote>👉 <b>𝐒ᴇɴᴅ 𝐏ʀᴏᴏғ:</b>\n𝐏ʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴄʟᴇᴀʀ 𝐒ᴄʀᴇᴇɴsʜᴏᴛ ᴏғ ᴛʜᴇ ᴘᴀʏᴍᴇɴᴛ ɴᴏᴡ.</blockquote>")
                try: 
                    import qrcode
                    qr = qrcode.QRCode(version=1, box_size=10, border=4)
                    qr.add_data(upi_url)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    qr_file = io.BytesIO()
                    qr_file.name = "upi_qr.png"
                    img.save(qr_file, "PNG")
                    qr_file.seek(0)
                    
                    await bot.send_file(uid, qr_file, caption=msg, buttons=[[Button.inline("❌ 𝐂ᴀɴᴄᴇʟ", "cancel_action")]])
                except Exception as e: 
                    logger.error(f"Failed to send UPI QR: {e}")
                    await bot.send_message(uid, msg, buttons=[[Button.inline("❌ 𝐂ᴀɴᴄᴇʟ", "cancel_action")]])
            else:
                row = cur.execute("SELECT caption, qr_file_id FROM custom_payments WHERE name=?", (method,)).fetchone()
                if row:
                    cap = f"<blockquote>{row[0]}</blockquote>\n{rate_text}\n<blockquote>👇 <b>𝐀ғᴛᴇʀ ᴘᴀʏɪɴɢ, sᴇɴᴅ ᴀ ᴄʟᴇᴀʀ 𝐒ᴄʀᴇᴇɴsʜᴏᴛ ʜᴇʀᴇ:</b></blockquote>"
                    btns = [[Button.inline("❌ 𝐂ᴀɴᴄᴇʟ", "cancel_action")]]
                    if row[1] and os.path.exists(row[1]): 
                        try: await bot.send_file(e.chat_id, row[1], caption=cap, buttons=btns)
                        except: await e.reply(cap, buttons=btns)
                    else: await e.reply(cap, buttons=btns)
                else: await e.reply(f"{P_CARD} <b>{method} Deposit</b>{rate_text}\n\n👇 Send Screenshot here:", buttons=[[Button.inline("❌ 𝐂ᴀɴᴄᴇʟ", "cancel_action")]])
        except ValueError: await e.respond(f"{P_NO} Please enter a valid number in {P_INR} (INR).")

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in waiting_proof and (e.photo or (e.text and "http" in e.text))))
    async def msg_wait_proof(e):
        uid = e.sender_id
        info = waiting_proof.pop(uid)
        final_amt = info['amount']
        if info['method'] == "Cwallet": final_amt = int(final_amt * 1.05)
        
        cur.execute("INSERT INTO deposits (user_id, amount, method_name, status) VALUES (?,?,?,?)", (uid, final_amt, info['method'], "pending"))
        db.commit()
        dep_id = cur.lastrowid
        await e.reply(f"{PE_GIFT} 𝐃ᴇᴘᴏsɪᴛ ʀᴇǫᴜᴇsᴛ sᴜʙᴍɪᴛᴛᴇᴅ! 𝐏ʟᴇᴀsᴇ ᴡᴀɪᴛ ғᴏʀ ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴀʟ.")
        cap = f"{PE_LIGHTNING} <b>𝐍ᴇᴡ 𝐃ᴇᴘᴏsɪᴛ 𝐑ᴇǫᴜᴇsᴛ</b>\n{P_ACC} 𝐔sᴇʀ: <code>{uid}</code>\n{P_MONEY} 𝐑ᴇǫᴜᴇsᴛ: <b>{P_INR}{info['amount']}</b>\n{P_CARD} 𝐌ᴇᴛʜᴏᴅ: {info['method']}\n{P_ID} 𝐑ᴇғ: <code>{dep_id}</code>"
        btns = [[style_btn(f"𝐀ᴄᴄᴇᴘᴛ (₹{final_amt})", f"dep_acc|{dep_id}|{uid}|{info['method']}|exact|{final_amt}", "success", icon=5409098988156629257), 
                 style_btn("𝐑ᴇᴊᴇᴄᴛ", f"dep_rej|{dep_id}|{uid}", "danger", icon=5409119256107297715)],
                [style_btn("𝐂ᴜsᴛᴏᴍ 𝐀ᴍᴏᴜɴᴛ", f"dep_acc|{dep_id}|{uid}|{info['method']}|custom|0", "primary", icon=5409098988156629257)]]
        
        try:
            for log_ch in LOG_CHANNELS:
                try:
                    if e.photo: await bot.send_message(log_ch, cap, file=e.media, buttons=btns)
                    else: await bot.send_message(log_ch, cap + f"\n🔗 Hash: {html.escape(e.text)}", buttons=btns)
                except Exception: pass
        except Exception as log_err:
            try:
                if e.photo: await bot.send_message(ADMIN_ID, f"⚠️ <b>LOG CHANNEL ERROR</b>\n\n{cap}", file=e.media, buttons=btns)
                else: await bot.send_message(ADMIN_ID, f"⚠️ <b>LOG CHANNEL ERROR</b>\n\n{cap}\n🔗 Hash: {html.escape(e.text)}", buttons=btns)
            except Exception as admin_err: logger.error(f"Failed to log deposit: {admin_err}")

    @bot.on(events.CallbackQuery(pattern=r"^dep_acc\|"))
    async def cb_dep_acc(e):
        p = e.data.decode().split("|")
        dep_id, t_uid, method, a_type = p[1], int(p[2]), p[3], p[4]
        row = cur.execute("SELECT status FROM deposits WHERE id=?", (dep_id,)).fetchone()
        if not row or row[0] != 'pending': return await e.edit(f"{P_WARN} Already processed.")
        
        if a_type == "exact":
            amt = int(p[5]) 
            async with get_user_lock(t_uid):
                prev_row = cur.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
                prev_bal = prev_row[0] if prev_row else 0
                update_balance(t_uid, amt)
                
                cur.execute("UPDATE deposits SET status='approved', amount=? WHERE id=?", (amt, dep_id))
                cur.execute("UPDATE users SET total_deposited = total_deposited + ? WHERE user_id=?", (amt, t_uid))
                db.commit()
            
            await process_referral_bonus(t_uid, amt)
            
            user_msg = (f"<blockquote>{PE_CHECK} <b>Deposit Approved!</b>\n\n{P_MONEY} <b>Amount Added:</b> ${to_usd(amt):.2f} ({P_INR}{amt})\n"
                        f"📉 <b>𝐏ʀᴇᴠious 𝐁ᴀʟᴀɴᴄᴇ:</b> ${to_usd(prev_bal):.2f} ({P_INR}{prev_bal})\n📈 <b>New 𝐁ᴀʟᴀɴᴄᴇ:</b> ${to_usd(prev_bal+amt):.2f} ({P_INR}{prev_bal+amt})</blockquote>")
            await bot.send_message(int(t_uid), user_msg)
            try: await e.edit(f"{PE_CHECK} <b>INSTANT CREDITED {P_INR}{amt} TO {t_uid}</b>")
            except MessageNotModifiedError: pass
            
        elif a_type == "custom":
            custom_dep_amt[int(dep_id)] = "0"
            await e.edit(f"{P_KEY} <b>Enter 𝐂ᴜsᴛᴏᴍ 𝐀ᴍᴏᴜɴᴛ for User {t_uid}:</b>\n\n{P_MONEY} 0", buttons=get_admin_custom_keypad(int(dep_id)))
            
    @bot.on(events.CallbackQuery(pattern=r"^dep_rej\|"))
    async def cb_dep_rej(e):
        uid = e.sender_id
        p = e.data.decode().split("|")
        dep_id, t_uid = p[1], int(p[2])
        row = cur.execute("SELECT status FROM deposits WHERE id=?", (dep_id,)).fetchone()
        if not row or row[0] != 'pending': return await e.edit(f"{P_WARN} Already processed.")
        admin_dep_state[uid] = {'target_uid': t_uid, 'dep_id': dep_id, 'step': 'wait_reason', 'msg_id': e.message_id}
        await bot.send_message(uid, f"{P_WARN} Reply to this message with the REASON for rejecting user <code>{t_uid}</code>:")
        try: await e.answer("Check your bot PMs to enter the reason.", alert=True)
        except: pass

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in admin_dep_state and admin_dep_state[e.sender_id]['step'] == 'wait_reason'))
    async def msg_admin_rej_reason(e):
        uid = e.sender_id
        st = admin_dep_state[uid]
        t_uid, dep_id, msg_id = st['target_uid'], st['dep_id'], st['msg_id']
        cur.execute("UPDATE deposits SET status='rejected' WHERE id=?", (dep_id,))
        db.commit()
        
        try:
            await bot.edit_message(LOG_CHANNEL_ID, msg_id, f"{P_NO} <b>REJECTED USER {t_uid}</b>\nReason: {html.escape(e.text)}")
            for log_ch in LOG_CHANNELS:
                if log_ch != LOG_CHANNEL_ID:
                    try: await bot.send_message(log_ch, f"{P_NO} <b>REJECTED USER {t_uid}</b>\nReason: {html.escape(e.text)}")
                    except: pass
        except: pass
        
        await bot.send_message(int(t_uid), f"{P_NO} <b>Deposit 𝐑ᴇᴊᴇᴄᴛed!</b>\n📋 Reason: {html.escape(e.text)}")
        await e.reply(f"{P_YES} 𝐑ᴇᴊᴇᴄᴛion reason sent.")
        admin_dep_state.pop(uid)

    @bot.on(events.CallbackQuery(pattern=r"^dkp\|"))
    async def cb_dkp(e):
        uid = e.sender_id
        _, dep_id, action = e.data.decode().split("|")
        dep_id = int(dep_id)
        row = cur.execute("SELECT user_id, method_name, status, amount FROM deposits WHERE id=?", (dep_id,)).fetchone()
        if not row or row[2] != 'pending': return await e.edit(f"{P_WARN} Already processed.")
        t_uid, method, orig_amt = row[0], row[1], row[3]
        
        curr = custom_dep_amt.get(dep_id, "0")
        
        if action.isdigit():
            if curr == "0": curr = action
            else: curr += action
            if len(curr) > 7: curr = curr[:7]
        elif action == "del": curr = curr[:-1] or "0"
        elif action == "cancel":
            btns = [[style_btn(f"𝐀ᴄᴄᴇᴘᴛ (₹{orig_amt})", f"dep_acc|{dep_id}|{t_uid}|{method}|exact|{orig_amt}", "success", icon=6147460667281511517), 
                     style_btn("𝐑ᴇᴊᴇᴄᴛ", f"dep_rej|{dep_id}|{t_uid}", "danger", icon=6129888444245089008)],
                    [style_btn("𝐂ᴜsᴛᴏᴍ 𝐀ᴍᴏᴜɴᴛ", f"dep_acc|{dep_id}|{t_uid}|{method}|custom|0", "primary", icon=5796170975699544141)]]
            return await e.edit(f"{PE_LIGHTNING} <b>𝐍ᴇᴡ 𝐃ᴇᴘᴏsɪᴛ 𝐑ᴇǫᴜᴇsᴛ</b>\n{P_ACC} 𝐔sᴇʀ: <code>{t_uid}</code>\n{P_MONEY} 𝐑ᴇǫᴜᴇsᴛ: <b>{P_INR}{orig_amt}</b>\n{P_CARD} 𝐌ᴇᴛʜᴏᴅ: {method}\n{P_ID} 𝐑ᴇғ: <code>{dep_id}</code>", buttons=btns)
        elif action == "conf":
            amt = int(curr)
            if amt <= 0: return await e.answer("Amount must be > 0", alert=True)
            
            async with get_user_lock(t_uid):
                prev_row = cur.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
                prev_bal = prev_row[0] if prev_row else 0
                update_balance(t_uid, amt)
                cur.execute("UPDATE deposits SET status='approved', amount=? WHERE id=?", (amt, dep_id))
                cur.execute("UPDATE users SET total_deposited = total_deposited + ? WHERE user_id=?", (amt, t_uid))
                db.commit()
                
            await process_referral_bonus(t_uid, amt)
            await e.edit(f"{PE_CHECK} <b>APPROVED {P_INR}{amt} TO {t_uid} (𝐂ᴜsᴛᴏᴍ 𝐀ᴍᴏᴜɴᴛ)</b>")
            await bot.send_message(int(t_uid), f"{PE_CHECK} <b>Deposit Approved!</b>\n{P_MONEY} Amount Added: {P_INR}{amt}\n📉 Old: {P_INR}{prev_bal} | 📈 New: {P_INR}{prev_bal+amt}")
            return

        custom_dep_amt[dep_id] = curr
        await e.edit(f"{P_KEY} <b>Enter 𝐂ᴜsᴛᴏᴍ 𝐀ᴍᴏᴜɴᴛ for User {t_uid}:</b>\n\n{P_MONEY} {curr}", buttons=get_admin_custom_keypad(dep_id))
