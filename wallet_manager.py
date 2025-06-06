### wallet_manager.py

import sqlite3

from config import DB_NAME

# Initialize wallets and positions tables
def init_wallet_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS tracked_wallets (wallet TEXT PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS position_changes (
                        wallet TEXT,
                        timestamp TEXT,
                        change_type TEXT,
                        market TEXT,
                        size REAL,
                        entry REAL,
                        direction TEXT
                    )''')
    conn.commit()
    conn.close()

def get_wallets():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT wallet FROM tracked_wallets")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_wallet(wallet):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO tracked_wallets (wallet) VALUES (?)", (wallet,))
    conn.commit()
    conn.close()

def remove_wallet(wallet):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tracked_wallets WHERE wallet = ?", (wallet,))
    conn.commit()
    conn.close()

def save_position_change(wallet, timestamp, change_type, market, size, entry, direction):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO position_changes (wallet, timestamp, change_type, market, size, entry, direction)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (wallet, timestamp, change_type, market, size, entry, direction))
    conn.commit()
    conn.close()