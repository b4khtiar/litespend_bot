import os
import sqlite3
import random

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

def get_all_transactions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions")
    rows = c.fetchall()
    conn.close()
    return rows

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

