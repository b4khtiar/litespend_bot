import sqlite3
import os

DB_PATH = os.path.join(os.getcwd(), 'data', 'finance.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    # Agar hasil query bisa diakses seperti dictionary (opsional tapi membantu)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  amount REAL,
                  category TEXT,
                  description TEXT,
                  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Menambahkan Index untuk user_id agar pencarian lebih cepat
    c.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON transactions(user_id)')
    
    # (Opsional) Index untuk tanggal juga sangat disarankan karena kita sering query berdasarkan waktu
    c.execute('CREATE INDEX IF NOT EXISTS idx_date ON transactions(date)')

    c.execute('''CREATE TABLE IF NOT EXISTS insights
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  period_type TEXT, -- 'weekly' atau 'monthly'
                  period_date TEXT, -- format 'YYYY-WW' atau 'YYYY-MM'
                  total_amount REAL,
                  trend_percent REAL,
                  insight_text TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()