import sqlite3
import os

DB_NAME = "fir_records.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fir_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lr_no TEXT UNIQUE,
    name TEXT NOT NULL,
    mobile TEXT,
    address TEXT,
    pincode TEXT,
    incident TEXT NOT NULL,
    pdf_path TEXT NOT NULL,
    created_at DATETIME
    )
    """)


    conn.commit()
    conn.close()
