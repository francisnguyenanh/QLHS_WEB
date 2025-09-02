import sqlite3
from db_utils import connect_db

def setup_settings_table():
    """Tạo bảng Settings nếu chưa có"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            FOREIGN KEY (updated_by) REFERENCES Users(id)
        )
    """)
    
    # Thêm setting mặc định cho background
    cursor.execute("""
        INSERT OR IGNORE INTO Settings (setting_key, setting_value) 
        VALUES ('background_image', '')
    """)
    
    conn.commit()
    conn.close()
    print("Settings table created successfully!")

if __name__ == '__main__':
    setup_settings_table()
