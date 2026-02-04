import schedule
import time
from database import check_and_remind

# SCHEDULER
def run_scheduler():
    schedule.every().day.at("21:00").do(check_and_remind)
    while True:
        schedule.run_pending()
        time.sleep(60)

