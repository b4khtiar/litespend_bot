import schedule
import time
import threading
from functions import check_and_remind_logic, get_weekly_insight_logic

def run_scheduler(bot, allowed_id):
    def job_remind():
        # Cek data di functions.py, jika perlu kirim pesan via bot
        if check_and_remind_logic(allowed_id):
            bot.send_message(allowed_id, "🔔 *Reminder:* Belum ada catatan hari ini!", parse_mode="Markdown")

    def job_insight():
        insight_text = get_weekly_insight_logic(allowed_id)
        bot.send_message(allowed_id, insight_text, parse_mode="Markdown")

    # Jadwal (Waktu UTC jika server menggunakan UTC)
    schedule.every().monday.at("03:00").do(job_insight) # 10:00 WIB
    schedule.every().day.at("14:00").do(job_remind)     # 21:00 WIB

    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler_thread(bot, allowed_id):
    t = threading.Thread(target=run_scheduler, args=(bot, allowed_id), daemon=True)
    t.start()

