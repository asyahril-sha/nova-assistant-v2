# update_db.py
import sqlite3
import os

def update_database():
    """Update database schema to add missing columns"""
    db_path = "gadis_v59.db"  # Sesuaikan dengan nama database Anda
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} tidak ditemukan!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cek kolom yang ada
    cursor.execute("PRAGMA table_info(relationships)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print("Kolom yang ada di tabel relationships:", columns)
    
    # Tambahkan kolom yang hilang satu per satu
    columns_to_add = [
        ("current_clothing", "TEXT DEFAULT 'pakaian biasa'"),
        ("last_clothing_change", "TIMESTAMP"),
        ("hair_style", "TEXT"),
        ("height", "INTEGER"),
        ("weight", "INTEGER"),
        ("breast_size", "TEXT"),
        ("hijab", "BOOLEAN DEFAULT 0"),
        ("most_sensitive_area", "TEXT")
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE relationships ADD COLUMN {col_name} {col_type}")
                print(f"✅ Kolom {col_name} berhasil ditambahkan")
            except Exception as e:
                print(f"❌ Gagal menambahkan {col_name}: {e}")
        else:
            print(f"⏭️  Kolom {col_name} sudah ada")
    
    conn.commit()
    conn.close()
    print("\n✅ Update database selesai!")

if __name__ == "__main__":
    update_database()
