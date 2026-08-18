import os
import re

files = [
    '/home/ubuntu/Numbott_Telethon/plugins/start.py',
    '/home/ubuntu/Numbott_Telethon/plugins/profile.py',
    '/home/ubuntu/Numbott_Telethon/plugins/deposit.py',
    '/home/ubuntu/Numbott_Telethon/plugins/buy.py',
    '/home/ubuntu/Numbott_Telethon/plugins/admin.py'
]

# We will search for all assignments to msg: msg = (f"..." or msg = f"..."
# and wrap them in <blockquote>...</blockquote>. We must handle them specifically to not break python code.

# To be perfectly safe, let's manually target the known lines we want to change in each file using replace().

replacements = {
    '/home/ubuntu/Numbott_Telethon/plugins/start.py': [
        ('msg = (f"{PE_HEART}', 'msg = (f"<blockquote>{PE_HEART}'),
        ('👨‍💻 <b>𝐃ᴇᴠᴇʟᴏᴘᴇʀ:</b> @I_VIP_RADHE_II")', '👨‍💻 <b>𝐃ᴇᴠᴇʟᴏᴘᴇʀ:</b> @Demon_x_coder_aura</blockquote>")'),
        ('msg = f"{PE_FLOWER}', 'msg = f"<blockquote>{PE_FLOWER}'),
        ('Verify Joined</b>."', 'Verify Joined</b>.</blockquote>"'),
        ('before using the bot."', 'before using the bot.</blockquote>"')
    ],
    '/home/ubuntu/Numbott_Telethon/plugins/profile.py': [
        ('msg = (f"{PE_KISS}', 'msg = (f"<blockquote expandable>{PE_KISS}'),
        ('bonuses!)</i>")', 'bonuses!)</i></blockquote>")'),
        ('msg = (f"{PE_CROWN}', 'msg = (f"<blockquote>{PE_CROWN}'),
        ('Total Deposited:</b>\\n${to_usd(dep):.2f}")', 'Total Deposited:</b>\\n<tg-spoiler>${to_usd(dep):.2f}</tg-spoiler></blockquote>")'),
        ('msg = f"{PE_FLOWER}', 'msg = f"<blockquote>{PE_FLOWER}'),
        ('msg += "No purchases found."', 'msg += "No purchases found.</blockquote>"'),
        ('msg += f"{P_PHONE}', 'msg += f"<blockquote>{P_PHONE}'),
        ('────────────────\\n"', '────────────────</blockquote>\\n"'),
        ('{uid}</code>', '<tg-spoiler>{uid}</tg-spoiler>'),
        ('₹{bal}', '<tg-spoiler>₹{bal}</tg-spoiler>')
    ],
    '/home/ubuntu/Numbott_Telethon/plugins/deposit.py': [
        ('msg = f"{PE_GIFT}', 'msg = f"<blockquote>{PE_GIFT}'),
        ('Choose your preferred payment method below:"', 'Choose your preferred payment method below:</blockquote>"'),
        ('msg = (f"{P_CARD}', 'msg = (f"<blockquote>{P_CARD}'),
        ('Transaction Hash (Link) or a Screenshot of the payment now.")', 'Transaction Hash (Link) or a Screenshot of the payment now.</blockquote>")'),
        ('cap = row[0] + f"{rate_text}', 'cap = "<blockquote>" + row[0] + f"{rate_text}'),
        ('send a clear Screenshot here:"', 'send a clear Screenshot here:</blockquote>"'),
        ('user_msg = (f"{PE_CHECK}', 'user_msg = (f"<blockquote>{PE_CHECK}'),
        ('({P_INR}{prev_bal+amt})")', '({P_INR}{prev_bal+amt})</blockquote>")')
    ],
    '/home/ubuntu/Numbott_Telethon/plugins/buy.py': [
        ('msg = f"{PE_LOCATION}', 'msg = f"<blockquote>{PE_LOCATION}'),
        ('Select a Country:</b> (Page {page})"', 'Select a Country:</b> (Page {page})</blockquote>"'),
        ('await event.edit(f"{flag}', 'await event.edit(f"<blockquote>{flag}'),
        ('{country}:</b>",', '{country}:</b></blockquote>",'),
        ('msg = f"{PE_GIFT}', 'msg = f"<blockquote>{PE_GIFT}'),
        ('Are you sure?"', 'Are you sure?</blockquote>"'),
        ('msg = (f"{PE_LIGHTNING}', 'msg = (f"<blockquote expandable>{PE_LIGHTNING}'),
        ('refund your balance automatically.</i>")', 'refund your balance automatically.</i></blockquote>")'),
        ('msg_text = (f"{PE_CHECK}', 'msg_text = (f"<blockquote>{PE_CHECK}'),
        ('{twofa_text}")', '{twofa_text}</blockquote>")'),
        ('{code}</code>', '<tg-spoiler>{code}</tg-spoiler>'),
        ('{twofa}</code>', '<tg-spoiler>{twofa}</tg-spoiler>'),
        ('({count})', '(<tg-spoiler>{count}</tg-spoiler>)')
    ],
    '/home/ubuntu/Numbott_Telethon/plugins/admin.py': [
        ('header = (f"{PE_CROWN}', 'header = (f"<blockquote>{PE_CROWN}'),
        ('Pending Deposits: <b>{pending_deposits}</b>")', 'Pending Deposits: <b><tg-spoiler>{pending_deposits}</tg-spoiler></b></blockquote>")'),
        ('msg = (f"{P_STATS}', 'msg = (f"<blockquote expandable>{P_STATS}'),
        ('Overall Sales Amount:</b> {P_INR}{total_spent}")', 'Overall Sales Amount:</b> <tg-spoiler>{P_INR}{total_spent}</tg-spoiler></blockquote>")')
    ]
}

for filepath, reps in replacements.items():
    if not os.path.exists(filepath): continue
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in reps:
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Blockquotes and Spoilers injected.")
