import telebot
import os
from telebot import types
import database
import functions
import scheduler

TOKEN = os.environ.get('TOKEN')
ALLOWED_ID = int(os.environ.get('ALLOWED_ID', 0))

bot = telebot.TeleBot(TOKEN)

# Jangan merespon user selain allowed_id
@bot.message_handler(func=lambda message: message.from_user.id != ALLOWED_ID)
def unauthorized():
    return

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id != ALLOWED_ID: return
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

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ALLOWED_ID: return
    user_id = message.from_user.id
    text = functions.get_stats_logic(user_id)
    bot.reply_to(message, text, parse_mode="Markdown")

# Tambahkan handler lainnya (rekap, delete, export) di sini...
@bot.message_handler(commands=['rekap'])
def rekap_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Hari Ini", callback_data='rekap_daily'),
        types.InlineKeyboardButton("Bulan Ini", callback_data='rekap_monthly'))
    bot.reply_to(message, "Pilih periode:", reply_markup=markup)

@bot.message_handler(commands=['export'])
def export_data(message):
    if message.from_user.id != ALLOWED_ID: return
    user_id = message.from_user.id
    data = functions.get_export_logic(user_id)

    if data is None:
        bot.reply_to(message, "📊 Tidak ada data untuk diekspor.")
        return
    
    text = f"📊 Ini data transaksimu dalam CSV:\n\n{data}"
    bot.reply_to(message, text)

@bot.message_handler(commands=['hapus'])
def hapus_command(message):
    user_id = message.from_user.id
    data = functions.get_last_transaction(user_id)
    if data is None:
        text = "❌ *Tidak ada data.*"
        bot.reply_to(message, text, parse_mode="Markdown")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🗑️ Hapus", callback_data='confirm_delete'),
        types.InlineKeyboardButton("❌ Batal", callback_data='cancel_delete'))
    bot.reply_to(message, data, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.message.chat.id
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
            if functions.save_transaction(data['amount'], category, data['desc'], user_id):
                bot.edit_message_text(
                    f"✅ *Tersimpan!*\n💰 Rp {data['amount']:,}\n📝 {data['desc']}\n🏷️ {category}",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown")
                del user_data[call.message.chat.id]
        else:
            bot.answer_callback_query(call.id, "Sesi habis, input ulang ya.")

    elif call.data == 'confirm_delete':
        deleted = functions.delete_last_transaction(user_id)
        if deleted:
            text = f"✅ *Entri terakhir dihapus!*"
        else:
            text = "❌ *Gagal menghapus entri terakhir.*"
        bot.edit_message_text(text,
                              call.message.chat.id,
                              call.message.message_id,
                              parse_mode="Markdown")

    elif call.data == 'cancel_delete':
        bot.edit_message_text(":leftwards_arrow_with_hook: Batal menghapus.", call.message.chat.id,
                              call.message.message_id,
                              parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.chat.id
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
                     "❓ Format salah, gunakan `NamaBarang Harga` (Contoh: Kopi 15k)",
                     parse_mode="Markdown")

if __name__ == "__main__":
    database.init_db()
    
    # Jalankan scheduler dengan mempassing objek 'bot'
    scheduler.start_scheduler_thread(bot, ALLOWED_ID)
    
    print("Bot LiteSpend is running...")
    bot.polling(none_stop=True)