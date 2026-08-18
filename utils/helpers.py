#MADE_BY_MADARA
#TRUE LODA LOVE

import asyncio
from telethon import Button
from telethon.errors import UserNotParticipantError, ChatAdminRequiredError
from telethon.tl.functions.channels import GetParticipantRequest
from config import CHECK_CHANNELS, JOIN_URLS, logger

async def check_channel_joined(bot, uid, is_admin_func):
    """Returns True if all joined, False otherwise."""
    if is_admin_func(uid): return True
    for ch in CHECK_CHANNELS:
        try:
            ch_id = int(ch.strip()) if str(ch).strip().lstrip('-').isdigit() else ch.strip()
            try:
                await bot(GetParticipantRequest(channel=ch_id, participant=uid))
            except ValueError:
                entity = await bot.get_entity(ch_id)
                await bot(GetParticipantRequest(channel=entity, participant=uid))
        except UserNotParticipantError:
            return False
        except ChatAdminRequiredError:
            logger.error(f"Bot is not admin in channel: {ch}")
            return False
        except Exception as e:
            logger.error(f"Channel Check Error for {ch}: {e}")
            return False
    return True

async def get_unjoined_channels(bot, uid):
    """Returns list of (url, index) for channels the user has NOT joined."""
    unjoined = []
    for i, ch in enumerate(CHECK_CHANNELS):
        try:
            ch_id = int(ch.strip()) if str(ch).strip().lstrip('-').isdigit() else ch.strip()
            try:
                await bot(GetParticipantRequest(channel=ch_id, participant=uid))
            except ValueError:
                entity = await bot.get_entity(ch_id)
                await bot(GetParticipantRequest(channel=entity, participant=uid))
        except UserNotParticipantError:
            if i < len(JOIN_URLS):
                unjoined.append((JOIN_URLS[i], i + 1))
        except Exception:
            if i < len(JOIN_URLS):
                unjoined.append((JOIN_URLS[i], i + 1))
    return unjoined
