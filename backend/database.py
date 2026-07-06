import sqlite3
import os
import hashlib
from backend.config import Config

DATABASE_PATH = os.path.abspath(Config.DATABASE_URL)

import bcrypt

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_db_connection():
    """Returns a SQLite connection with WAL journal mode and cached optimizations."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # Performance Optimizations: Enable WAL and increase cache sizes
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -10000;") # ~10MB Cache size limit
    except sqlite3.OperationalError:
        pass
    return conn

def init_db():
    """Initializes the database schema with constraints, indices, and defaults."""
    # Ensure storage folders exist
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    os.makedirs(os.path.join(Config.STORAGE_DIR, "originals"), exist_ok=True)
    os.makedirs(os.path.join(Config.STORAGE_DIR, "evidence"), exist_ok=True)
    os.makedirs(os.path.join(Config.STORAGE_DIR, "temp"), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Schema Migrations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        migration_name TEXT NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Users Table
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
    
    # 3. Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    
    # 4. Audit Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER,
        details_json TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)
    
    # 5. Cases Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL CHECK (length(title) > 0),
        description TEXT,
        owner_user_id INTEGER,
        assigned_user_id INTEGER,
        priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
        status TEXT NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft', 'Investigating', 'Scanning', 'Evidence Collected', 'Verified', 'DMCA Draft', 'DMCA Sent', 'Resolved', 'Archived', 'Active', 'Closed', 'Suspended')),
        tags TEXT,
        client_name TEXT,
        platform TEXT,
        is_deleted INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY (assigned_user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)
    
    # Run dynamic migration alterations for existing databases
    for col, definition in [("client_name", "TEXT"), ("platform", "TEXT"), ("is_deleted", "INTEGER DEFAULT 0")]:
        try:
            cursor.execute(f"ALTER TABLE cases ADD COLUMN {col} {definition};")
        except sqlite3.OperationalError:
            pass # column already exists
    
    # 5b. Case Notes Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS case_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        note TEXT NOT NULL CHECK (length(note) > 0),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    
    # 5c. Archived Cases Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS archived_cases (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        archive_json TEXT NOT NULL,
        archived_by INTEGER,
        archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE SET NULL
    );
    """)
    
    # 6. Originals Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS originals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        file_uuid TEXT NOT NULL UNIQUE,
        storage_provider TEXT NOT NULL CHECK (storage_provider IN ('local', 's3', 'r2')),
        filesize INTEGER NOT NULL CHECK (filesize > 0),
        duration REAL NOT NULL CHECK (duration >= 0.0),
        fingerprint_json TEXT,
        metadata_analysis_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    """)
    
    # 7. Evidence Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        platform TEXT NOT NULL CHECK (platform IN ('YouTube', 'TikTok', 'Facebook', 'Instagram', 'Other')),
        url TEXT NOT NULL CHECK (length(url) > 0),
        title TEXT,
        uploader TEXT,
        upload_date TEXT,
        similarity_score REAL DEFAULT 0.0 CHECK (similarity_score BETWEEN 0.0 AND 1.0),
        status TEXT NOT NULL DEFAULT 'Detected' CHECK (status IN ('Detected', 'Verified', 'DMCA Drafted', 'DMCA Filed', 'Resolved')),
        screenshot_path TEXT,
        ocr_text TEXT,
        ocr_metadata_json TEXT,
        logo_metadata_json TEXT,
        metadata_comparison_json TEXT,
        similarity_report_json TEXT,
        confidence_score REAL DEFAULT 0.0 CHECK (confidence_score BETWEEN 0.0 AND 1.0),
        confidence_level TEXT CHECK (confidence_level IN ('Low', 'Medium', 'High')),
        confidence_report_json TEXT,
        file_type TEXT,
        file_size INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    """)
    
    # 7b. Evidence Attachments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence_attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evidence_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        filesize INTEGER NOT NULL CHECK (filesize > 0),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
    );
    """)
    
    # Dynamic schema migration for existing database installations
    try:
        cursor.execute("ALTER TABLE originals ADD COLUMN metadata_analysis_json TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN ocr_text TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN ocr_metadata_json TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN logo_metadata_json TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN metadata_comparison_json TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN similarity_report_json TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN confidence_score REAL DEFAULT 0.0;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN confidence_level TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN confidence_report_json TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN file_type TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE evidence ADD COLUMN file_size INTEGER;")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE cases ADD COLUMN owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE cases ADD COLUMN assigned_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE cases ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High'));")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE cases ADD COLUMN tags TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE cases ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    except sqlite3.OperationalError:
        pass
    
    # 8. Reports Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dmca_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        platform TEXT NOT NULL,
        sender_name TEXT NOT NULL,
        sender_email TEXT NOT NULL,
        sender_phone TEXT,
        sender_address TEXT,
        copyright_owner_name TEXT NOT NULL,
        report_text TEXT NOT NULL,
        template_type TEXT,
        signature_base64 TEXT,
        status TEXT NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft', 'Signed', 'Exported')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    """)
    
    try:
        cursor.execute("ALTER TABLE dmca_reports ADD COLUMN template_type TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE dmca_reports ADD COLUMN signature_base64 TEXT;")
    except sqlite3.OperationalError:
        pass
    
    # 9. Background Jobs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS background_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        job_type TEXT NOT NULL CHECK (job_type IN ('fingerprint_original', 'scan_link')),
        status TEXT NOT NULL DEFAULT 'Queued' CHECK (status IN ('Queued', 'Processing', 'Completed', 'Failed')),
        payload_json TEXT NOT NULL,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    """)
    
    # 10. Duplicate Groups Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS duplicate_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        representative_file_uuid TEXT NOT NULL,
        representative_file_type TEXT NOT NULL CHECK (representative_file_type IN ('original', 'evidence')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS duplicate_group_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        member_file_uuid TEXT NOT NULL,
        member_file_type TEXT NOT NULL CHECK (member_file_type IN ('original', 'evidence')),
        similarity_score REAL NOT NULL,
        is_exact INTEGER NOT NULL CHECK (is_exact IN (0, 1)),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES duplicate_groups(id) ON DELETE CASCADE
    );
    """)
    
    # 11. Evidence Packages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence_packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evidence_id INTEGER NOT NULL,
        case_id INTEGER NOT NULL,
        evidence_hash TEXT NOT NULL UNIQUE,
        package_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    """)
    
    # 12. Timeline Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timeline_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        evidence_id INTEGER,
        module_name TEXT NOT NULL CHECK (module_name IN ('video', 'image', 'audio', 'ocr', 'logo', 'metadata', 'similarity', 'confidence', 'duplicate', 'evidence')),
        event_type TEXT NOT NULL,
        timestamp REAL NOT NULL CHECK (timestamp >= 0.0),
        confidence REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
        description TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
        FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
    );
    """)
    
    # Create Indices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_originals_case ON originals(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_similarity ON evidence(similarity_score);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_case ON dmca_reports(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON background_jobs(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_duplicate_members ON duplicate_group_members(group_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_packages_hash ON evidence_packages(evidence_hash);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_packages_case ON evidence_packages(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_case_time ON timeline_events(case_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_evidence ON timeline_events(evidence_id);")
    
    # 13. Jobs Queue Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        evidence_id INTEGER,
        job_type TEXT NOT NULL CHECK (job_type IN ('asset_ingestion', 'leak_scan', 'reindex')),
        status TEXT NOT NULL DEFAULT 'Queued' CHECK (status IN ('Queued', 'Processing', 'Completed', 'Failed')),
        priority INTEGER NOT NULL DEFAULT 2,
        progress_percentage REAL NOT NULL DEFAULT 0.0,
        retries_count INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        payload_json TEXT NOT NULL,
        error_traceback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
        FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_queue_polling ON jobs_queue(status, priority, created_at);")
    
    # 14. Verification Center Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verification_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Verified', 'Pending', 'Rejected')),
        ai_score REAL DEFAULT 0.0 CHECK (ai_score BETWEEN 0.0 AND 1.0),
        reviewer_id INTEGER,
        metadata_validation TEXT NOT NULL DEFAULT 'Pending' CHECK (metadata_validation IN ('Verified', 'Warning', 'Pending', 'Failed')),
        hash_verification TEXT NOT NULL DEFAULT 'Pending' CHECK (hash_verification IN ('Verified', 'Warning', 'Pending', 'Failed')),
        evidence_summary TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
        FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_verification_case ON verification_records(case_id);")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verification_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        verification_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        note TEXT NOT NULL CHECK (length(note) > 0),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (verification_id) REFERENCES verification_records(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_verification_notes_rec ON verification_notes(verification_id);")
    
    # Auto-populate verification records for any existing cases that don't have one
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO verification_records (case_id, status, ai_score, reviewer_id, metadata_validation, hash_verification, evidence_summary)
        SELECT 
            c.id, 
            'Pending', 
            COALESCE((SELECT MAX(similarity_score) FROM evidence WHERE case_id = c.id), 0.0),
            (SELECT id FROM users WHERE role = 'Admin' LIMIT 1),
            'Pending',
            'Pending',
            'Pending initial evaluation of evidence files.'
        FROM cases c;
        """)
    except Exception as e:
        print("Warning: Could not auto-populate verification_records:", str(e))
    
    # Seed default Admin User if missing or upgrade legacy SHA-256 hash
    cursor.execute("SELECT id, password_hash FROM users WHERE username = 'admin' OR email = 'admin@example.com';")
    admin_row = cursor.fetchone()
    if not admin_row:
        admin_pass_hash = hash_password("Admin123")
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, role)
        VALUES ('admin', 'admin@example.com', ?, 'Admin');
        """, (admin_pass_hash,))
        print("Default administrator seeded successfully (username: 'admin', password: 'Admin123').")
    else:
        db_hash = admin_row["password_hash"]
        if not db_hash.startswith("$2b$") and not db_hash.startswith("$2a$"):
            print("Upgrading legacy administrator password hash to bcrypt...")
            bcrypt_hash = hash_password("Admin123")
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (bcrypt_hash, admin_row["id"]))
            
    # Upgrade any other users with legacy SHA-256 password hashes to bcrypt (using 'GuestPassword123')
    cursor.execute("SELECT id, username, password_hash FROM users WHERE id != 1;")
    for row in cursor.fetchall():
        u_hash = row["password_hash"]
        if not u_hash.startswith("$2b$") and not u_hash.startswith("$2a$"):
            print(f"Upgrading legacy password hash for user '{row['username']}'...")
            new_hash = hash_password("GuestPassword123")
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (new_hash, row["id"]))
        
        
    # Seed Migration Version 1
    cursor.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 1;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO schema_migrations (version, migration_name)
        VALUES (1, 'Baseline Schema Setup');
        """)
        
    # Seed Migration Version 5: Relax check constraints on cases table
    cursor.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 5;")
    if cursor.fetchone()[0] == 0:
        print("Migrating cases table to relax check constraints for Sprint 5...")
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute("""
        CREATE TABLE cases_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL CHECK (length(title) > 0),
            description TEXT,
            owner_user_id INTEGER,
            assigned_user_id INTEGER,
            priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
            status TEXT NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft', 'Investigating', 'Scanning', 'Evidence Collected', 'Verified', 'DMCA Draft', 'DMCA Sent', 'Resolved', 'Archived', 'Active', 'Closed', 'Suspended')),
            tags TEXT,
            client_name TEXT,
            platform TEXT,
            is_deleted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (assigned_user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """)
        cursor.execute("""
        INSERT INTO cases_new (id, title, description, owner_user_id, assigned_user_id, priority, status, tags, client_name, platform, is_deleted, created_at, updated_at)
        SELECT id, title, description, owner_user_id, assigned_user_id, priority, status, tags, client_name, platform, is_deleted, created_at, updated_at
        FROM cases;
        """)
        cursor.execute("DROP TABLE cases;")
        cursor.execute("ALTER TABLE cases_new RENAME TO cases;")
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("""
        INSERT INTO schema_migrations (version, migration_name)
        VALUES (5, 'Sprint 5 cases check constraints relaxed');
        """)
        print("Cases table migration completed successfully.")
        
    conn.commit()
    conn.close()
    print("Database schema verified and initialized successfully at", DATABASE_PATH)

if __name__ == "__main__":
    init_db()
