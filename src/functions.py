from database import get_db_connection
import random
from datetime import datetime, timedelta
import io
import re
import csv
from dateutil.relativedelta import relativedelta


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
    item = {
        "id": data[0],
        "user_id": data[1],
        "amount": data[2],
        "category": data[3],
        "description": data[4],
        "date": data[5]
    }
    return item

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
    item = get_last_transaction(user_id)
    if item is None:
        return False
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?", (item['id'],))
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

def get_weekly_insight_logic(user_id, is_archive=False):
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

    # 2. Jika tidak ada, jalankan kalkulasi
    c.execute("SELECT SUM(amount) FROM transactions WHERE date >= date('now', '-7 days') AND user_id=?", (user_id,))
    this_week_total = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE date >= date('now', '-14 days') AND date < date('now', '-7 days') AND user_id=?", (user_id,))
    last_week_total = c.fetchone()[0] or 0
    
    if this_week_total == 0 and last_week_total == 0:
        conn.close()
        return "Belum ada data pengeluaran minggu ini."
    
    # find top 3 categories
    c.execute("SELECT category, COUNT(*) as count FROM transactions WHERE date >= date('now', '-7 days') AND user_id=? GROUP BY category ORDER BY count DESC LIMIT 3", (user_id,))
    top_categories = c.fetchall()
    
    diff = this_week_total - last_week_total
    diff_percent = 0
    if last_week_total > 0:
        # buat persentase (absolut dan bulatkan tanpa desimal)
        diff_percent = round(abs(diff / last_week_total * 100))

    emotion = "happy" if diff <= 0 else "sad"
    status = "Stabil"
    suggestion = "Pengeluaranmu minggu ini stabil banget! ⚖️ Ini tanda kamu sudah punya kontrol yang matang atas gaya hidupmu. Predictable is good! 👏"
    if diff > 0:
        status = "🔴 Naik " + str(diff_percent) + "%"
        suggestion = "Minggu yang cukup sibuk buat dompetmu, ya? 💸 Mencatat saat pengeluaran naik itu justru yang paling hebat, karena kamu berani menghadapi realita. Besok kita coba lebih disiplin lagi, yuk!"
    elif diff < 0:
        status = "🟢 Turun " + str(diff_percent) + "%"
        suggestion = "Lihat deh angkanya... lebih hijau! 🍏 Kamu sukses mengendalikan godaan minggu ini. Pertahankan konsistensinya ya!"
    
    insight_text = (f"📅 *Weekly Financial Insight*\n\n"
                    "Halo! Seminggu ini kamu luar biasa tetap konsisten mencatat. Inilah rangkuman perjalanan uangmu:\n\n"
                    f"💰 *Total Pengeluaran*: `Rp {this_week_total:,.0f}` ({status} dari pekan lalu.)\n\n"
                    f"📊 *Top Kategori*\n")
    # add category with count (only top 3 count)
    top_3_categories = top_categories[:3]
    for category, count in top_3_categories:
        insight_text += f"- {category}: {count}x\n"

    insight_text += f"\n💡 {suggestion}"
                

    if is_archive:
        c.execute("""INSERT INTO insights (user_id, period_type, period_date, total_amount, trend_percent, insight_text) 
                     VALUES (?, ?, ?, ?, ?, ?)""", 
                  (user_id, 'weekly', current_period, this_week_total, diff_percent, insight_text))    
    conn.commit()
    conn.close()
    
    return insight_text, emotion

def get_monthly_insight_logic(user_id, is_archive=False):
    now = datetime.now()
    current_period = now.strftime('%Y-%m')
    
    # Cara paling aman menghitung bulan lalu (termasuk ganti tahun)
    last_month_date = now - relativedelta(months=1)
    previous_period = last_month_date.strftime('%Y-%m')
    
    day_today = now.day

    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Cek cache insight bulan ini
    c.execute("""SELECT insight_text FROM insights 
                 WHERE period_type='monthly' AND period_date=? AND user_id=?""", 
              (current_period, user_id))
    existing = c.fetchone()
    if existing:
        conn.close()
        return existing[0] + "\n\n_(Arsip)_"

    # 2. Hitung total bulan ini (Gunakan format YYYY-MM agar index idx_date terpakai)
    c.execute("""SELECT SUM(amount) FROM transactions 
                 WHERE strftime('%Y-%m', date, '+7 hours') = ? AND user_id=?""", 
              (current_period, user_id))
    this_month_total = c.fetchone()[0] or 0

    if this_month_total == 0:
        conn.close()
        return "Bulan ini belum ada catatan. Yuk, mulai catat! ✨"

    # 3. Top Category
    c.execute("""
        SELECT category, SUM(amount) as total_cat 
        FROM transactions 
        WHERE strftime('%Y-%m', date, '+7 hours') = ? AND user_id=?
        GROUP BY category 
        ORDER BY total_cat DESC LIMIT 1
    """, (current_period, user_id))
    top_cat_data = c.fetchone()
    top_category = top_cat_data[0] if top_cat_data else "Lainnya"

    # 4. Ambil data bulan lalu dari tabel INSIGHTS (Bukan hitung ulang tabel transaksi)
    c.execute("""SELECT total_amount FROM insights 
                 WHERE period_type='monthly' AND period_date=? AND user_id=?""", 
              (previous_period, user_id))
    prev_data = c.fetchone()

    emotion = "happy"
    # --- KONSTRUKSI TEKS ---
    insight_text = f"📊 *Ringkasan {now.strftime('%B %Y')}*\n━━━━━━━━━━━━━━━\n\n"
    diff_percent = 0
    daily_avg = round(this_month_total / day_today)

    if prev_data:
        previous_total = prev_data[0]
        diff = this_month_total - previous_total
        if previous_total > 0:
            diff_percent = round(abs(diff / previous_total * 100))
        
        status = "Stabil"
        if diff > 0: 
            status = f"🔴 Naik {diff_percent}%"
            emotion = "sad"
        elif diff < 0: status = f"🟢 Turun {diff_percent}%"
        
        insight_text += f"Total pengeluaran *Rp {this_month_total:,.0f}*, {status} dari bulan lalu.\n"
    else:
        insight_text += f"Bulan pertamamu! Total: *Rp {this_month_total:,.0f}*.\n"

    insight_text += (
        f"\n📍 *Insight:*\n"
        f"• Terbanyak: *{top_category}*\n"
        f"• Rata-rata harian: *Rp {daily_avg:,.0f}*\n\n"
        f"💡 _Tips: Jaga pengeluaran di {top_category} agar bulan depan lebih hemat!_"
    )

    if is_archive:
        c.execute("""INSERT INTO insights (user_id, period_type, period_date, total_amount, trend_percent, insight_text) 
                     VALUES (?, ?, ?, ?, ?, ?)""", 
                  (user_id, 'monthly', current_period, this_month_total, diff_percent, insight_text))
    
    conn.commit()
    conn.close()
    return insight_text, emotion

def get_stats_logic(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT category, COUNT(category) as count FROM transactions WHERE user_id=? GROUP BY category ORDER BY count DESC LIMIT 1", (user_id,)
    )
    most_freq = c.fetchone()
    conn.close()

    if not most_freq:
        return "Belum ada statistik. Yuk, mulai mencatat!"

    stats = get_user_stats(user_id)
    # Bersihkan tampilan tanggal (hilangkan waktu & format %d %B %Y)
    start_date_clean = "-"
    if stats['first_input_date']:
        start_date_strip = stats['first_input_date'].split()[0]
        start_date_clean = datetime.strptime(start_date_strip, "%Y-%m-%d").strftime("%d %B %Y")
    last_date_clean = "hari ini"  # sementara
    if stats['last_input_date']:
        last_date_strip = stats['last_input_date'].split()[0]
        last_date_clean = datetime.strptime(last_date_strip, "%Y-%m-%d").strftime("%d %B %Y")
    freq_text = f"{most_freq[0]} ({most_freq[1]}x)" if most_freq else "-"

    # Ambil motivasi random
    pesan_motivasi = random.choice(MOTIVASI_BANK)

    stats_text = ("📈 *STATISTIK PENGGUNAAN*\n"
                  "━━━━━━━━━━━━━━━\n"
                  f"🗓️ *Mulai Sejak:* `{start_date_clean}`\n"
                  f"📅 *Terakhir Mencatat:* `{last_date_clean}`\n"
                  f"✅ *Aktif Mencatat:* `{stats['total_days']} hari`\n"
                  f"🔥 *Streak:* `{stats['current_streak']} hari`\n"
                  f"🏆 *Rekor:* `{stats['longest_streak']} hari`\n"
                  f"🏷️ *Top Kategori:* `{freq_text}`\n"
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

def get_user_stats(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT current_streak, longest_streak, first_input_date, total_days, last_input_date FROM user_stats WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'current_streak': row[0],
            'longest_streak': row[1],
            'first_input_date': row[2],
            'total_days': row[3],
            'last_input_date': row[4]
        }
    return None

def save_user_stats(user_id, new_streak, new_longest, new_active, input_date):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE user_stats SET current_streak=?, longest_streak=?, total_days=?, last_input_date=? WHERE user_id=?",
              (new_streak, new_longest, new_active, input_date, user_id))
    conn.commit()
    conn.close()

def create_user_stats(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    date_today = datetime.now().date()
    c.execute(
        "SELECT COUNT(*), MIN(datetime(date, '+7 hours')) FROM transactions WHERE user_id=?", (user_id,)
    )
    total_entries, start_date = c.fetchone()
    c.execute("SELECT COUNT(DISTINCT date(date)) FROM transactions WHERE user_id=?", (user_id,))
    active_days = c.fetchone()[0]
    
    c.execute("INSERT INTO user_stats (user_id, current_streak, longest_streak, total_days, first_input_date, last_input_date) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, active_days, active_days, active_days, start_date, date_today))
    conn.commit()
    conn.close()
    return active_days

def update_streak(user_id):
    # date string with format YYYY-MM-DD
    today_str = datetime.now().strftime('%Y-%m-%d')
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    two_days_ago_str = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    message = None
    # Ambil data streak user
    stats = get_user_stats(user_id) # {current_streak, last_input_date}
    if stats == None:
        start_streak = create_user_stats(user_id)
        message = "🔥 *Streak Dimulai!* Kamu telah mencatat pengeluaran pertamamu. Terus konsisten ya! 🚀"
        return start_streak, False, message
    
    last_date = stats['last_input_date']
    current_s = stats['current_streak']
    new_active = stats['total_days'] + 1
    if last_date == today_str:
        return current_s, False, message # Sudah update hari ini
    
    if last_date == yesterday_str:
        new_streak = current_s + 1
        show_congrats = True if new_streak in [3, 7, 10, 30, 60, 100, 180, 365, 500, 730, 1000] else False
    elif last_date == two_days_ago_str:
        new_streak = current_s + 2
        show_congrats = False
        message = "🛡️ *Streak Recovery Active!* Aku selamatkan streak-mu karena kamu kembali hari ini. Lanjutkan konsistensinya! 🔥"
    else:
        new_streak = 1
        show_congrats = False
        message = "📉 *Streak terputus.* Gak apa-apa, ayo mulai perjalanan baru hari ini! Semangat lagi! ✨"
    
    new_longest = stats['longest_streak']
    if new_longest < new_streak:
        new_longest = new_streak

    save_user_stats(user_id, new_streak, new_longest, new_active, today_str)
    return new_streak, show_congrats, message

def show_milestone(streak):
    milestones = {
        3: "🌱 *Awal yang solid!* 3 hari berturut-turut mencatat. Kebiasaan baik mulai terbentuk!",
        7: "🔥 *Satu minggu penuh!* Kamu sudah membuktikan kalau kamu bisa disiplin. Lanjutkan!",
        10: "✅ *Double digits!* 10 hari konsisten. Kontrol keuanganmu makin mantap nih.",
        30: "🚀 *Satu bulan luar biasa!* Kamu sudah menjadikan finansial sehat sebagai gaya hidup.",
        60: "💎 *Dua bulan konsisten!* Kedisiplinanmu adalah investasi terbaik untuk masa depanmu.",
        100: "💯 *Angka legendaris!* 100 hari tanpa putus. Kamu sudah berada di level yang berbeda!",
        180: "🌟 *Setengah tahun!* Kamu sudah menguasai seni mengelola uang. Inspiratif banget!",
        365: "👑 *Satu tahun penuh!* Kamu resmi jadi pahlawan keuanganmu sendiri. Selamat atas dedikasimu!",
        500: "🏛️ *Kokoh tak tergoyahkan!* 500 hari mencatat adalah bukti nyata komitmenmu.",
        730: "🛡️ *Dua tahun konsisten!* Finansialmu sudah punya pondasi baja berkat ketelitianmu.",
        1000: "🌌 *Luar biasa!* 1000 hari adalah sebuah pencapaian langka. Kamu benar-benar hebat!"
    }
    return milestones.get(streak, "")
