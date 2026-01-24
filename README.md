# 💸 LiteSpend Bot: Personal Finance Habit Tracker

**LiteSpend** adalah bot Telegram minimalis yang dirancang untuk satu tujuan: **membangun kebiasaan mencatat keuangan tanpa ribet.** 

Berbeda dengan aplikasi keuangan yang penuh dengan grafik kompleks dan menu yang membingungkan, LiteSpend mengutamakan kecepatan input dan kesederhanaan. Dirancang untuk bisa dijalankan sendiri (*self-hosted*) di server rumah VPS spesifikasi rendah (Low-Spec).

<img src="https://blog.bakhtiar.my.id/wp-content/uploads/2026/01/1000279845-459x1024.jpg" alt="LiteSpend Bot Screenshot" width="40%" height="auto">

## ✨ Fitur Utama
- ⚡ **Hybrid Input:** Ketik nominal (e.g., `Kopi 15k`) dan pilih kategori lewat tombol interaktif.
- 📊 **Smart Reports:** Rekap harian mendetail & rekap bulanan yang dikelompokkan per kategori dengan bar chart visual (ASCII).
- 🔔 **Habit Reminder:** Bot akan mengingatkanmu setiap jam 9 malam jika kamu lupa mencatat hari itu.
- 🗑️ **Quick Undo:** Salah input? Cukup gunakan fitur hapus transaksi terakhir.
- 📂 **CSV Export:** Ekspor seluruh data ke format CSV yang siap dibuka di Excel atau Google Sheets.
- 🔒 **Privacy-First:** Data disimpan di database SQLite milikmu sendiri. Bot hanya merespons ID Telegram yang sudah kamu whitelist.

## 🛠️ Persyaratan Sistem
- **OS:** Linux (Debian direkomendasikan).
- **Container Engine:** Podman atau Docker.
- **Resources:** Minimal RAM 512MB (sangat ringan!).

## 🚀 Cara Instalasi (Self-Hosted)

### 1. Persiapan Bot Telegram
1. Chat dengan [@BotFather](https://t.me/botfather).
2. Buat bot baru dan simpan `API_TOKEN`.
3. Dapatkan ID Telegram kamu melalui [@userinfobot](https://t.me/userinfobot).

### 2. Setup Folder di VPS
```bash
git clone [https://github.com/b4khtiar/litespend-bot.git](https://github.com/b4khtiar/litespend-bot.git)
cd litespend-bot
```
### 3. Konfigurasi Environment
Buat file .env di root folder:
```env
TOKEN=12345678:ABCDEFG_YOUR_TOKEN
ALLOWED_ID=123456789
```

### 4. Jalankan dengan Podman
```bash
podman-compose up --build -d
```
## ⌨️ Command Bot
- /start - Memulai bot dan petunjuk penggunaan.
- /rekap - Melihat laporan harian dan bulanan (grouping kategori).
- /hapus - Menghapus transaksi terakhir jika salah input.
- /export - Mendapatkan file CSV seluruh data transaksi.
- /stats - Lihat statistik habit plus motivasi terpilih.

## Tips
Untuk menjaga chat tetap bersih, gunakan "Auto-Delete Messages":
1. Buka chat bot kamu di Telegram.
2. Klik nama bot di bagian atas.
3. Klik ikon titik tiga (⋮) atau "More".
4. Pilih Enable Auto-Delete (Bisa pilih 24 jam, 1 minggu, atau custom).

## 🏗️ Struktur Proyek
```plaintext

├── src/
│   ├── bot.py         # Logika utama bot & scheduler
├── data/              # Persistent storage (finance.db & CSV)
├── Dockerfile      # Definisi image container (Alpine based)
└── docker-compose.yml
```

## 🤝 Kontribusi
****
Bot ini dibuat untuk penggunaan pribadi yang praktis. Jika kamu punya ide fitur atau menemukan bug, silakan buka Issue atau kirimkan Pull Request.



Built with ❤️ for a better financial habit.