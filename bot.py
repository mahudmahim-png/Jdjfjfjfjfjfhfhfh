import telebot
from telebot import types
import sqlite3, requests
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
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

def init_db():
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
    
    # কলাম চেক (যদি আগে না থাকে)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN username TEXT DEFAULT 'NoUsername'")
        cur.execute("ALTER TABLE users ADD COLUMN searches INTEGER DEFAULT 0")
    except:
        pass
    db.commit()

init_db()

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

# ================= START & REGISTRATION =================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    if not is_joined(uid):
        return show_force_join(m.chat.id)

    username = m.from_user.username or "NoUsername"
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()

    if not user:
        args = m.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != uid else None
        
        cur.execute("INSERT INTO users(user_id, username, balance, join_date, referred_by, searches) VALUES(?,?,?,?,?,?)",
                    (uid, username, JOIN_BONUS, datetime.now().strftime("%Y-%m-%d"), ref_id, 0))
        
        if ref_id:
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (REF_BONUS, ref_id))
            try: bot.send_message(ref_id, f"🎁 <b>Referral Bonus!</b>\n+{REF_BONUS} credits added.")
            except: pass
        db.commit()
    
    bot.send_message(m.chat.id, f"👋 <b>Hello {m.from_user.first_name}!</b>\nWelcome to ULTRA Search Bot.", reply_markup=main_menu(uid))

def show_force_join(chat_id):
    kb = types.InlineKeyboardMarkup()
    for i, ch in enumerate(CHANNELS, 1):
        kb.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(types.InlineKeyboardButton("🔄 Check Join", callback_data="check_join"))
    bot.send_message(chat_id, "❌ <b>Access Denied!</b>\nJoin all channels first.", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_callback(c):
    if is_joined(c.from_user.id):
        bot.delete_message(c.message.chat.id, c.message.message_id)
        bot.send_message(c.message.chat.id, "✅ Joined! You can use the bot now.", reply_markup=main_menu(c.from_user.id))
    else:
        bot.answer_callback_query(c.id, "❌ You haven't joined yet!", show_alert=True)

# ================= BUTTON HANDLERS =================

@bot.message_handler(func=lambda m: True)
def handle_all_messages(m):
    uid = m.from_user.id
    text = m.text

    if not is_joined(uid):
        return show_force_join(m.chat.id)

    # --- 1. BACK BUTTON ---
    if text == "⬅ Back":
        return bot.send_message(m.chat.id, "🔙 Main Menu", reply_markup=main_menu(uid))

    # --- 2. SEARCH USER ---
    elif text == "🔎 Search User":
        cur.execute("SELECT bot_status FROM stats")
        if cur.fetchone()[0] == 0 and uid not in ADMIN_IDS:
            return bot.send_message(m.chat.id, "⚠️ Bot is OFF by admin.")

        cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        if cur.fetchone()[0] < 1:
            return bot.send_message(m.chat.id, "❌ No credits! Refer others to earn.")

        msg = bot.send_message(m.chat.id, "📩 Send the <b>Chat ID</b> you want to search:", reply_markup=back_kb())
        bot.register_next_step_handler(msg, perform_search)

    # --- 3. MY STATS ---
    elif text == "📊 My Stats":
        cur.execute("SELECT balance, searches FROM users WHERE user_id=?", (uid,))
        data = cur.fetchone()
        bot.send_message(m.chat.id, f"📊 <b>Your Stats</b>\n\n💳 Credits: {data[0]}\n🔎 Total Searches: {data[1]}")

    # --- 4. REFER & EARN ---
    elif text == "👥 Refer & Earn":
        bot_user = bot.get_me().username
        link = f"https://t.me/{bot_user}?start={uid}"
        bot.send_message(m.chat.id, f"👥 <b>Referral Program</b>\n\nInvite link:\n<code>{link}</code>\n\nBonus: {REF_BONUS} Credits.")

    # --- 5. SUPPORT ---
    elif text == "🆘 Support":
        bot.send_message(m.chat.id, "🆘 Support: @Unkonwn_BMT")

    # --- 6. ADMIN PANEL ---
    elif text == "⚙ Admin Panel" and uid in ADMIN_IDS:
        show_admin_panel(m)

    # --- 7. ADMIN ACTIONS ---
    elif uid in ADMIN_IDS:
        if text == "📴 Bot OFF":
            cur.execute("UPDATE stats SET bot_status=0")
            db.commit()
            bot.send_message(m.chat.id, "✅ Bot Turned OFF")
        elif text == "📳 Bot ON":
            cur.execute("UPDATE stats SET bot_status=1")
            db.commit()
            bot.send_message(m.chat.id, "✅ Bot Turned ON")
        elif text == "📋 Users Stats":
            send_user_page(m.chat.id, 0)
        elif text == "📣 Broadcast":
            msg = bot.send_message(m.chat.id, "Send message to broadcast:", reply_markup=back_kb())
            bot.register_next_step_handler(msg, process_broadcast)
        elif text == "➕ Add Credit":
            msg = bot.send_message(m.chat.id, "Send: <code>ID Amount</code>", reply_markup=back_kb())
            bot.register_next_step_handler(msg, lambda m: process_credit(m, "add"))

# ================= FUNCTIONALITIES =================

def perform_search(m):
    uid = m.from_user.id
    if m.text == "⬅ Back": return handle_all_messages(m)
    
    if not m.text.isdigit():
        msg = bot.send_message(m.chat.id, "⚠️ Invalid ID. Try again:")
        return bot.register_next_step_handler(msg, perform_search)

    wait = bot.send_message(m.chat.id, "🛰 Searching...")
    try:
        r = requests.get(API_URL + m.text, timeout=20).json()
        if r.get("status") == "success" and r.get("data", {}).get("found"):
            info = r["data"]
            res = f"✨ <b>Found!</b>\nID: {m.text}\nNumber: {info.get('number')}\nCountry: {info.get('country')}"
            cur.execute("UPDATE users SET balance = balance - 1, searches = searches + 1 WHERE user_id = ?", (uid,))
            db.commit()
            bot.edit_message_text(res, m.chat.id, wait.message_id)
        else:
            bot.edit_message_text("❌ No data found.", m.chat.id, wait.message_id)
    except:
        bot.edit_message_text("❌ API Error.", m.chat.id, wait.message_id)

def show_admin_panel(m):
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📴 Bot OFF", "📳 Bot ON")
    kb.row("➕ Add Credit", "📣 Broadcast")
    kb.row("📋 Users Stats", "⬅ Back")
    bot.send_message(m.chat.id, f"👮 Admin Panel\nTotal Users: {total}", reply_markup=kb)

def process_broadcast(m):
    if m.text == "⬅ Back": return handle_all_messages(m)
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    for u in users:
        try: bot.copy_message(u[0], m.chat.id, m.message_id)
        except: pass
    bot.send_message(m.chat.id, "✅ Broadcast Done!")

def process_credit(m, type):
    if m.text == "⬅ Back": return handle_all_messages(m)
    try:
        tid, amt = map(int, m.text.split())
        cur.execute(f"UPDATE users SET balance = balance + {amt} WHERE user_id = ?", (tid,))
        db.commit()
        bot.send_message(m.chat.id, "✅ Done!")
    except:
        bot.send_message(m.chat.id, "❌ Invalid Format.")

# --- Pagination (Original Logic) ---
def send_user_page(chat_id, page, message_id=None):
    limit = 10
    offset = page * limit
    cur.execute("SELECT user_id, username, searches FROM users LIMIT ? OFFSET ?", (limit, offset))
    users = cur.fetchall()
    msg = f"📋 User List (Page {page+1}):\n\n"
    for u in users:
        msg += f"ID: {u[0]} | @{u[1]} | Search: {u[2]}\n"
    
    kb = types.InlineKeyboardMarkup()
    if page > 0:
        kb.add(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"userpage_{page-1}"))
    kb.add(types.InlineKeyboardButton("Next ➡️", callback_data=f"userpage_{page+1}"))
    
    if message_id:
        bot.edit_message_text(msg, chat_id, message_id, reply_markup=kb)
    else:
        bot.send_message(chat_id, msg, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("userpage_"))
def user_page_callback(c):
    page = int(c.data.split("_")[1])
    send_user_page(c.message.chat.id, page, c.message.message_id)

# ================= RUN =================
print("🔥 Bot is Online!")
bot.infinity_polling()
