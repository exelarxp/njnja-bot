import sqlite3
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== الإعدادات ====================
BOT_TOKEN = "8678848659:AAEW8cJAoobHHaV9eXiacrKYZsGJk6EsQYM"
ADMIN_ID = 6419462811

# المسار الثابت لقاعدة البيانات
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ninja_store.db')

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== قاعدة البيانات ====================
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        name TEXT,
        username TEXT,
        balance REAL DEFAULT 0,
        access INTEGER DEFAULT 0,
        bought_count INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        duration TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        code TEXT,
        is_sold BOOLEAN DEFAULT FALSE,
        sold_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        code_id INTEGER,
        price REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        products = [
            ('Ninja 1Day', 1, '1 Day'),
            ('Ninja 3Day', 2, '3 Days'),
            ('Ninja 7Day', 4, '7 Days'),
            ('Ninja 15Day', 6, '15 Days'),
            ('Ninja 30Day', 8, '30 Days'),
        ]
        c.executemany("INSERT INTO products (name, price, duration) VALUES (?, ?, ?)", products)
    
    conn.commit()
    conn.close()
    logger.info("✅ Database ready!")

# ==================== دوال مساعدة ====================
def get_user(telegram_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(telegram_id, name, username):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO users (telegram_id, name, username) VALUES (?, ?, ?)",
              (telegram_id, name, username))
    conn.commit()
    conn.close()

def set_admin(telegram_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE users SET access = 777 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()

def remove_admin(telegram_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE users SET access = 0 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()

def ban_user(telegram_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()

def unban_user(telegram_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 0 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()

def get_products():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM products ORDER BY price")
    products = c.fetchall()
    conn.close()
    return products

def get_product(product_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()
    return product

def get_available_codes(product_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM codes WHERE product_id = ? AND is_sold = FALSE", (product_id,))
    codes = c.fetchall()
    conn.close()
    return codes

def update_balance_add(telegram_id, amount):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, telegram_id))
    conn.commit()
    conn.close()

def update_balance_remove(telegram_id, amount):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (amount, telegram_id))
    conn.commit()
    conn.close()

def get_access_name(access):
    if access == 777:
        return 'Developer'
    elif access == 1:
        return 'Admin'
    return 'User'

def is_admin(telegram_id):
    if telegram_id == ADMIN_ID:
        return True
    user = get_user(telegram_id)
    if user and user[6] >= 1:
        return True
    return False

def is_banned(telegram_id):
    user = get_user(telegram_id)
    return user and user[7] == 1

def format_code(code):
    return code.replace(' Password: ', '\nPassword: ')

# ==================== أوامر البوت ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        create_user(user_id, update.effective_user.first_name, update.effective_user.username or "No username")
        user = get_user(user_id)
    
    if user_id == ADMIN_ID:
        set_admin(ADMIN_ID)
        user = get_user(user_id)
    
    if is_banned(user_id):
        await update.message.reply_text("⛔️ You are banned from using this bot!")
        return
    
    await show_menu(update, context)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    access_name = get_access_name(user[6])
    
    keyboard = [
        [InlineKeyboardButton("🛒 View Plans", callback_data='plans')],
        [InlineKeyboardButton("📋 My Orders", callback_data='orders')],
        [InlineKeyboardButton("👤 Profile", callback_data='profile')],
    ]
    
    if is_admin(update.effective_user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data='admin')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"🥷 Ninja Store\n\n👤 {user[2]} ({access_name})\n💰 Balance: ${user[5]}"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# ==================== معالجة الأزرار ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'plans':
        products = get_products()
        keyboard = []
        for p in products:
            stock = len(get_available_codes(p[0]))
            keyboard.append([InlineKeyboardButton(f"🥷 {p[1]} - ${p[2]} ({stock} available)", callback_data=f'buy_{p[0]}')])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='menu')])
        await query.edit_message_text("🛒 Available Plans:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'orders':
        user = get_user(update.effective_user.id)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT o.price, p.name, c.code FROM orders o JOIN products p ON o.product_id=p.id JOIN codes c ON o.code_id=c.id WHERE o.user_id=?", (user[0],))
        orders = c.fetchall()
        conn.close()
        text = "📋 Your Orders:\n\n" if orders else "📋 No orders yet!"
        for o in orders:
            text += f"• {o[1]} - ${o[0]}\n{format_code(o[2])}\n\n"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='menu')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'profile':
        user = get_user(update.effective_user.id)
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='menu')]]
        await query.edit_message_text(
            f"👤 Profile\n\nName: {user[2]}\nUsername: @{user[3]}\nBalance: ${user[5]}\nBought: {user[7]} items",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == 'admin':
        if not is_admin(update.effective_user.id):
            return
        keyboard = [
            [InlineKeyboardButton("📥 Add Codes", callback_data='addcodes')],
            [InlineKeyboardButton("📊 Stock", callback_data='stock')],
            [InlineKeyboardButton("👥 Users", callback_data='users')],
            [InlineKeyboardButton("🔙 Back", callback_data='menu')],
        ]
        await query.edit_message_text("⚙️ Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'menu':
        await show_menu(update, context)
    
    elif data == 'addcodes':
        products = get_products()
        keyboard = []
        for p in products:
            keyboard.append([InlineKeyboardButton(f"🥷 {p[1]} - ${p[2]}", callback_data=f'ac_{p[0]}')])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='admin')])
        await query.edit_message_text("📦 Select Plan to Add Codes:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'stock':
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT p.id, p.name, COUNT(CASE WHEN c.is_sold=0 THEN 1 END), COUNT(CASE WHEN c.is_sold=1 THEN 1 END) FROM products p LEFT JOIN codes c ON p.id=c.product_id GROUP BY p.id")
        stock = c.fetchall()
        conn.close()
        text = "📊 Stock Report:\n\n"
        for s in stock:
            text += f"ID {s[0]}: {s[1]} - ✅{s[2]} ❌{s[3]}\n"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='admin')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'users':
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        conn.close()
        keyboard = []
        for u in users:
            banned = "⛔️" if u[7] else ""
            keyboard.append([InlineKeyboardButton(f"{banned}{u[2]} (ID:{u[1]}) - ${u[5]}", callback_data=f'u_{u[1]}')])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='admin')])
        await query.edit_message_text(f"👥 Users ({len(users)}):", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith('ac_'):
        product_id = int(data.replace('ac_', ''))
        context.user_data['add_product'] = product_id
        await query.edit_message_text("📦 Send codes in this format:\n\nUsername: xxx\nPassword: yyy\nUsername: aaa\nPassword: bbb")
    
    elif data.startswith('u_'):
        user_id = int(data.replace('u_', ''))
        user = get_user(user_id)
        if not user:
            await query.answer("User not found!", show_alert=True)
            return
        access_name = get_access_name(user[6])
        banned = "Yes" if user[7] else "No"
        keyboard = [
            [InlineKeyboardButton("💰 Give Balance", callback_data=f'give_{user_id}')],
            [InlineKeyboardButton("💸 Remove Balance", callback_data=f'remove_{user_id}')],
            [InlineKeyboardButton("⛔️ Ban" if user[7] == 0 else "✅ Unban", callback_data=f'ban_{user_id}')],
            [InlineKeyboardButton("👑 Set Admin" if user[6] < 777 else "👤 Remove Admin", callback_data=f'sa_{user_id}')],
            [InlineKeyboardButton("🔙 Back", callback_data='users')],
        ]
        await query.edit_message_text(
            f"👤 {user[2]}\nID: {user[1]}\nBalance: ${user[5]}\nAccess: {access_name}\nBanned: {banned}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith('give_'):
        user_id = int(data.replace('give_', ''))
        context.user_data['action'] = 'give'
        context.user_data['target'] = user_id
        await query.edit_message_text(f"💰 Enter amount to give to user {user_id}:")
    
    elif data.startswith('remove_'):
        user_id = int(data.replace('remove_', ''))
        context.user_data['action'] = 'remove'
        context.user_data['target'] = user_id
        await query.edit_message_text(f"💸 Enter amount to remove from user {user_id}:")
    
    elif data.startswith('ban_'):
        user_id = int(data.replace('ban_', ''))
        user = get_user(user_id)
        if user[7] == 1:
            unban_user(user_id)
            await query.answer("✅ User unbanned!", show_alert=True)
        else:
            ban_user(user_id)
            await query.answer("✅ User banned!", show_alert=True)
    
    elif data.startswith('sa_'):
        user_id = int(data.replace('sa_', ''))
        user = get_user(user_id)
        if user[6] < 777:
            set_admin(user_id)
            await query.answer("✅ User is now admin!", show_alert=True)
        else:
            remove_admin(user_id)
            await query.answer("✅ Admin removed!", show_alert=True)
    
    elif data.startswith('buy_'):
        product_id = int(data.replace('buy_', ''))
        user = get_user(update.effective_user.id)
        codes = get_available_codes(product_id)
        if not codes:
            await query.answer("❌ Out of stock!", show_alert=True)
            return
        product = get_product(product_id)
        if user[5] < product[2]:
            await query.answer(f"❌ Need ${product[2]}!", show_alert=True)
            return
        
        code = codes[0]
        new_balance = user[5] - product[2]
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE codes SET is_sold=1, sold_at=? WHERE id=?", (datetime.now(), code[0]))
        c.execute("INSERT INTO orders (user_id, product_id, code_id, price) VALUES (?,?,?,?)", (user[0], product_id, code[0], product[2]))
        c.execute("UPDATE users SET balance=?, bought_count=bought_count+1 WHERE id=?", (new_balance, user[0]))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(f"🎉 Purchase Successful!\n\n{format_code(code[2])}")

# ==================== معالجة الرسائل ====================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if 'add_product' in context.user_data:
        product_id = context.user_data['add_product']
        del context.user_data['add_product']
        lines = text.split('\n')
        codes = []
        current = []
        for line in lines:
            line = line.strip()
            if line.startswith('Username:'):
                if current:
                    codes.append(' '.join(current))
                current = [line]
            elif line.startswith('Password:'):
                current.append(line)
        if current:
            codes.append(' '.join(current))
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        for code in codes:
            c.execute("INSERT INTO codes (product_id, code, is_sold) VALUES (?,?,0)", (product_id, code))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Added {len(codes)} codes!")
        return
    
    if 'action' in context.user_data:
        action = context.user_data['action']
        target = context.user_data['target']
        del context.user_data['action']
        del context.user_data['target']
        
        try:
            amount = float(text)
            if action == 'give':
                update_balance_add(target, amount)
                await update.message.reply_text(f"✅ Gave ${amount} to user {target}!")
            else:
                update_balance_remove(target, amount)
                await update.message.reply_text(f"✅ Removed ${amount} from user {target}!")
        except:
            await update.message.reply_text("❌ Invalid amount!")

# ==================== الرئيسية ====================
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🤖 Bot started!")
    app.run_polling()

if __name__ == '__main__':
    main()