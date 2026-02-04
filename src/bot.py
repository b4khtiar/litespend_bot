import telebot
import sqlite3
import re
import os
import threading
import csv
from telebot import types

# --- IMPORT FUNGSI DATABASE ---
from database import (
    init_db, save_to_db, get_report, get_last_transaction, delete_last_transaction, get_user_stats,
    get_all_transactions
)


# --- KONFIGURASI ---
TOKEN = os.environ.get('TOKEN')
ALLOWED_ID = int(os.environ.get('ALLOWED_ID', 0))
DB_PATH = os.path.join(os.getcwd(), 'data', 'finance.db')
bot = telebot.TeleBot(TOKEN)
user_data = {}


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
        rows = get_all_transactions()
        if not rows:
            bot.reply_to(message, "❌ Tidak ada data untuk diekspor.")
            return
            
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