import schedule
import time
import threading
from datetime import datetime
import calendar

STICKERS = {
    'REMINDER': 'CAACAgIAAxkBAAIBoWmFZLoZic6wMVQ3oN42uT160YUJAALbAAOYv4ANMp05Rfi6Kxo4BA',
    'INSIGHT_HAPPY': 'CAACAgIAAxkBAAIBqWmFZsbJbRDTxavcCXBKk9nyc-arAALQAAOYv4ANunjqE9NonHw4BA',
    'INSIGHT_SAD': 'CAACAgIAAxkBAAIBpWmFZQQcLtc2XHykzfXd7liwAvHeAALKAAOYv4ANOXmOnhOR5nQ4BA'
}

def run_scheduler(bot, allowed_id, functions): # Tambahkan parameter functions
    
    def is_last_day_of_month():
        today = datetime.now()
        # Mengambil hari terakhir dari bulan saat ini
        last_day = calendar.monthrange(today.year, today.month)[1]
        return today.day == last_day

    def job_remind():
        if functions.check_and_remind_logic(allowed_id):
            text = (
                "🔔 *Halo! Jangan sampai lupa...*\n\n"
                "Cukup 10 detik untuk mencatat pengeluaranmu hari ini. ⏱️\n"
                "Ketik saja: `Bensin 25rb`"
            )
            bot.send_sticker(allowed_id, STICKERS['REMINDER'])
            bot.send_message(allowed_id, text, parse_mode="Markdown")

    def job_weekly():
        # Karena dijalankan Senin pagi, kita ambil data minggu lalu
        text, emotion = functions.get_weekly_insight_logic(allowed_id, is_archive=True)
        insight_sticker_id = STICKERS['INSIGHT_HAPPY'] if emotion == 'happy' else STICKERS['INSIGHT_SAD']
        bot.send_sticker(allowed_id, insight_sticker_id)
        bot.send_message(allowed_id, text, parse_mode="Markdown")

    def job_monthly_check():
        # Fungsi ini dipanggil setiap hari pukul 20:00 WIB
        # Tapi hanya eksekusi insight jika hari ini hari terakhir
        if is_last_day_of_month():
            text, emotion = functions.get_monthly_insight_logic(allowed_id, is_archive=True)
            insight_sticker_id = STICKERS['INSIGHT_HAPPY'] if emotion == 'happy' else STICKERS['INSIGHT_SAD']
            bot.send_sticker(allowed_id, insight_sticker_id)
            bot.send_message(allowed_id, text, parse_mode="Markdown")

    # --- PENJADWALAN (WIB to UTC) ---
    
    # 1. Harian: Jam 21:00 WIB (14:00 UTC)
    schedule.every().day.at("14:00").do(job_remind)

    # 2. Mingguan: Senin Jam 10:00 WIB (03:00 UTC)
    schedule.every().monday.at("03:00").do(job_weekly)

    # 3. Bulanan: Cek setiap hari jam 20:00 WIB (13:00 UTC)
    schedule.every().day.at("13:00").do(job_monthly_check)

    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler_thread(bot, allowed_id, functions):
    t = threading.Thread(target=run_scheduler, args=(bot, allowed_id, functions), daemon=True)
    t.start()