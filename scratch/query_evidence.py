import sqlite3

def main():
    conn = sqlite3.connect('storage/database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    rows = cursor.execute('SELECT id, case_id, title, url, file_size, file_type, created_at FROM evidence ORDER BY id DESC LIMIT 50')
    for r in rows:
        title_safe = str(r['title']).encode('ascii', errors='replace').decode('ascii')
        url_safe = str(r['url']).encode('ascii', errors='replace').decode('ascii')
        print(f"ID: {r['id']} | Case: {r['case_id']} | Title: {title_safe} | Size: {r['file_size']} | Type: {r['file_type']} | Date: {r['created_at']}")
        
    conn.close()

if __name__ == "__main__":
    main()
