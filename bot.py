import telebot
from telebot import types
import sqlite3, requests, time
from datetime import datetime

# ================= CONFIG =================
BOT_TOKEN = "8659832644:AAGG8M0i6zWRas4e_j80FLYWFraaQu8vZ7k" # আপনার টোকেন দিন
ADMIN_IDS = [7276206449]
CHANNELS = ["@mbtcyber", "@unknown_owner_info"]
LOG_GROUP_ID = -1002740128760
API_URL = "https://store.abdulstoreapi.workers.dev/api/v1?key=ak_14e69e6604def065e627fc9910a8868c&userid="
JOIN_BONUS = 1
REF_BONUS = 2

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    return conn

db = get_db()
cur = db.cursor()

# Table initialization
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
cur.execute("INSERT OR IGNORE INTO stats(rowid, bot_status) VALUES(1, 1)")
db.commit()

# Column update (Safe way)
def update_db_schema():
    columns = [row[1] for row in cur.execute("PRAGMA table_info(users)")]
    if "username" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN username TEXT DEFAULT 'NoUsername'")
    if "searches" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN searches INTEGER DEFAULT 0")
    db.commit()

update_db_schema()

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

# ================= HANDLERS =================

@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    if not is_joined(uid):
        return force_join_handler(m)
        
    username = m.from_user.username or "NoUsername"
    
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    user_exists = cur.fetchone()
    
    if not user_exists:
        args = m.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != uid else None
        
        cur.execute("INSERT INTO users(user_id, username, balance, join_date, referred_by, searches) VALUES(?,?,?,?,?,?)",
                    (uid, username, JOIN_BONUS, datetime.now().strftime("%Y-%m-%d"), ref_id, 0))
        
        if ref_id:
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (REF_BONUS, ref_id))
            try: bot.send_message(ref_id, f"🎁 <b>Referral Bonus!</b>\n+{REF_BONUS} credits added.")
            except: pass
        db.commit()
    else:
        cur.execute("UPDATE users SET username=? WHERE user_id=?", (username, uid))
        db.commit()
        
    bot.send_message(m.chat.id, f"👋 <b>Hello {m.from_user.first_name}!</b>\nWelcome to the ULTRA Search Bot.", reply_markup=main_menu(uid))

# Force Join Display
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

# ================= SEARCH LOGIC =================

@bot.message_handler(func=lambda m: m.text == "🔎 Search User")
def ask_search_id(m):
    uid = m.from_user.id
    if not is_joined(uid): return force_join_handler(m)

    cur.execute("SELECT bot_status FROM stats")
    is_on = cur.fetchone()[0]
    
    if is_on == 0 and uid not in ADMIN_IDS:
        return bot.send_message(m.chat.id, "⚠️ <b>Bot is currently OFF by Admin.</b>")

    cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    bal = cur.fetchone()[0]
    
    if bal < 1:
        return bot.send_message(m.chat.id, "❌ <b>Insufficient Credits!</b>\nRefer friends to earn more.")
    
    msg = bot.send_message(m.chat.id, "📩 Send the User <b>Chat ID</b> you want to search:", reply_markup=back_kb())
    bot.register_next_step_handler(msg, perform_search)

def perform_search(m):
    uid = m.from_user.id
    target_id = m.text

    if target_id == "⬅ Back":
        return bot.send_message(m.chat.id, "🔙 Main Menu", reply_markup=main_menu(uid))
    
    if not target_id.isdigit():
        msg = bot.send_message(m.chat.id, "⚠️ Invalid ID! Numeric Chat ID only:")
        return bot.register_next_step_handler(msg, perform_search)

    wait = bot.send_message(m.chat.id, f"🛰 <b>Searching {target_id} in Database...</b>")
    
    try:
        r = requests.get(API_URL + str(target_id), timeout=20).json()
        if r.get("status") == "success" and r.get("data", {}).get("found"):
            info = r["data"]
            res_text = f"""
✨ <b>User Details Found</b> ✨
━━━━━━━━━━━━━━
🆔 ID: <code>{target_id}</code>
📱 Number: <code>{info.get('number','N/A')}</code>
🌍 Country: {info.get('country','N/A')}
━━━━━━━━━━━━━━
💳 Credits Deducted: 1
"""
            cur.execute("UPDATE users SET balance = balance - 1, searches = searches + 1 WHERE user_id = ?", (uid,))
            db.commit()
            bot.edit_message_text(res_text, m.chat.id, wait.message_id)
        else:
            bot.edit_message_text("❌ <b>No Data Found!</b>", m.chat.id, wait.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ API Error!", m.chat.id, wait.message_id)

# ================= ADMIN PANEL =================

@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and (m.text == "⚙ Admin Panel" or m.text == "⬅ Back"))
def admin_menu(m):
    cur.execute("SELECT COUNT(*), SUM(balance), SUM(searches) FROM users")
    stats = cur.fetchone()
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📴 Bot OFF", "📳 Bot ON")
    kb.row("➕ Add Credit", "➖ Remove Credit")
    kb.row("📣 Broadcast", "📋 Users Stats")
    kb.row("⬅ Back")
    bot.send_message(m.chat.id, f"👮 <b>Admin Panel</b>\n\nTotal Users: {stats[0]}\nTotal Balance: {stats[1]}\nSearches: {stats[2]}", reply_markup=kb)

@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text == "📴 Bot OFF")
def bot_off(m):
    cur.execute("UPDATE stats SET bot_status=0")
    db.commit()
    bot.send_message(m.chat.id, "📴 Bot is now OFF")

@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text == "📳 Bot ON")
def bot_on(m):
    cur.execute("UPDATE stats SET bot_status=1")
    db.commit()
    bot.send_message(m.chat.id, "📳 Bot is now ON")

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def my_stats(m):
    cur.execute("SELECT balance, searches FROM users WHERE user_id=?", (m.from_user.id,))
    res = cur.fetchone()
    bot.send_message(m.chat.id, f"📊 <b>Account Stats</b>\n\n💳 Credits: {res[0]}\n🔎 Total Searches: {res[1]}")

# ... (Keep Refer & Earn, Support, and Pagination functions same as your original) ...

# ================= RUN =================
if __name__ == "__main__":
    print("🔥 ULTRA Bot is Online!")
    bot.infinity_polling(skip_pending=True)
