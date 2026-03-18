import telebot
from telebot import types
import sqlite3, requests, time
from datetime import datetime

# ================= CONFIG =================
BOT_TOKEN = "8659832644:AAGG8M0i6zWRas4e_j80FLYWFraaQu8vZ7k" # নিজের টোকেনটি এখানে রাখুন
ADMIN_IDS = [7276206449]
CHANNELS = ["@mbtcyber", "@unknown_owner_info"]
LOG_GROUP_ID = -1002740128760
API_URL = "https://store.abdulstoreapi.workers.dev/api/v1?key=ak_14e69e6604def065e627fc9910a8868c&userid="
JOIN_BONUS = 1
REF_BONUS = 2

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ================= DATABASE =================
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()
# --- কলামগুলো চেক এবং অ্যাড করার জন্য এই অংশটুকু যোগ করুন ---
try:
    cur.execute("ALTER TABLE users ADD COLUMN username TEXT DEFAULT 'NoUsername'")
    db.commit()
except: pass

try:
    cur.execute("ALTER TABLE users ADD COLUMN searches INTEGER DEFAULT 0")
    db.commit()
except: pass

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 1,
    join_date TEXT,
    referred_by INTEGER,
    searches INTEGER DEFAULT 0
)
""")

cur.execute("CREATE TABLE IF NOT EXISTS stats(bot_status INTEGER DEFAULT 1)")
cur.execute("INSERT OR IGNORE INTO stats(bot_status) VALUES(1)")
db.commit()

# ================= UTILS =================
def is_joined(uid):
    for ch in CHANNELS:
        try:
            m = bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔎 Search User", "📊 My Stats")
    kb.row("👥 Refer & Earn", "🆘 Support")
    if uid in ADMIN_IDS:
        kb.row("⚙ Admin Panel")
    return kb

def back_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅ Back")
    return kb

# ================= FORCE JOIN =================
@bot.message_handler(func=lambda m: not is_joined(m.from_user.id))
def force_join_handler(m):
    kb = types.InlineKeyboardMarkup()
    for i, ch in enumerate(CHANNELS, 1):
        kb.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(types.InlineKeyboardButton("🔄 Check Join", callback_data="check_join"))
    bot.send_message(m.chat.id, "❌ <b>Access Denied!</b>\nJoin all channels to use the bot.", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_callback(c):
    if is_joined(c.from_user.id):
        bot.delete_message(c.message.chat.id, c.message.message_id)
        bot.send_message(c.message.chat.id, "✅ <b>Success! You can use the bot now.</b>", reply_markup=main_menu(c.from_user.id))
    else:
        bot.answer_callback_query(c.id, "❌ You haven't joined all channels!", show_alert=True)

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    username = m.from_user.username or "NoUsername"
    
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    user_exists = cur.fetchone()
    
    if not user_exists:
        # নতুন ইউজার হলে এখানে ডাটা সেভ হবে
        args = m.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != uid else None
        
        cur.execute("INSERT INTO users(user_id, username, balance, join_date, referred_by, searches) VALUES(?,?,?,?,?,?)",
                    (uid, username, JOIN_BONUS, datetime.now().strftime("%Y-%m-%d"), ref_id, 0))
        
        if ref_id:
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (REF_BONUS, ref_id))
            try: 
                bot.send_message(ref_id, f"🎁 <b>Referral Bonus!</b>\n+{REF_BONUS} credits added.")
            except: 
                pass
        db.commit()
    else:
        # পুরনো ইউজার হলেও তার ইউজারনেম আপডেট করে দিচ্ছি (যাতে @NoUsername চলে যায়)
        cur.execute("UPDATE users SET username=? WHERE user_id=?", (username, uid))
        db.commit()
        
    bot.send_message(m.chat.id, f"👋 <b>Hello {m.from_user.first_name}!</b>\nWelcome to the ULTRA Search Bot.", reply_markup=main_menu(uid))

# ================= ADMIN MASTER HANDLER =================
@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text in ["⚙ Admin Panel", "📴 Bot OFF", "📳 Bot ON", "📋 Users Stats", "📣 Broadcast", "➕ Add Credit", "➖ Remove Credit"])
def admin_panel_logic(m):
    if m.text == "⚙ Admin Panel":
        cur.execute("SELECT COUNT(*), SUM(balance), SUM(searches) FROM users")
        stats = cur.fetchone()
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("📴 Bot OFF", "📳 Bot ON")
        kb.row("➕ Add Credit", "➖ Remove Credit", "📣 Broadcast")
        kb.row("📋 Users Stats", "⬅ Back")
        bot.send_message(m.chat.id, f"👮 <b>Admin Panel</b>\n\nTotal Users: {stats[0]}\nTotal Balance: {stats[1]}\nTotal Searches: {stats[2]}", reply_markup=kb)

    elif m.text == "📴 Bot OFF":
        cur.execute("UPDATE stats SET bot_status=0")
        db.commit()
        bot.send_message(m.chat.id, "📴 Bot is now OFF")

    elif m.text == "📳 Bot ON":
        cur.execute("UPDATE stats SET bot_status=1")
        db.commit()
        bot.send_message(m.chat.id, "📳 Bot is now ON")

    elif m.text == "📋 Users Stats":
        cur.execute("SELECT user_id, username, balance FROM users LIMIT 30")
        users = cur.fetchall()
        res = "📋 <b>User List:</b>\n\n"
        for u in users:
            res += f"ID: <code>{u[0]}</code> | @{u[1]} | Bal: {u[2]}\n"
        bot.send_message(m.chat.id, res)

    elif m.text == "📣 Broadcast":
        msg = bot.send_message(m.chat.id, "Send message to broadcast:", reply_markup=back_kb())
        bot.register_next_step_handler(msg, process_broadcast)

    elif m.text in ["➕ Add Credit", "➖ Remove Credit"]:
        mode = "ADD" if "Add" in m.text else "REMOVE"
        msg = bot.send_message(m.chat.id, "Send <b>UserID Amount</b> (e.g. 7276206449 10):", reply_markup=back_kb())
        bot.register_next_step_handler(msg, lambda x: process_credit_change(x, mode))

# --- ADMIN SUB-FUNCTIONS ---
def process_broadcast(m):
    if m.text == "⬅ Back": return
    cur.execute("SELECT user_id FROM users")
    all_u = cur.fetchall()
    count = 0
    for u in all_u:
        try:
            bot.copy_message(u[0], m.chat.id, m.message_id)
            count += 1
        except: pass
    bot.send_message(m.chat.id, f"✅ Broadcast sent to {count} users.")

def process_credit_change(m, mode):
    if m.text == "⬅ Back": return
    try:
        target_id, amount = map(int, m.text.split())
        operator = "+" if mode == "ADD" else "-"
        cur.execute(f"UPDATE users SET balance = balance {operator} ? WHERE user_id = ?", (amount, target_id))
        db.commit()
        bot.send_message(m.chat.id, f"✅ Success! {mode}ed {amount} credits.")
    except:
        bot.send_message(m.chat.id, "❌ Error! Use format: ID AMOUNT")

# ================= SEARCH LOGIC =================
# ================= SEARCH LOGIC (Updated) =================
@bot.message_handler(func=lambda m: m.text == "🔎 Search User")
def ask_search_id(m):
    uid = m.from_user.id
    
    # ১. প্রথমে চেক করবে বট কি অফ? (অ্যাডমিনরা অফ থাকলেও সার্চ করতে পারবে)
    cur.execute("SELECT bot_status FROM stats")
    status_row = cur.fetchone()
    is_on = status_row[0] if status_row else 1
    
    if is_on == 0 and uid not in ADMIN_IDS:
        return bot.send_message(m.chat.id, "⚠️ <b>Bot is currently OFF by Admin.</b>\nPlease try again later...")

    # ২. ব্যালেন্স চেক
    cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    user_data = cur.fetchone()
    bal = user_data[0] if user_data else 0
    
    if bal < 1:
        return bot.send_message(m.chat.id, "❌ <b>Insufficient Credits!</b>\nRefer friends to earn more.")
    
    # ৩. ইনপুট নেওয়া
    msg = bot.send_message(m.chat.id, "If You don't know what is Chat ID tap <b>support<\b> \n📩 Send the User <b>Chat ID</b> you want to search Number:", reply_markup=back_kb())
    bot.register_next_step_handler(msg, perform_search)

def perform_search(m):
    uid = m.from_user.id
    target_id = m.text

    # ব্যাক বাটনের কাজ
    if target_id == "⬅ Back":
        return bot.send_message(m.chat.id, "🔙 Main Menu", reply_markup=main_menu(uid))
    
    # আইডি কি নাম্বার?
    if not target_id.isdigit():
        msg = bot.send_message(m.chat.id, "⚠️ Invalid ID! Please send a numeric Chat ID:")
        return bot.register_next_step_handler(msg, perform_search)

    wait = bot.send_message(m.chat.id, "🛰 <b>Searching {target_id} in Database...</b>")
    
    try:
        # API Call
        r = requests.get(API_URL + str(target_id), timeout=35).json()
        
        if r.get("status") == "success" and r.get("data", {}).get("found"):
            info = r["data"]
            res_text = f"""
✨ <b>User Details Found</b> ✨
━━━━━━━━━━━━━━
🆔 ID: <code>{target_id}</code>
👤 Country Code: <code>{info.get('country_code','N/A')}</code>
📱 Number: <code>{info.get('number','N/A')}</code>
🌍 Country: {info.get('country','N/A')}
━━━━━━━━━━━━━━
💳 Credits Deducted: 1\n
<b>................................................</b>\n
<b>DEVELOPED BY:</b> @Unkonwn_BMT
"""
            # ব্যালেন্স কাটা এবং সার্চ কাউন্ট বাড়ানো
            cur.execute("UPDATE users SET balance = balance - 1, searches = searches + 1 WHERE user_id = ?", (uid,))
            db.commit()
            bot.edit_message_text(res_text, m.chat.id, wait.message_id)
            
            # লগ পাঠানো
            try: bot.send_message(LOG_GROUP_ID, f"🔍 User <code>{uid}</code> searched <code>{target_id}</code>")
            except: pass
        else:
            bot.edit_message_text("❌ <b>No Data Found!</b>", m.chat.id, wait.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ <b>API Error!</b>\nDetails: {str(e)}", m.chat.id, wait.message_id)

# ================= ADMIN CONTROL (Ensure this matches) =================
@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text in ["📴 Bot OFF", "📳 Bot ON"])
def toggle_bot(m):
    if m.text == "📴 Bot OFF":
        cur.execute("UPDATE stats SET bot_status=0")
        db.commit()
        bot.send_message(m.chat.id, "✅ Bot has been turned <b>OFF</b> for users.")
    elif m.text == "📳 Bot ON":
        cur.execute("UPDATE stats SET bot_status=1")
        db.commit()
        bot.send_message(m.chat.id, "✅ Bot is now <b>ON</b>.")
# ================= OTHER BUTTONS =================
@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def my_stats(m):
    cur.execute("SELECT balance, searches FROM users WHERE user_id=?", (m.from_user.id,))
    res = cur.fetchone()
    bot.send_message(m.chat.id, f"📊 <b>Account Stats</b>\n\n💳 Credits: {res[0]}\n🔎 Total Searches: {res[1]}")

@bot.message_handler(func=lambda m: m.text == "👥 Refer & Earn")
def refer_earn(m):
    bot_info = bot.get_me()
    link = f"<code>https://t.me/{bot_info.username}?start={m.from_user.id}</code>"
    bot.send_message(m.chat.id, f"👥 <b>Referral Program</b>\n\nEarn <b>{REF_BONUS} credits</b> for each person you invite!\n\n🔗 Your Link: {link}")

@bot.message_handler(func=lambda m: m.text == "⬅ Back")
def back_btn(m):
    bot.send_message(m.chat.id, "🔙 Main Menu", reply_markup=main_menu(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🆘 Support")
def support(m):
    bot.send_message(m.chat.id, "🆘 For support contact: @Unkonwn_BMT")
@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text == "📋 Users Stats")
def admin_users_list(m):
    # সরাসরি প্রথম পেজ (Page 0) কল করবে
    send_user_page(m.chat.id, page=0)
def send_user_page(chat_id, page=0, message_id=None):
    limit = 10  # প্রতি পেজে ১০ জন ইউজার দেখাবে
    offset = page * limit
    
    try:
        # ডাটাবেজ থেকে ইউজার আনা
        cur.execute("SELECT user_id, username, balance, searches FROM users ORDER BY searches DESC LIMIT ? OFFSET ?", (limit, offset))
        users = cur.fetchall()
        
        # মোট ইউজার সংখ্যা বের করা
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        total_pages = (total_users + limit - 1) // limit

        if not users:
            return bot.send_message(chat_id, "📭 No users found in database.")

        msg = f"📋 <b>User List (Page {page + 1}/{total_pages})</b>\n"
        msg += f"Total Database Users: {total_users}\n"
        msg += "━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, u in enumerate(users, offset + 1):
            uid, uname, bal, src = u
            username = f"@{uname}" if uname != "NoUsername" else "No User"
            msg += f"{i}. {username}\n   ├ ID: <code>{uid}</code>\n   └ 💰 Bal: {bal} | 🔎 Src: {src}\n\n"

        # বাটন তৈরি (Next/Previous)
        kb = types.InlineKeyboardMarkup()
        btns = []
        if page > 0:
            btns.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"userpage_{page-1}"))
        if offset + limit < total_users:
            btns.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"userpage_{page+1}"))
        
        if btns:
            kb.row(*btns)
        
        if message_id:
            bot.edit_message_text(msg, chat_id, message_id, reply_markup=kb, parse_mode="HTML")
        else:
            bot.send_message(chat_id, msg, reply_markup=kb, parse_mode="HTML")
            
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# ইনলাইন বাটনের ক্লিক হ্যান্ডেল করার জন্য
@bot.callback_query_handler(func=lambda c: c.data.startswith("userpage_"))
def user_page_callback(c):
    if c.from_user.id not in ADMIN_IDS:
        return bot.answer_callback_query(c.id, "❌ Access Denied!", show_alert=True)
    
    page = int(c.data.split("_")[1])
    send_user_page(c.message.chat.id, page=page, message_id=c.message.message_id)
    bot.answer_callback_query(c.id)
# ================= RUN =================
print("🔥 ULTRA Bot is Online!")
bot.infinity_polling()
