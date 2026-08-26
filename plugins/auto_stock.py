import asyncio
import html
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient, events
from telethon.tl.functions.account import GetPasswordRequest

from config import (
    API_HASH,
    API_ID,
    ACCOUNT_PROFIT,
    AUTO_STOCK_DEFAULT_COST,
    AUTO_STOCK_UPLOAD_ENABLED,
    P_INR,
    P_NO,
    P_PHONE,
    P_PKG,
    P_WAIT,
    P_YES,
    bot,
    logger,
)
from database import (
    ADMIN_ID,
    cur,
    db,
    get_country_info,
    get_flag_by_country_name,
    has_perm,
)


auto_upload_waiting = set()
_import_locks = {}


def begin_auto_upload(uid):
    auto_upload_waiting.add(uid)


def _get_import_lock(uid):
    if uid not in _import_locks:
        _import_locks[uid] = asyncio.Lock()
    return _import_locks[uid]


def _is_auto_upload_message(event):
    if not event.file:
        return False
    filename = (event.file.name or "").lower()
    caption = (event.raw_text or "").strip().lower()
    return (
        event.sender_id in auto_upload_waiting
        or caption in {"/auto", "auto", "/autostock", "autostock"}
        or filename.startswith("auto_")
    )


async def _detect_account(client):
    if not await client.is_user_authorized():
        raise ValueError("session is not authorized")

    me = await client.get_me()
    phone = (getattr(me, "phone", None) or "").replace(" ", "").replace("+", "")
    if not phone:
        raise ValueError("session has no phone number")

    password = await client(GetPasswordRequest())
    if password.has_password:
        raise ValueError("account has 2FA enabled")

    year = None
    try:
        async for message in client.iter_messages("me", limit=1, reverse=True):
            if message.date:
                year = message.date.year
                break
    except Exception:
        pass
    if not year:
        year = datetime.now().year

    country, flag = get_country_info(phone)
    return phone, country, flag, year


def _base_price(country, year):
    row = cur.execute(
        "SELECT price FROM auto_prices WHERE country=? AND year=?",
        (country, str(year)),
    ).fetchone()
    if not row:
        row = cur.execute(
            "SELECT price FROM auto_prices WHERE country=? AND year='Common'",
            (country,),
        ).fetchone()
    if row:
        return int(row[0])

    row = cur.execute(
        "SELECT price FROM stock WHERE country_name=? LIMIT 1",
        (country,),
    ).fetchone()
    return int(row[0]) if row else AUTO_STOCK_DEFAULT_COST


def _safe_extract(zip_path, target_dir):
    target_root = Path(target_dir).resolve()
    session_paths = []
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            target = (target_root / member.filename).resolve()
            if target != target_root and target_root not in target.parents:
                raise ValueError("ZIP contains an unsafe path")
            if not member.filename.lower().endswith(".session"):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            session_paths.append(str(target))
    return session_paths


async def _inspect_session(session_file):
    base_path = session_file[:-8] if session_file.endswith(".session") else session_file
    client = TelegramClient(base_path, API_ID, API_HASH)
    try:
        await client.connect()
        return await _detect_account(client)
    finally:
        await client.disconnect()


def _move_session_files(source_file, phone):
    os.makedirs("sessions", exist_ok=True)
    source_base = source_file[:-8] if source_file.endswith(".session") else source_file
    destination_base = os.path.join("sessions", phone)
    for extension in (".session", ".session-wal", ".session-shm", ".session-journal"):
        source = source_base + extension
        if os.path.exists(source):
            if os.path.exists(destination_base + extension):
                os.remove(destination_base + extension)
            shutil.move(source, destination_base + extension)
    return destination_base + ".session"


async def _import_sessions(uid, session_files):
    summary = {"added": 0, "skipped": [], "failed": []}
    seen_phones = set()

    for session_file in session_files:
        try:
            phone, country, flag, year = await _inspect_session(session_file)
            if phone in seen_phones:
                raise ValueError("duplicate phone number in upload")
            seen_phones.add(phone)
            if country == "Unknown":
                raise ValueError("country code is not configured")

            base_price = _base_price(country, year)
            sale_price = base_price + max(0, ACCOUNT_PROFIT)
            stored_path = _move_session_files(session_file, phone)
            cur.execute(
                """
                INSERT OR REPLACE INTO stock
                (phone, session_file, country_name, country_icon, account_year,
                 category, price, available, twofa, cost_price, profit)
                VALUES (?, ?, ?, ?, ?, 'Good', ?, 1, 'None', ?, ?)
                """,
                (
                    phone,
                    stored_path,
                    country,
                    flag or get_flag_by_country_name(country),
                    year,
                    sale_price,
                    base_price,
                    max(0, ACCOUNT_PROFIT),
                ),
            )
            summary["added"] += 1
        except Exception as exc:
            name = os.path.basename(session_file)
            summary["skipped"].append(f"{name}: {exc}")

    db.commit()
    return summary


async def process_auto_upload(event):
    uid = event.sender_id
    auto_upload_waiting.discard(uid)
    filename = (event.file.name or "").lower()
    work_dir = tempfile.mkdtemp(prefix="auto_stock_")
    safe_filename = os.path.basename(event.file.name or "upload")
    downloaded = os.path.join(work_dir, safe_filename)

    try:
        await event.reply(f"{P_WAIT} <b>Validating uploaded account stock...</b>")
        await bot.download_media(event, downloaded)

        if filename.endswith(".zip"):
            session_files = _safe_extract(downloaded, os.path.join(work_dir, "extracted"))
        elif filename.endswith(".session"):
            session_files = [downloaded]
        else:
            return await event.reply(
                f"{P_NO} Send a <code>.session</code> file or a ZIP containing session files."
            )

        if not session_files:
            return await event.reply(f"{P_NO} No <code>.session</code> files were found.")

        async with _get_import_lock(uid):
            summary = await _import_sessions(uid, session_files)

        message = (
            f"{P_YES} <b>Automatic stock import complete</b>\n\n"
            f"{P_PKG} Added: <b>{summary['added']}</b>\n"
            f"{P_INR} Profit per imported account: <b>₹{max(0, ACCOUNT_PROFIT)}</b>"
        )
        if summary["skipped"]:
            preview = "\n".join(
                f"• {html.escape(item)}" for item in summary["skipped"][:10]
            )
            message += (
                f"\n\n{P_NO} Skipped: <b>{len(summary['skipped'])}</b>\n"
                f"<code>{preview}</code>"
            )
        await event.reply(message)
    except zipfile.BadZipFile:
        await event.reply(f"{P_NO} The uploaded ZIP file is invalid or damaged.")
    except Exception as exc:
        logger.exception("Automatic stock import failed: %s", exc)
        await event.reply(f"{P_NO} Automatic import failed. No unvalidated account was added.")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def register_auto_stock(bot):
    @bot.on(events.NewMessage(pattern=r"^/cancel$", func=lambda event: event.sender_id in auto_upload_waiting))
    async def cancel_auto_upload(event):
        auto_upload_waiting.discard(event.sender_id)
        await event.reply("Automatic stock import cancelled.")

    @bot.on(events.NewMessage(func=lambda event: _is_auto_upload_message(event)))
    async def auto_stock_upload(event):
        uid = event.sender_id
        if not AUTO_STOCK_UPLOAD_ENABLED:
            return
        if not (uid == ADMIN_ID or has_perm(uid, "p_add_stock")):
            return
        await process_auto_upload(event)