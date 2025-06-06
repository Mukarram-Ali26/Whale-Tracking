import sqlite3
from config import DB_NAME

def get_tracked_wallets():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS wallets (address TEXT PRIMARY KEY)")
    wallets = [row[0] for row in cursor.execute("SELECT address FROM wallets").fetchall()]
    conn.close()
    return wallets
