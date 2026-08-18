import os
import re
import random

emoji_ids = [
    5375125990118793401, 5409271925014801629, 5409119256107297715, 5408995930416362034, 
    5409098988156629257, 5409166771330494453, 5409380965644514142, 5409337058193847247, 
    5409320020058584473, 5408832111773757273, 5440627033111557670, 6203982793379154737, 
    6064310143380625195, 6064275556008989746, 5355292788923593967, 6154249597532248059, 
    5354889508674360491, 6170048080679801421, 6129399728506412489, 6129779562529168023, 
    6129627894349045589, 6129732880529628243, 6129731974291527294, 6129432481927010933, 
    6129888444245089008, 5796170975699544141, 6129812419028982717, 6129650743575060215
]

files = [
    '/home/ubuntu/Numbott_Telethon/utils/keyboards.py',
    '/home/ubuntu/Numbott_Telethon/plugins/admin.py',
    '/home/ubuntu/Numbott_Telethon/plugins/buy.py',
    '/home/ubuntu/Numbott_Telethon/plugins/deposit.py'
]

# We want to replace `style_btn("...", "...", "type")` with `style_btn("...", "...", "type", icon=XXX)`
# And `icon=5409098988156629257` with `icon=XXX`
def replace_icon(match):
    prefix = match.group(1)
    return f"{prefix}, icon={random.choice(emoji_ids)})"

def replace_existing_icon(match):
    prefix = match.group(1)
    return f"{prefix}icon={random.choice(emoji_ids)}"

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Replace existing icons
    content = re.sub(r"(style_btn\([^)]*?)icon=\d+", replace_existing_icon, content)
    
    # 2. Add icons to style_btn that don't have them
    # Match style_btn("...", "...", "...") where it ends with ) and does NOT have icon=
    def add_icon(m):
        inner = m.group(1)
        if "icon=" not in inner:
            return f"style_btn({inner}, icon={random.choice(emoji_ids)})"
        return m.group(0)
    
    content = re.sub(r"style_btn\(([^)]+)\)", add_icon, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Icons randomized.")

