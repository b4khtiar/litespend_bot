import telebot
import sqlite3
import re
import os
import schedule
import threading
import time
import csv

from telebot import types

# Mengambil variabel dari Environment (dari docker-compose.yaml)
TOKEN = os.environ.get('TOKEN')
# Gunakan int() karena ID Telegram adalah angka, berikan default 0 jika tidak ada
ALLOWED_ID = int(os.environ.get('ALLOWED_ID', 0))

bot = telebot.TeleBot(TOKEN)

# Memastikan tabel tersedia
def init_db():
    db_path = os.path.join(os.getcwd(), 'data', 'finance.db')
    conn = sqlite3.connect(db_path)
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

# Menyimpan ke database
def save_to_db(amount, category, desc):
    try:
        db_path = os.path.join(os.getcwd(), 'data', 'finance.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT INTO transactions (user_id, amount, category, description) VALUES (?, ?, ?, ?)",
                  (ALLOWED_ID, amount, category, desc))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        return False

# Fungsi untuk mengecek apakah sudah ada input hari ini
def check_and_remind():
    db_path = os.path.join(os.getcwd(), 'data', 'finance.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions WHERE date(date) = date('now')")
    count = c.fetchone()[0]
    conn.close()

    if count == 0:
        bot.send_message(ALLOWED_ID, "🔔 *Reminder Malam:* Kamu belum mencatat pengeluaran hari ini. Yuk, catat sekarang agar habit tetap terjaga! 📝", parse_mode="Markdown")

# Fungsi untuk menjalankan scheduler di background
def run_scheduler():
    # Atur waktu pengingat (misal jam 21:00)
    schedule.every().day.at("21:00").do(check_and_remind)
    while True:
        schedule.run_pending()
        time.sleep(60) # Cek setiap menit

# Jalankan scheduler dalam thread terpisah
reminder_thread = threading.Thread(target=run_scheduler, daemon=True)
reminder_thread.start()

user_data = {}

def generate_category_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    categories = ['🍴 Makan', '🚗 Transport', '🛍️ Jajan', '🏠 Rumah', '💊 Kesehatan', '✨ Lainnya']
    buttons = [types.InlineKeyboardButton(cat, callback_data=f"cat_{cat}") for cat in categories]
    markup.add(*buttons)
    return markup

# perintah mengambil rekap
def get_report(period='daily'):
    db_path = os.path.join(os.getcwd(), 'data', 'finance.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    if period == 'daily':
        query = "SELECT description, amount FROM transactions WHERE date(date, '+7 hours') = date('now', '+7 hours')"
        title = "📅 *REKAP HARIAN*"
        c.execute(query)
        rows = c.fetchall()
        report_text = f"{title}\n━━━━━━━━━━━━━━━\n"
        total = 0
        for desc, amount in rows:
            report_text += f"• {desc}: `Rp {amount:,.0f}`\n"
            total += amount
    else:
        # Query khusus untuk grouping per kategori
        query = """SELECT category, SUM(amount) as total 
                   FROM transactions 
                   WHERE strftime('%m-%Y', date, '+7 hours') = strftime('%m-%Y', 'now', '+7 hours')
                   GROUP BY category ORDER BY total DESC"""
        title = "📊 *REKAP BULANAN (PER KATEGORI)*"
        c.execute(query)
        rows = c.fetchall()
        report_text = f"{title}\n━━━━━━━━━━━━━━━\n"
        total = sum(item[1] for item in rows)
        
        for cat, amount in rows:
            porsi = (amount / total) * 100 if total > 0 else 0
            bar = "┃" + "█" * int(porsi/8) + "░" * (8 - int(porsi/8)) + "┃"
            report_text += f"*{cat}*\n`Rp {amount:>10,.0f}` {bar} {porsi:>3.0f}%\n"
    
    conn.close()
    if not rows: return f"{title}\n\nBelum ada data."
    
    report_text += f"━━━━━━━━━━━━━━━\n💰 *TOTAL: Rp {total:,.0f}*"
    return report_text

# menghapus data terakhir kalau typo misalnya
def delete_last_transaction():
    try:
        db_path = os.path.join(os.getcwd(), 'data', 'finance.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Cari transaksi terakhir
        c.execute("SELECT id, description, amount FROM transactions ORDER BY id DESC LIMIT 1")
        last_row = c.fetchone()

        if last_row:
            row_id, desc, amount = last_row
            c.execute("DELETE FROM transactions WHERE id = ?", (row_id,))
            conn.commit()
            conn.close()
            return f"🗑️ *Dihapus:* {desc} (Rp {amount:,.0f})"
        else:
            conn.close()
            return "❌ Tidak ada data yang bisa dihapus."
    except Exception as e:
        print(f"DELETE ERROR: {e}")
        return "❌ Gagal menghapus data."

# Keamanan: Cek ID
@bot.message_handler(func=lambda message: message.from_user.id != ALLOWED_ID)
def unauthorized(message):
    bot.reply_to(message, "❌ Akses ditolak. Ini bot pribadi.")

#Jalankan init_db sebelum polling
init_db()

# Fungsi start / selamat datang
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Mengambil nama depan user
    first_name = message.from_user.first_name
    
    # tombol Quick Start (Inline Keyboard)
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_rekap = types.InlineKeyboardButton("📊 Lihat Rekap", callback_data='rekap_daily')
    btn_hapus = types.InlineKeyboardButton("🗑️ Hapus Terakhir", callback_data='confirm_delete')
    markup.add(btn_rekap, btn_hapus)

    welcome_text = (
        f"👋 *Halo, {first_name}!*\n\n"
        "Saya *LiteSpend*, asisten minimalis yang siap membantu menjaga habit keuanganmu.\n\n"
        " langsung ketik untuk mencatat:\n"
        "👉 `Kopi 15k` atau `Bensin 20000`\n\n"
        "Setelah itu, pilih kategori yang sesuai. Gampang kan?\n\n"
        "📌 *Tips:* Gunakan menu di bawah untuk akses cepat."
    )
    
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode="Markdown", 
        reply_markup=markup
    )

# panggil fungsi rekap
@bot.message_handler(commands=['rekap'])
def rekap_command(message):
    markup = types.InlineKeyboardMarkup()
    item_daily = types.InlineKeyboardButton("Hari Ini", callback_data='rekap_daily')
    item_monthly = types.InlineKeyboardButton("Bulan Ini", callback_data='rekap_monthly')
    markup.add(item_daily, item_monthly)

    bot.reply_to(message, "Pilih periode rekap yang ingin kamu lihat:", reply_markup=markup)

# memanggil fungsi hapus
@bot.message_handler(commands=['hapus'])
def hapus_command(message):
    # Cek dulu transaksi terakhirnya apa
    db_path = os.path.join(os.getcwd(), 'data', 'finance.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT description, amount FROM transactions ORDER BY id DESC LIMIT 1")
    last = c.fetchone()
    conn.close()

    if last:
        markup = types.InlineKeyboardMarkup()
        btn_confirm = types.InlineKeyboardButton("Ya, Hapus!", callback_data='confirm_delete')
        btn_cancel = types.InlineKeyboardButton("Batal", callback_data='cancel_delete')
        markup.add(btn_confirm, btn_cancel)

        bot.reply_to(message, f"Yakin ingin menghapus transaksi terakhir?\n👉 *{last[0]} (Rp {last[1]:,.0f})*",
                     parse_mode="Markdown", reply_markup=markup)
    else:
        bot.reply_to(message, "Belum ada transaksi yang tercatat.")

# ekspor rekap        
@bot.message_handler(commands=['export'])
def export_csv(message):
    db_path = os.path.join(os.getcwd(), 'data', 'finance.db')
    file_path = 'data/data_keuangan.csv'
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT date, category, description, amount FROM transactions ORDER BY date DESC")
        rows = c.fetchall()
        conn.close()

        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Tanggal', 'Kategori', 'Keterangan', 'Nominal']) # Header

            # Membersihkan emoji dari kolom Kategori
            # Regex ini akan menghapus karakter non-ASCII (termasuk emoji)
            for row in rows:
                clean_category = re.sub(r'[^\x00-\x7F]+', '', row[1]).strip()
                
                # Masukkan data yang sudah bersih ke CSV
                writer.writerow([row[0], clean_category, row[2], row[3]])

        with open(file_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📂 Ini data keuangan kamu dalam format CSV.")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Gagal ekspor data: {e}")

# Handler input
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    if call.data.startswith('rekap_'):
        # Logika rekap yang tadi
        if call.data == 'rekap_daily':
            report = get_report('daily')
        else:
            report = get_report('monthly')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=report, parse_mode="Markdown")
        pass

    # --- LOGIKA PILIH KATEGORI (BARU) ---
    elif call.data.startswith('cat_'):
        category = call.data.replace("cat_", "")
        data = user_data.get(call.message.chat.id)

        if data:
            if save_to_db(data['amount'], category, data['desc']):
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"✅ *Tersimpan!*\n\n💰 Rp {data['amount']:,}\n📝 {data['desc']}\n🏷️ {category}",
                    parse_mode="Markdown"
                )
                # Hapus data sementara setelah tersimpan
                del user_data[call.message.chat.id]
            else:
                bot.edit_message_text(chat_id=call.message.chat.id,
                                      message_id=call.message.message_id,
                                      text="❌ Gagal menyimpan ke database.")
        else:
            bot.answer_callback_query(call.id, "Data sudah kadaluarsa, silakan input ulang.")

    elif call.data == 'confirm_delete':
        result = delete_last_transaction()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=result, parse_mode="Markdown")

    elif call.data == 'cancel_delete':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ Penghapusan dibatalkan.")

# Handler untuk memproses klik tombol
@bot.callback_query_handler(func=lambda call: call.data.startswith('rekap_'))
def callback_rekap(call):
    if call.data == 'rekap_daily':
        report = get_report('daily')
    elif call.data == 'rekap_monthly':
        report = get_report('monthly')

    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=report,
                          parse_mode="Markdown")

# Smart Parsing: Menangkap input teks (Contoh: "Bakso 20k" atau "Bensin 15000")
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text.lower()
    match = re.search(r'(\d+)\s*(k|rb)?', text)

    if match:
        nominal = int(match.group(1))
        if match.group(2) in ['k', 'rb']:
            nominal *= 1000

        deskripsi = text.replace(match.group(0), "").strip() or "Tanpa keterangan"

        # Simpan data sementara di memori (dict)
        user_data[message.chat.id] = {'amount': nominal, 'desc': deskripsi}

        bot.reply_to(message,
                     f"💰 *Rp {nominal:,}* untuk *{deskripsi}*\nPilih kategorinya:",
                     reply_markup=generate_category_markup(),
                     parse_mode="Markdown")
    else:
        bot.reply_to(message, "❓ Format salah. Coba: 'Kopi 15k'")

bot.polling()