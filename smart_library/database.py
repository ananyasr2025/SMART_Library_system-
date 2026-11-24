# One helper for ALL SQL. mysql.connector opens the connection using Config.DB.
import mysql.connector
from config import Config

def query(sql, args=(), one=False, commit=False):
    conn = mysql.connector.connect(**Config.DB)
    cur = conn.cursor(dictionary=True)   # rows come back as dicts
    try:
        cur.execute(sql, args)           # %s placeholders prevent SQL injection
        if commit:
            conn.commit()
            return cur.lastrowid
        return cur.fetchone() if one else cur.fetchall()
    finally:
        cur.close(); conn.close()
