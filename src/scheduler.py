import schedule
import time
from bot import check_and_remind

# SCHEDULER
def run_scheduler():
    # sesuaikan dengan gmt+7 (WIB)
    # 21:00 WIB = 14:00 UTC
    schedule.every().day.at("14:00").do(check_and_remind)
    while True:
        schedule.run_pending()
        time.sleep(60)

