import telebot
import sqlite3
import re
import os
import schedule
import threading
import time
import csv
import random
from telebot import types

# Konfigurasi
TOKEN = os.environ.get('TOKEN')
ALLOWED_ID = int(os.environ.get('ALLOWED_ID', 0))
DB_PATH = os.path.join(os.getcwd(), 'data', 'finance.db')
MOTIVASI_BANK = [
    "Keep it up! Konsistensi adalah kunci. 🚀",
    "Hemat hari ini, tenang di masa depan. 💰",
    "Bukan tentang seberapa banyak yang dihasilkan, tapi seberapa banyak yang disimpan. ✨",
    "Disiplin keuangan adalah bentuk kebebasan. 🔥",
    "Catatan kecil hari ini adalah rencana besar untuk esok. 📝",
    "Uangmu adalah hasil kerja kerasmu, hargai dengan mencatatnya. 💪",
    "Satu entri hari ini, satu langkah menuju financial freedom. 🏁",
    "Habit yang baik lebih berharga daripada saldo yang besar. 🌟"
]

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
        c.execute(
            "INSERT INTO transactions (user_id, amount, category, description) VALUES (?, ?, ?, ?)",
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
            bar = "┃" + "█" * int(
                porsi / 10) + "░" * (10 - int(porsi / 10)) + "┃"
            report_text += f"*{cat}*\n`Rp {amount:>10,.0f}` {bar} {porsi:>3.0f}%\n"

    conn.close()
    if not rows: return f"{title}\n\nBelum ada data."
    report_text += f"━━━━━━━━━━━━━━━\n💰 *TOTAL: Rp {total:,.0f}*"
    return report_text


def get_last_transaction():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT id, description, amount FROM transactions ORDER BY id DESC LIMIT 1"
        )
        last_row = c.fetchone()
        if last_row:
            row_id, desc, amount = last_row
            conn.close()
            return f"🔍 Entri terakhir: {desc} (Rp {amount:,.0f})"
        conn.close()
        return "0"
    except Exception as e:
        return f"❌ Error: {e}"


def delete_last_transaction():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT id, description, amount FROM transactions ORDER BY id DESC LIMIT 1"
        )
        last_row = c.fetchone()
        if last_row:
            row_id, desc, amount = last_row
            c.execute("DELETE FROM transactions WHERE id = ?", (row_id, ))
            conn.commit()
            conn.close()
            return f"🗑️ *Entri dihapus:* {desc} (Rp {amount:,.0f})"
        conn.close()
        return "❌ Tidak ada data."
    except Exception as e:
        return f"❌ Error: {e}"


def get_user_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Ambil data dari database
    c.execute(
        "SELECT COUNT(*), MIN(datetime(date, '+7 hours')) FROM transactions")
    total_entries, start_date = c.fetchone()

    c.execute(
        "SELECT category, COUNT(category) as count FROM transactions GROUP BY category ORDER BY count DESC LIMIT 1"
    )
    most_freq = c.fetchone()

    c.execute("SELECT COUNT(DISTINCT date(date)) FROM transactions")
    active_days = c.fetchone()[0]
    conn.close()

    if not total_entries:
        return "Belum ada statistik. Yuk, mulai mencatat!"

    # Bersihkan tampilan tanggal
    start_date_clean = start_date.split()[0] if start_date else "-"
    freq_text = f"{most_freq[0]} ({most_freq[1]}x)" if most_freq else "-"

    # Ambil motivasi random
    pesan_motivasi = random.choice(MOTIVASI_BANK)

    stats_text = ("📈 *STATISTIK PENGGUNAAN*\n"
                  "━━━━━━━━━━━━━━━\n"
                  f"🗓️ *Mulai Sejak:* `{start_date_clean}`\n"
                  f"📝 *Total Entri:* `{total_entries} kali`\n"
                  f"🔥 *Hari Aktif:* `{active_days} hari`\n"
                  f"🏷️ *Kategori Favorit:* `{freq_text}`\n"
                  "━━━━━━━━━━━━━━━\n"
                  f"_{pesan_motivasi}_")
    return stats_text


# --- SCHEDULER ---


def check_and_remind():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM transactions WHERE date(date, '+7 hours') = date('now', '+7 hours')"
    )
    count = c.fetchone()[0]
    conn.close()
    if count == 0:
        bot.send_message(
            ALLOWED_ID,
            "🔔 *Reminder:* Kamu belum mencatat pengeluaran hari ini!",
            parse_mode="Markdown")


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
    first_name = message.from_user.first_name
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_rekap = types.InlineKeyboardButton("📊 Lihat Rekap",
                                           callback_data='rekap_daily')
    btn_stats = types.InlineKeyboardButton("📈 Cek Stats",
                                           callback_data='stats')
    markup.add(btn_rekap, btn_stats)

    welcome_text = (
        f"👋 *Halo, {first_name}!*\n\n"
        "Saya *LiteSpend*, asisten yang siap membantu menjaga habit keuanganmu.\n\n"
        " langsung ketik untuk mencatat:\n"
        "👉 `Kopi 15k` atau `Bensin 20000`\n\n"
        "Setelah itu, pilih kategori yang sesuai. Gampang kan?\n\n"
        "📌 *Tips:* Gunakan menu di bawah untuk akses cepat.")

    bot.send_message(message.chat.id,
                     welcome_text,
                     parse_mode="Markdown",
                     reply_markup=markup)


@bot.message_handler(commands=['hapus'])
def hapus_command(message):
    data = get_last_transaction()
    if data == "0":
        text = "❌ *Tidak ada data.*"
        bot.reply_to(message, text, parse_mode="Markdown")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🗑️ Hapus", callback_data='confirm_delete'),
        types.InlineKeyboardButton("❌ Batal", callback_data='cancel_delete'))
    bot.reply_to(message, data, reply_markup=markup)


@bot.message_handler(commands=['rekap'])
def rekap_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Hari Ini", callback_data='rekap_daily'),
        types.InlineKeyboardButton("Bulan Ini", callback_data='rekap_monthly'))
    bot.reply_to(message, "Pilih periode:", reply_markup=markup)


@bot.message_handler(commands=['stats'])
def stats_command(message):
    bot.reply_to(message, get_user_stats(), parse_mode="Markdown")


@bot.message_handler(commands=['export'])
def export_csv(message):
    file_path = 'data/export_keuangan.csv'
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        query = """
            SELECT datetime(date, '+7 hours'), category, description, amount 
            FROM transactions 
            ORDER BY date DESC
        """
        c.execute(query)
        rows = c.fetchall()
        conn.close()
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Tanggal', 'Kategori', 'Keterangan', 'Nominal'])
            for row in rows:
                clean_cat = re.sub(r'[^\x00-\x7F]+', '', row[1]).strip()
                clean_cat = " ".join(clean_cat.split()).strip()
                writer.writerow([row[0], clean_cat, row[2], row[3]])
        with open(file_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📂 Data Ekspor CSV")
    except Exception as e:
        bot.reply_to(message, f"❌ Gagal: {e}")


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data.startswith('rekap_'):
        period = call.data.replace('rekap_', '')
        bot.edit_message_text(get_report(period),
                              call.message.chat.id,
                              call.message.message_id,
                              parse_mode="Markdown")

    elif call.data.startswith('cat_'):
        category = call.data.replace("cat_", "")
        data = user_data.get(call.message.chat.id)
        if data:
            if save_to_db(data['amount'], category, data['desc']):
                bot.edit_message_text(
                    f"✅ *Tersimpan!*\n💰 Rp {data['amount']:,}\n📝 {data['desc']}\n🏷️ {category}",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown")
                del user_data[call.message.chat.id]
        else:
            bot.answer_callback_query(call.id, "Sesi habis, input ulang ya.")

    elif call.data == 'confirm_delete':
        bot.edit_message_text(delete_last_transaction(),
                              call.message.chat.id,
                              call.message.message_id,
                              parse_mode="Markdown")

    elif call.data == 'cancel_delete':
        bot.edit_message_text("✅ Dibatalkan.", call.message.chat.id,
                              call.message.message_id)


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    match = re.search(r'(\d+)\s*(k|rb)?', message.text.lower())
    if match:
        nominal = int(match.group(1)) * (1000 if match.group(2) else 1)
        deskripsi = re.sub(r'\d+\s*(k|rb)?', '',
                           message.text.lower()).strip() or "Tanpa keterangan"
        user_data[message.chat.id] = {'amount': nominal, 'desc': deskripsi}

        markup = types.InlineKeyboardMarkup(row_width=2)
        cats = [
            '🍴 Makan', '🚗 Transport', '🛍️ Jajan', '🏠 Rumah', '💊 Kesehatan',
            '📚 Edukasi', '✨ Lainnya'
        ]
        markup.add(*[
            types.InlineKeyboardButton(c, callback_data=f"cat_{c}")
            for c in cats
        ])
        bot.reply_to(message,
                     f"💰 *Rp {nominal:,}* - {deskripsi}\nPilih kategori:",
                     reply_markup=markup,
                     parse_mode="Markdown")
    else:
        bot.reply_to(message,
                     "❓ Format: `NamaBarang Harga` (Contoh: Kopi 15k)")


if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_scheduler, daemon=True).start()
    bot.polling(none_stop=True)