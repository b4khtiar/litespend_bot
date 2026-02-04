from database import get_db_connection
import random
from datetime import datetime

MOTIVASI_BANK = [
    "Hemat hari ini, tenang di masa depan. 💰",
    "Disiplin keuangan adalah bentuk kebebasan. 🔥",
    "Catatan kecil hari ini adalah rencana besar untuk esok. 📝",
    "Keep it up! Konsistensi adalah kunci. 🚀",
    "Bukan tentang seberapa banyak yang dihasilkan, tapi seberapa banyak yang disimpan. ✨",
    "Catatan kecil hari ini adalah rencana besar untuk esok. 📝",
    "Uangmu adalah hasil kerja kerasmu, hargai dengan mencatatnya. 💪",
    "Satu entri hari ini, satu langkah menuju financial freedom. 🏁",
    "Habit yang baik lebih berharga daripada saldo yang besar. 🌟"
]

def save_transaction(amount, category, description, user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO transactions (amount, category, description, user_id) VALUES (?, ?, ?, ?)",
              (amount, category, description, user_id))
    conn.commit()
    conn.close()
    return True

def get_last_transaction(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    data = c.fetchone()
    conn.close()
    return data

def delete_last_transaction(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    conn.commit()
    conn.close()
    return True

def check_remind_needed(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    # Gunakan +7 hours jika server UTC tapi ingin hitung hari WIB
    c.execute("SELECT COUNT(*) FROM transactions WHERE date(date, '+7 hours') = date('now', '+7 hours') AND user_id=?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count == 0

def get_weekly_insight_logic(user_id):
    # Ambil penanda minggu ini (Contoh: '2023-42' untuk tahun 2023 minggu ke-42)
    current_period = datetime.now().strftime('%Y-%U')
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Cek apakah sudah ada di database
    c.execute("SELECT insight_text FROM insights WHERE period_type='weekly' AND period_date=? AND user_id=?", (current_period, user_id))
    existing = c.fetchone()
    
    if existing:
        conn.close()
        return existing[0] + "\n\n_(Diambil dari arsip)_"

    # 2. Jika tidak ada, jalankan kalkulasi berat seperti sebelumnya
    c.execute("SELECT SUM(amount) FROM transactions WHERE date >= date('now', '-7 days') AND user_id=?", (user_id,))
    this_week_total = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE date >= date('now', '-14 days') AND date < date('now', '-7 days') AND user_id=?", (user_id,))
    last_week_total = c.fetchone()[0] or 0

    diff = this_week_total - last_week_total
    diff_percent = diff / last_week_total * 100 if last_week_total > 0 else 0
    status = "naik 🔴" if diff > 0 else "turun 🟢"
    
    insight_text = (f"💡 *INSIGHT MINGGUAN*\n"
                        f"Pengeluaranmu {status} {diff_percent:.1f}% dibanding pekan lalu.\n"
                        f"Total seminggu ini: `Rp {this_week_total:,.0f}`")

    # 3. Simpan hasil kalkulasi ke tabel insights agar minggu depan tidak hitung lagi
    c.execute("""INSERT INTO insights (user_id, period_type, period_date, total_amount, trend_percent, insight_text) 
                 VALUES (?, ?, ?, ?, ?, ?)""", 
              (user_id, 'weekly', current_period, this_week_total, diff_percent, insight_text))
    
    conn.commit()
    conn.close()
    
    return insight_text

def get_stats_logic(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*), MIN(datetime(date, '+7 hours')) FROM transactions WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    
    motivasi = random.choice(MOTIVASI_BANK)
    return f"📈 *STATISTIK*\nTotal Input: `{res[0]}`\nMencatat sejak: `{res[1]}`\n\n_{motivasi}_"

def get_export_logic(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return None
    
    # Buat CSV
    import csv
    from io import StringIO
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Tanggal", "Kategori", "Deskripsi", "Jumlah", "User ID"])
    writer.writerows(rows)
    return output.getvalue()