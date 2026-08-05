from telethon import Button
from telethon.tl.types import ReplyKeyboardMarkup, KeyboardButtonRow, KeyboardButton, KeyboardButtonStyle
from config import TERMS_URL, JOIN_URLS
from database import is_admin, get_support_url

# We use bg_primary (blue), bg_success (green), bg_danger (red)
# For icon, we pass the custom emoji ID (int)

def style_btn(text, data, style_type=None, icon=None):
    return Button.inline(text, data, style=style_type, icon=icon)

def style_url(text, url, style_type=None, icon=None):
    return Button.url(text, url, style=style_type, icon=icon)


def get_terms_buttons():
    buttons = []
    if TERMS_URL and TERMS_URL.startswith("http"):
        buttons.append([Button.url("📜 Read Terms & Conditions", TERMS_URL)])
    buttons.append([
        style_btn("𝐀ᴄᴄᴇᴘᴛ", b"tc_accept", style_type='success', icon=5409380965644514142),
        style_btn("𝐑ᴇᴊᴇᴄᴛ", b"tc_reject", style_type='danger', icon=5354889508674360491)
    ])
    return buttons

def get_join_buttons():
    buttons = [[Button.url(f"📢 Join Channel {i+1}", link)] for i, link in enumerate(JOIN_URLS) if link]
    buttons.append([style_btn("𝐕ᴇʀɪғʏ 𝐉ᴏɪɴᴇᴅ", b"verify_join", style_type='success', icon=6129627894349045589)])
    return buttons

def get_persistent_menu(uid):
    from database import is_admin
    from telethon import Button
    buttons = [
        [Button.text("🛒 𝐁ᴜʏ 𝐀ᴄᴄᴏᴜɴᴛ", style="success", icon=5440627033111557670), Button.text("💳 𝐃ᴇᴘᴏsɪᴛ", style="primary", icon=5409271925014801629)],
        [Button.text("📁 𝐁ᴏᴛ 𝐑ᴇᴘᴏs", style="primary", icon=5409271925014801629), Button.text("📊 𝐒𝐌𝐌 𝐒ᴇʀᴠɪᴄᴇs", style="success", icon=5409098988156629257)],
        [Button.text("👤 𝐏ʀᴏғɪʟᴇ", style="primary", icon=6203982793379154737), Button.text("📦 𝐌ʏ 𝐎ʀᴅᴇʀs", style="primary", icon=5409098988156629257)],
        [Button.text("💰 𝐁ᴀʟᴀɴᴄᴇ", style="success", icon=5409320020058584473), Button.text("📊 𝐒ᴛᴏᴄᴋ", style="primary", icon=6129627894349045589)],
        [Button.text("🎁 𝐑ᴇғᴇʀ", style="success", icon=5354889508674360491), Button.text("📩 𝐒ᴜᴘᴘᴏʀᴛ", style="primary", icon=6129732880529628243)],
        [Button.text("🏠 𝐒ᴛᴀʀᴛ", style="success", icon=6129399728506412489)]
    ]
    if is_admin(uid):
        buttons.append([Button.text("🔐 𝐀ᴅᴍɪɴ 𝐏ᴀɴᴇʟ", style="danger", icon=5409166771330494453)])
    return buttons

def get_support_buttons():
    buttons = [
        [Button.url("📩 Support", get_support_url())],
    ]
    if TERMS_URL and TERMS_URL.startswith("http"):
        buttons.append([Button.url("📜 Terms & Conditions", TERMS_URL)])
    if JOIN_URLS:
        buttons.append([Button.url("📢 Channel", JOIN_URLS[0])])
    return buttons

def get_keypad():
    return [
        [style_btn("1", b"kp_1", style_type="primary", icon=6064275556008989746), style_btn("2", b"kp_2", style_type="primary", icon=5409337058193847247), style_btn("3", b"kp_3", style_type="primary", icon=5355292788923593967)],
        [style_btn("4", b"kp_4", style_type="primary", icon=5409320020058584473), style_btn("5", b"kp_5", style_type="primary", icon=6064310143380625195), style_btn("6", b"kp_6", style_type="primary", icon=6129399728506412489)],
        [style_btn("7", b"kp_7", style_type="primary", icon=6129779562529168023), style_btn("8", b"kp_8", style_type="primary", icon=6154249597532248059), style_btn("9", b"kp_9", style_type="primary", icon=6129812419028982717)],
        [style_btn("Del", b"kp_del", style_type="danger", icon=6129731974291527294), style_btn("0", b"kp_0", style_type="primary", icon=6203982793379154737), style_btn("Confirm", b"kp_done", style_type="success", icon=6129399728506412489)],
        [style_btn("𝐂ᴀɴᴄᴇʟ", b"cancel_action", style_type="danger", icon=6064310143380625195)]
    ]
