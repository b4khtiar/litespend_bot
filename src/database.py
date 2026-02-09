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

    c.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON transactions(user_id)')
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

    c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_insight 
                 ON insights (user_id, period_type, period_date)''')
    
    # create table user_stats (drop if exist)
    c.execute('''DROP TABLE IF EXISTS user_stats''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  current_streak INTEGER DEFAULT 0,
                  longest_streak INTEGER DEFAULT 0,
                  first_input_date TEXT,
                  total_days INTEGER DEFAULT 0,
                  last_input_date TEXT,
                  latest_recovery_date TEXT DEFAULT "",
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # create index for user_stats
    c.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON user_stats(user_id)')

    conn.commit()
    conn.close()
