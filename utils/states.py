#MADE_BY_MADARA
#TRUE LODA LOVE

import asyncio

active_orders = {}      
waiting_proof = {}      
deposit_input = {} 
admin_dep_state = {}    
user_spam_cooldown = {} 
session_buy_state = {}  
custom_dep_amt = {}     
user_locks = {}
admin_state = {}
def get_user_lock(uid):
    if uid not in user_locks:
        user_locks[uid] = asyncio.Lock()
    return user_locks[uid]
