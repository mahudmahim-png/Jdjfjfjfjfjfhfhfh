import telebot
from telebot import types
import sqlite3, requests
from datetime import datetime

# ================= CONFIG =================
BOT_TOKEN = "8659832644:AAGG8M0i6zWRas4e_j80FLYWFraaQu8vZ7k"
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
    bot.send_message(m.chat.id, "❌ <b>Join all channels first!</b>", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_callback(c):
    if is_joined(c.from_user.id):
        bot.delete_message(c.message.chat.id, c.message.message_id)
        bot.send_message(c.message.chat.id, "✅ Joined!", reply_markup=main_menu(c.from_user.id))
    else:
        bot.answer_callback_query(c.id, "❌ Not joined!", show_alert=True)

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    username = m.from_user.username or "NoUsername"

    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    if not cur.fetchone():
        args = m.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != uid else None

        cur.execute("INSERT INTO users VALUES(?,?,?,?,?,?)",
                    (uid, username, JOIN_BONUS, datetime.now().strftime("%Y-%m-%d"), ref_id, 0))

        if ref_id:
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (REF_BONUS, ref_id))
            try:
                bot.send_message(ref_id, f"🎁You Get Your Referral Bonus +{REF_BONUS}")
            except: pass

        db.commit()
    else:
        cur.execute("UPDATE users SET username=? WHERE user_id=?", (username, uid))
        db.commit()

    bot.send_message(m.chat.id, f"👋 Hello {m.from_user.name}\n<b>Welcome to our search bot</b>", reply_markup=main_menu(uid))

# ================= ADMIN PANEL =================
@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text == "⚙ Admin Panel")
def admin_panel(m):
    cur.execute("SELECT COUNT(*), SUM(balance), SUM(searches) FROM users")
    stats = cur.fetchone()

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📴 Bot OFF", "📳 Bot ON")
    kb.row("➕ Add Credit", "➖ Remove Credit", "📣 Broadcast")
    kb.row("📋 Users Stats", "⬅ Back")

    bot.send_message(m.chat.id,
                     f"👮 Admin Panel\nUsers: {stats[0]}\nBalance: {stats[1]}\nSearch: {stats[2]}",
                     reply_markup=kb)

# ================= ADMIN ACTIONS =================
@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text in ["📴 Bot OFF", "📳 Bot ON"])
def toggle_bot(m):
    status = 0 if "OFF" in m.text else 1
    cur.execute("UPDATE stats SET bot_status=?", (status,))
    db.commit()
    bot.send_message(m.chat.id, f"Bot {'OFF' if status == 0 else 'ON'}")

@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text == "📣 Broadcast")
def broadcast(m):
    msg = bot.send_message(m.chat.id, "Send message:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(m):
    cur.execute("SELECT user_id FROM users")
    for u in cur.fetchall():
        try:
            bot.copy_message(u[0], m.chat.id, m.message_id)
        except: pass
    bot.send_message(m.chat.id, "✅ Done")

@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text in ["➕ Add Credit", "➖ Remove Credit"])
def credit(m):
    mode = 1 if "Add" in m.text else -1
    msg = bot.send_message(m.chat.id, "Send ID Amount")
    bot.register_next_step_handler(msg, lambda x: process_credit(x, mode))

def process_credit(m, mode):
    try:
        uid, amt = map(int, m.text.split())
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt*mode, uid))
        db.commit()
        bot.send_message(m.chat.id, "✅ Success")
    except:
        bot.send_message(m.chat.id, "❌ Error")

# ================= USERS LIST (FIXED) =================
@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text == "📋 Users Stats")
def admin_users(m):
    send_user_page(m.chat.id, 0)

def send_user_page(chat_id, page):
    limit = 10
    offset = page * limit

    cur.execute("SELECT user_id, username, balance, searches FROM users LIMIT ? OFFSET ?", (limit, offset))
    users = cur.fetchall()

    msg = "📋 User List\n\n"
    for u in users:
        msg += f"ID:{u[0]} @{u[1]} Bal:{u[2]} Src:{u[3]}\n"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Next", callback_data=f"page_{page+1}"))

    bot.send_message(chat_id, msg, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("page_"))
def next_page(c):
    page = int(c.data.split("_")[1])
    send_user_page(c.message.chat.id, page)

# ================= SEARCH =================
@bot.message_handler(func=lambda m: m.text == "🔎 Search User")
def search(m):
    cur.execute("SELECT bot_status FROM stats")
    if cur.fetchone()[0] == 0:
        return bot.send_message(m.chat.id, "⚠️ <b>Bot is currently OFF by Admin.</b>\nPlease try again later...")

    cur.execute("SELECT balance FROM users WHERE user_id=?", (m.from_user.id,))
    if cur.fetchone()[0] < 1:
        return bot.send_message(m.chat.id, "❌ No balance")

    msg = bot.send_message(m.chat.id, "If You don't know what is Chat ID tap <b>support<\b> \n📩 Send the User <b>Chat ID</b> you want to search Number:", reply_markup=back_kb())
    bot.register_next_step_handler(msg, do_search)

def do_search(m):
    if m.text == "⬅ Back":
        return bot.send_message(m.chat.id, "Back", reply_markup=main_menu(m.from_user.id))

    if not m.text.isdigit():
        return bot.send_message(m.chat.id, "Invalid ID")

    wait = bot.send_message(m.chat.id, "🛰 <b>Searching {m.text} in Database...</b>")

    try:
        # API Call
        r = requests.get(API_URL + str(m.text), timeout=35).json()
        
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
        else:
            bot.edit_message_text("❌ <b>No Data Found!</b>", m.chat.id, wait.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ <b>API Error!</b>\nDetails: {str(e)}", m.chat.id, wait.message_id)

# ================= OTHER =================
@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def stats(m):
    cur.execute("SELECT balance, searches FROM users WHERE user_id=?", (m.from_user.id,))
    res = cur.fetchone()

    if not res:
        return bot.send_message(m.chat.id, "❌ Start first")

    bot.send_message(m.chat.id, f"💳<b>Your Credit:</b> {res[0]} | 🔍<a>Total Search:</a> {res[1]}")

@bot.message_handler(func=lambda m: m.text == "👥 Refer & Earn")
def refer(m):
    me = bot.get_me()
    link = f"<code>https://t.me/{me.username}?start={m.from_user.id}</code>"
    bot.send_message(m.chat.id, f"Invite link:\n{link}")

@bot.message_handler(func=lambda m: m.text == "⬅ Back")
def back(m):
    bot.send_message(m.chat.id, "Main Menu", reply_markup=main_menu(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🆘 Support")
def sup(m):
    bot.send_message(m.chat.id, "<b>Need any help contact:</b> @Unkonwn_BMT")

# ================= RUN =================
print("🔥 Bot Running...")
bot.infinity_polling()
