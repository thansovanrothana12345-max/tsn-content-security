import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Insert first row
cursor.execute(
    "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json) VALUES (?, ?, ?, ?, ?);",
    (1, 'TEST_CHAIN_1', 'case', 1, '{}')
)
# Insert second row
cursor.execute(
    "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json) VALUES (?, ?, ?, ?, ?);",
    (2, 'TEST_CHAIN_2', 'evidence', 10, '{"meta": true}')
)

conn.commit()

# Fetch last 2 rows
cursor.execute("SELECT id, user_id, action, previous_entry_hash, entry_hash FROM audit_logs ORDER BY id DESC LIMIT 2;")
rows = cursor.fetchall()
for r in rows:
    print(dict(r))

conn.close()
