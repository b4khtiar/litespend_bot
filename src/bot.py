import telebot
import sqlite3
import re
import os
import schedule
import threading
import time
import csv
from telebot import types

# Konfigurasi
TOKEN = os.environ.get('TOKEN')
ALLOWED_ID = int(os.environ.get('ALLOWED_ID', 0))
DB_PATH = os.path.join(os.getcwd(), 'data', 'finance.db')

bot = telebot.TeleBot(TOKEN)
user_data = {}

# --- FUNGSI DATABASE ---

def init_db():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  amount REAL,
                  category TEXT,
                  description TEXT,
                  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def save_to_db(amount, category, desc):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO transactions (user_id, amount, category, description) VALUES (?, ?, ?, ?)",
                  (ALLOWED_ID, amount, category, desc))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        return False

def get_report(period='daily'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if period == 'daily':
        query = "SELECT description, amount FROM transactions WHERE date(date, '+7 hours') = date('now', '+7 hours')"
        title = "📅 *REKAP HARIAN*"
        c.execute(query)
        rows = c.fetchall()
        report_text = f"{title}\n━━━━━━━━━━━━━━━\n"
        total = sum(item[1] for item in rows)
        for desc, amount in rows:
            report_text += f"• {desc}: `Rp {amount:,.0f}`\n"
    else:
        query = """SELECT category, SUM(amount) as total 
                   FROM transactions 
                   WHERE strftime('%m-%Y', date, '+7 hours') = strftime('%m-%Y', 'now', '+7 hours')
                   GROUP BY category ORDER BY total DESC"""
        title = "📊 *REKAP BULANAN*"
        c.execute(query)
        rows = c.fetchall()
        report_text = f"{title}\n━━━━━━━━━━━━━━━\n"
        total = sum(item[1] for item in rows)
        
        for cat, amount in rows:
            porsi = (amount / total) * 100 if total > 0 else 0
            bar = "┃" + "█" * int(porsi/10) + "░" * (10 - int(porsi/10)) + "┃"
            report_text += f"*{cat}*\n`Rp {amount:>10,.0f}` {bar} {porsi:>3.0f}%\n"
    
    conn.close()
    if not rows: return f"{title}\n\nBelum ada data."
    report_text += f"━━━━━━━━━━━━━━━\n💰 *TOTAL: Rp {total:,.0f}*"
    return report_text

def delete_last_transaction():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, description, amount FROM transactions ORDER BY id DESC LIMIT 1")
        last_row = c.fetchone()
        if last_row:
            row_id, desc, amount = last_row
            c.execute("DELETE FROM transactions WHERE id = ?", (row_id,))
            conn.commit()
            conn.close()
            return f"🗑️ *Entri dihapus:* {desc} (Rp {amount:,.0f})"
        conn.close()
        return "❌ Tidak ada data."
    except Exception as e:
        return f"❌ Error: {e}"

# --- SCHEDULER ---

def check_and_remind():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions WHERE date(date, '+7 hours') = date('now', '+7 hours')")
    count = c.fetchone()[0]
    conn.close()
    if count == 0:
        bot.send_message(ALLOWED_ID, "🔔 *Reminder:* Kamu belum mencatat pengeluaran hari ini!", parse_mode="Markdown")

def run_scheduler():
    schedule.every().day.at("21:00").do(check_and_remind)
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- BOT HANDLERS ---

@bot.message_handler(func=lambda message: message.from_user.id != ALLOWED_ID)
def unauthorized(message):
    bot.reply_to(message, "❌ Akses ditolak.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("📊 Rekap", callback_data='rekap_daily'),
               types.InlineKeyboardButton("🗑️ Hapus", callback_data='confirm_delete'))
    bot.send_message(message.chat.id, f"👋 Halo *{message.from_user.first_name}*!\nKetik `Barang Harga` untuk mencatat.", 
                     parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['rekap'])
def rekap_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Hari Ini", callback_data='rekap_daily'),
               types.InlineKeyboardButton("Bulan Ini", callback_data='rekap_monthly'))
    bot.reply_to(message, "Pilih periode:", reply_markup=markup)

@bot.message_handler(commands=['export'])
def export_csv(message):
    file_path = 'data/export_keuangan.csv'
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT date, category, description, amount FROM transactions ORDER BY date DESC")
        rows = c.fetchall()
        conn.close()
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Tanggal', 'Kategori', 'Keterangan', 'Nominal'])
            for row in rows:
                clean_cat = re.sub(r'[^\x00-\x7F]+', '', row[1]).strip()
                writer.writerow([row[0], clean_cat, row[2], row[3]])
        with open(file_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📂 Data Ekspor CSV")
    except Exception as e:
        bot.reply_to(message, f"❌ Gagal: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data.startswith('rekap_'):
        period = call.data.replace('rekap_', '')
        bot.edit_message_text(get_report(period), call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    elif call.data.startswith('cat_'):
        category = call.data.replace("cat_", "")
        data = user_data.get(call.message.chat.id)
        if data:
            if save_to_db(data['amount'], category, data['desc']):
                bot.edit_message_text(f"✅ *Tersimpan!*\n💰 Rp {data['amount']:,}\n📝 {data['desc']}\n🏷️ {category}",
                                      call.message.chat.id, call.message.message_id, parse_mode="Markdown")
                del user_data[call.message.chat.id]
        else:
            bot.answer_callback_query(call.id, "Sesi habis, input ulang ya.")

    elif call.data == 'confirm_delete':
        bot.edit_message_text(delete_last_transaction(), call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    elif call.data == 'cancel_delete':
        bot.edit_message_text("✅ Dibatalkan.", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    match = re.search(r'(\d+)\s*(k|rb)?', message.text.lower())
    if match:
        nominal = int(match.group(1)) * (1000 if match.group(2) else 1)
        deskripsi = re.sub(r'\d+\s*(k|rb)?', '', message.text.lower()).strip() or "Tanpa keterangan"
        user_data[message.chat.id] = {'amount': nominal, 'desc': deskripsi}
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        cats = ['🍴 Makan', '🚗 Transport', '🛍️ Jajan', '🏠 Rumah', '💊 Kesehatan', '📚 Edukasi', '✨ Lainnya']
        markup.add(*[types.InlineKeyboardButton(c, callback_data=f"cat_{c}") for c in cats])
        bot.reply_to(message, f"💰 *Rp {nominal:,}* - {deskripsi}\nPilih kategori:", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❓ Format: `NamaBarang Harga` (Contoh: Kopi 15k)")

if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_scheduler, daemon=True).start()
    bot.polling(none_stop=True)