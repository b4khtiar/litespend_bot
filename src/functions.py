from database import get_db_connection
import random
from datetime import datetime
import io
import re
import csv

MOTIVASI_BANK = [
    "Uangmu adalah hasil kerja kerasmu, hargai dengan mencatatnya. 💪",
    "Tiap catatan kecil adalah langkah besar menuju kebebasan finansialmu! 🚀",
    "Mengetahui ke mana uangmu pergi adalah bentuk kasih sayang pada diri sendiri. ❤️",
    "Kamu yang pegang kendali! Mencatat hari ini berarti menang besok. 🏆",
    "Small steps, big impact. Terima kasih sudah disiplin hari ini! 🌟",
    "Mencatat bukan soal membatasi, tapi soal memberi ruang untuk hal yang berarti. 🌈",
    "Keuangan yang sehat dimulai dari kejujuran pada diri sendiri. Keep it up! 📈",
    "Kamu baru saja menyelamatkan masa depanmu dengan satu catatan ini. 🛡️",
    "Fokus pada progres, bukan kesempurnaan. Kamu luar biasa hari ini! ✨",
    "Uang adalah alat, dan kamu adalah masternya. Lanjutkan kebiasaan baik ini! 👑",
    "Pikiran jadi lebih tenang, tidur pun jadi lebih nyenyak. 🌙",
    "Disiplin finansial hari ini adalah tiket liburanmu di masa depan. ✈️",
    "Satu input satu langkah menjauh dari rasa cemas. You got this! 💪",
    "Mengelola uang adalah cara terbaik untuk menghargai kerja kerasmu. 💎",
    "Tidak ada pengeluaran yang terlalu kecil untuk dicatat. Teliti itu keren! 😎",
    "Masa depan yang lebih kaya sedang tersenyum padamu. 💰",
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

def get_transactions_today(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT description, amount FROM transactions WHERE date(date, '+7 hours') = date('now', '+7 hours') AND user_id=?",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

def delete_last_transaction(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    conn.commit()
    conn.close()
    return True

def check_and_remind_logic(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    # Gunakan +7 hours jika server UTC tapi ingin hitung hari WIB
    c.execute("SELECT COUNT(*) FROM transactions WHERE date(date, '+7 hours') = date('now', '+7 hours') AND user_id=?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    # if no result, return True
    if count == 0:
        return True
    return False

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
    status = "Stabil"
    suggestion = "Pengeluaranmu minggu ini stabil banget! ⚖️ Ini tanda kamu sudah punya kontrol yang matang atas gaya hidupmu. Predictable is good! 👏"
    if diff > 0:
        status = "🔴 Naik " + str(diff_percent) + "%"
        suggestion = "Minggu yang cukup sibuk buat dompetmu, ya? 💸 Mencatat saat pengeluaran naik itu justru yang paling hebat, karena kamu berani menghadapi realita. Besok kita coba lebih disiplin lagi, yuk!"
    elif diff < 0:
        status = "🟢 Turun " + str(diff_percent) + "%"
        suggestion = "Lihat deh angkanya... lebih hijau! 🍏 Kamu sukses mengendalikan godaan minggu ini. Pertahankan konsistensinya ya!"
    
    insight_text = (f"📅 *Weekly Financial Insight*\n"
                    "Halo! Seminggu ini kamu luar biasa tetap konsisten mencatat. Inilah rangkuman perjalanan uangmu:\n"
                    f"💰 Total Pengeluaran: `Rp {this_week_total:,.0f}` ({status})\n\n"
                    f"💡 {suggestion}"
                )

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
    c.execute(
        "SELECT COUNT(*), MIN(datetime(date, '+7 hours')) FROM transactions WHERE user_id=?", (user_id,)
    )
    total_entries, start_date = c.fetchone()

    c.execute(
        "SELECT category, COUNT(category) as count FROM transactions WHERE user_id=? GROUP BY category ORDER BY count DESC LIMIT 1", (user_id,)
    )
    most_freq = c.fetchone()

    c.execute("SELECT COUNT(DISTINCT date(date)) FROM transactions WHERE user_id=?", (user_id,))
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
                  f"🔥 *Hari aktif:* `{active_days} hari`\n"
                  f"🏷️ *Kategori Favorit:* `{freq_text}`\n"
                  "━━━━━━━━━━━━━━━\n"
                  f"_{pesan_motivasi}_")
    return stats_text

def generate_csv_export(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Ambil data spesifik user dengan waktu WIB
    query = """
        SELECT datetime(date, '+7 hours'), category, description, amount 
        FROM transactions 
        WHERE user_id = ? 
        ORDER BY date DESC
    """
    c.execute(query, (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return None

    # Buat buffer di memori
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Tanggal', 'Kategori', 'Keterangan', 'Nominal'])
    
    for row in rows:
        # Pembersihan kategori dari emoji dan spasi ganda
        clean_cat = re.sub(r'[^\x00-\x7F]+', '', row[1])
        clean_cat = " ".join(clean_cat.split()).strip()
        writer.writerow([row[0], clean_cat, row[2], row[3]])
    
    # Kembalikan pointer ke awal file virtual
    output.seek(0)
    return output

def get_report(period , user_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    if period == 'daily':
        c.execute(
        "SELECT description, amount FROM transactions WHERE date(date, '+7 hours') = date('now', '+7 hours') AND user_id=?",
        (user_id,)
        )
        rows = c.fetchall()
        title = "📅 *REKAP HARI INI*"
        date = datetime.now().strftime('%d %B %Y')
        report_text = f"{title}\n{date}\n━━━━━━━━━━━━━━━\n"
        total = sum(item[1] for item in rows)
        for desc, amount in rows:
            report_text += f"• {desc}: `Rp {amount:,.0f}`\n"
    else:
        c.execute(
        """SELECT category, SUM(amount) as total 
                   FROM transactions 
                   WHERE strftime('%m-%Y', date, '+7 hours') = strftime('%m-%Y', 'now', '+7 hours') AND user_id=?
                   GROUP BY category ORDER BY total DESC""",
        (user_id,)
        )
        rows = c.fetchall()
        title = "📊 *REKAP BULAN INI*"
        date = datetime.now().strftime('%B %Y')
        report_text = f"{title}\n{date}\n━━━━━━━━━━━━━━━\n"
        total = sum(item[1] for item in rows)

        for cat, amount in rows:
            porsi = (amount / total) * 100 if total > 0 else 0
            bar = "┃" + "█" * int(
                porsi / 10) + "░" * (10 - int(porsi / 10)) + "┃"
            report_text += f"*{cat}*\n`Rp {amount:>10,.0f}` {bar} {porsi:>3.0f}%\n"

    conn.close()
    if not rows: return f"{title}\n\nBelum ada data."
    report_text += f"━━━━━━━━━━━━━━━\n💰 *TOTAL: Rp {total:,.0f}*"
    motivasi = random.choice(MOTIVASI_BANK)
    report_text += "\n\n_" + motivasi + "_"
    return report_text
        