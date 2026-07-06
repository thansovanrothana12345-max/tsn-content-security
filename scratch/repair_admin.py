import sqlite3
import hashlib
import os
import sys

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import hash_password

db_paths = [
    "storage/database.db",
    "dist/CopyrightCenter/storage/database.db"
]

admin_hash = hash_password("AdminPassword123")

for db_path in db_paths:
    if not os.path.exists(os.path.dirname(db_path)):
        print(f"Skipping directory that does not exist: {db_path}")
        continue
        
    print(f"Repairing database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Ensure users table exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('Admin', 'Editor', 'Reviewer', 'Guest')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Ensure we have the user
    cursor.execute("SELECT id FROM users WHERE email = 'admin@example.com'")
    user = cursor.fetchone()
    
    if user:
        # Repair password and role and username
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, role = 'Admin', username = 'admin' 
            WHERE email = 'admin@example.com'
        """, (admin_hash,))
        print(f"Updated existing user admin@example.com in {db_path}")
    else:
        # Ensure username 'admin' doesn't conflict
        cursor.execute("DELETE FROM users WHERE username = 'admin'")
        # Insert new admin
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role) 
            VALUES ('admin', 'admin@example.com', ?, 'Admin')
        """, (admin_hash,))
        print(f"Created new user admin@example.com in {db_path}")
        
    conn.commit()
    conn.close()

print("Admin database repair completed on all active databases.")
