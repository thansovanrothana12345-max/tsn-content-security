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
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Register compute_audit_hash custom function for audit log chaining (Sprint 9)
    def sqlite_audit_hash(user_id, action, entity_type, entity_id, details_json, prev_hash, created_at):
        import hashlib
        u_id = str(user_id) if user_id is not None else ""
        act = str(action) if action is not None else ""
        e_type = str(entity_type) if entity_type is not None else ""
        e_id = str(entity_id) if entity_id is not None else ""
        det = str(details_json) if details_json is not None else ""
        p_hash = str(prev_hash) if prev_hash is not None else "GENESIS"
        cat = str(created_at) if created_at is not None else ""
        
        data = f"{u_id}|{act}|{e_type}|{e_id}|{det}|{p_hash}|{cat}"
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
        
    conn.create_function("compute_audit_hash", 7, sqlite_audit_hash)

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
        sha256_hash TEXT,
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
        cursor.execute("ALTER TABLE evidence ADD COLUMN sha256_hash TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE scan_jobs ADD COLUMN case_id INTEGER;")
    except sqlite3.OperationalError:
        pass
        
    # Performance Tuning Indexes
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_hash ON assets(sha256_hash);")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_hash ON evidence(sha256_hash);")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_case_evidence_junction ON case_evidence(case_id, evidence_id);")
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
        cursor.execute("ALTER TABLE cases ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Critical', 'High', 'Medium', 'Low'));")
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
    
    # 9. Background Jobs Table Migration & Schema definition
    import json
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='background_jobs';")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(background_jobs);")
        bg_cols = [row["name"] for row in cursor.fetchall()]
        if bg_cols and "duration" not in bg_cols:
            try:
                cursor.execute("ALTER TABLE background_jobs RENAME TO background_jobs_old;")
                cursor.execute("""
                CREATE TABLE background_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER NOT NULL,
                    job_type TEXT NOT NULL CHECK (job_type IN ('fingerprint_original', 'scan_link')),
                    status TEXT NOT NULL DEFAULT 'Queued' CHECK (status IN ('Queued', 'Processing', 'Completed', 'Failed', 'Cancelled')),
                    payload_json TEXT NOT NULL,
                    error_message TEXT,
                    progress_percent REAL DEFAULT 0.0,
                    current_step TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    duration REAL,
                    url TEXT,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
                );
                """)
                cursor.execute("""
                INSERT INTO background_jobs (id, case_id, job_type, status, payload_json, error_message, progress_percent, current_step, created_at, started_at, completed_at, finished_at, updated_at)
                SELECT id, case_id, job_type, status, payload_json, error_message, progress_percent, current_step, created_at, started_at, completed_at, completed_at, updated_at
                FROM background_jobs_old;
                """)
                cursor.execute("DROP TABLE background_jobs_old;")
                
                # Update url values from payload
                cursor.execute("SELECT id, payload_json FROM background_jobs WHERE job_type = 'scan_link';")
                for job in cursor.fetchall():
                    try:
                        p = json.loads(job["payload_json"])
                        u = p.get("url")
                        if u:
                            cursor.execute("UPDATE background_jobs SET url = ? WHERE id = ?;", (u, job["id"]))
                    except Exception:
                        pass
                
            except Exception as e:
                print("[MIGRATION_ERROR]", e)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS background_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        job_type TEXT NOT NULL CHECK (job_type IN ('fingerprint_original', 'scan_link')),
        status TEXT NOT NULL DEFAULT 'Queued' CHECK (status IN ('Queued', 'Processing', 'Completed', 'Failed', 'Cancelled')),
        payload_json TEXT NOT NULL,
        error_message TEXT,
        progress_percent REAL DEFAULT 0.0,
        current_step TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        finished_at TIMESTAMP,
        duration REAL,
        url TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    """)
    
    try:
        cursor.execute("ALTER TABLE background_jobs ADD COLUMN progress_percent REAL DEFAULT 0.0;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE background_jobs ADD COLUMN current_step TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE background_jobs ADD COLUMN updated_at TIMESTAMP;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE background_jobs ADD COLUMN finished_at TIMESTAMP;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE background_jobs ADD COLUMN duration REAL;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE background_jobs ADD COLUMN url TEXT;")
    except sqlite3.OperationalError:
        pass
    
    
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
    
    # --- ENTERPRISE AI FINGERPRINT ENGINE SCHEMAS ---
    # 13. General Fingerprints Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fingerprints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL CHECK (entity_type IN ('original', 'evidence')),
        entity_id INTEGER NOT NULL,
        phash TEXT,
        ahash TEXT,
        dhash TEXT,
        whash TEXT,
        metadata_hash TEXT,
        ocr_fingerprint TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    """)
    
    # 14. Image Embeddings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS image_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fingerprint_id INTEGER NOT NULL,
        model_name TEXT NOT NULL,
        embedding BLOB NOT NULL,
        dimensions INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fingerprint_id) REFERENCES fingerprints(id) ON DELETE CASCADE
    );
    """)
    
    # 15. Video Embeddings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS video_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fingerprint_id INTEGER NOT NULL,
        model_name TEXT NOT NULL,
        frame_index INTEGER NOT NULL,
        timestamp_sec REAL NOT NULL,
        embedding BLOB NOT NULL,
        dimensions INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fingerprint_id) REFERENCES fingerprints(id) ON DELETE CASCADE
    );
    """)
    
    # 16. Audio Embeddings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audio_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fingerprint_id INTEGER NOT NULL,
        model_name TEXT NOT NULL,
        timestamp_start REAL NOT NULL,
        timestamp_end REAL NOT NULL,
        embedding BLOB NOT NULL,
        dimensions INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fingerprint_id) REFERENCES fingerprints(id) ON DELETE CASCADE
    );
    """)
    
    # 17. Scan History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        scan_type TEXT NOT NULL CHECK (scan_type IN ('image', 'video', 'audio', 'ocr', 'metadata', 'all')),
        status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
        error_message TEXT,
        progress_percent REAL DEFAULT 0.0,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    """)
    
    # 18. Similarity Results Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS similarity_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id INTEGER NOT NULL,
        source_entity_type TEXT NOT NULL CHECK (source_entity_type IN ('original', 'evidence')),
        source_entity_id INTEGER NOT NULL,
        target_entity_type TEXT NOT NULL CHECK (target_entity_type IN ('original', 'evidence')),
        target_entity_id INTEGER NOT NULL,
        match_type TEXT NOT NULL CHECK (match_type IN ('perceptual_hash', 'embedding', 'ocr', 'metadata', 'hybrid')),
        similarity_score REAL NOT NULL CHECK (similarity_score BETWEEN 0.0 AND 1.0),
        match_details_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (scan_id) REFERENCES scan_history(id) ON DELETE CASCADE
    );
    """)
    
    # 19. Feature Vectors Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feature_vectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fingerprint_id INTEGER NOT NULL,
        feature_type TEXT NOT NULL CHECK (feature_type IN ('ORB', 'SIFT', 'SURF', 'keypoints')),
        keypoints_json TEXT,
        descriptors_binary BLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fingerprint_id) REFERENCES fingerprints(id) ON DELETE CASCADE
    );
    """)
    
    # AI Index Optimizations
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fingerprints_case ON fingerprints(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fingerprints_entity ON fingerprints(entity_type, entity_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_embeddings_fp ON image_embeddings(fingerprint_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_embeddings_fp ON video_embeddings(fingerprint_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_embeddings_fp ON audio_embeddings(fingerprint_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_history_case ON scan_history(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_similarity_results_scan ON similarity_results(scan_id);")
    
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
    
    # Seed default System User with ID 0 for system-level actions/audit log foreign keys
    cursor.execute("SELECT id FROM users WHERE id = 0;")
    if not cursor.fetchone():
        system_pass_hash = hash_password("SystemAccountNoLoginPassword123")
        cursor.execute("""
        INSERT INTO users (id, username, email, password_hash, role)
        VALUES (0, 'system', 'system@local', ?, 'Admin');
        """, (system_pass_hash,))
        print("Default system user seeded successfully with ID 0.")

    # Seed default Admin User if missing or upgrade legacy SHA-256 hash
    cursor.execute("SELECT id, password_hash FROM users WHERE username = 'admin' OR email = 'admin@example.com';")
    admin_row = cursor.fetchone()
    if not admin_row:
        admin_pass_hash = hash_password("AdminPassword123")
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, role)
        VALUES ('admin', 'admin@example.com', ?, 'Admin');
        """, (admin_pass_hash,))
        print("Default administrator seeded successfully (username: 'admin', password: 'AdminPassword123').")
    else:
        db_hash = admin_row["password_hash"]
        if not db_hash.startswith("$2b$") and not db_hash.startswith("$2a$"):
            print("Upgrading legacy administrator password hash to bcrypt...")
            bcrypt_hash = hash_password("AdminPassword123")
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
        
    # Seed Migration Version 6: Expand background_jobs job_type check constraint
    cursor.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 6;")
    if cursor.fetchone()[0] == 0:
        print("Migrating background_jobs table to allow new AI fingerprinting job types...")
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute("""
        CREATE TABLE background_jobs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            job_type TEXT NOT NULL CHECK (job_type IN ('fingerprint_original', 'scan_link', 'fingerprint_video', 'fingerprint_audio')),
            status TEXT NOT NULL DEFAULT 'Queued' CHECK (status IN ('Queued', 'Processing', 'Completed', 'Failed', 'Cancelled')),
            payload_json TEXT NOT NULL,
            error_message TEXT,
            progress_percent REAL DEFAULT 0.0,
            current_step TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            finished_at TIMESTAMP,
            duration REAL,
            url TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
        );
        """)
        
        cursor.execute("""
        INSERT INTO background_jobs_new (id, case_id, job_type, status, payload_json, error_message, progress_percent, current_step, created_at, started_at, completed_at, finished_at, duration, url, updated_at)
        SELECT id, case_id, job_type, status, payload_json, error_message, progress_percent, current_step, created_at, started_at, completed_at, finished_at, duration, url, updated_at
        FROM background_jobs;
        """)
        
        cursor.execute("DROP TABLE background_jobs;")
        cursor.execute("ALTER TABLE background_jobs_new RENAME TO background_jobs;")
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("""
        INSERT INTO schema_migrations (version, migration_name)
        VALUES (6, 'AI Fingerprint Engine background jobs extension');
        """)
        print("Background jobs migration completed successfully.")
        
    # Seed Migration Version 11: Scan Center & Evidence Management tables
    cursor.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 11;")
    if cursor.fetchone()[0] == 0:
        print("Migrating schema to add Scan Center & Evidence Management tables (assets, scan_jobs, scan_results, case_evidence)...")
        
        # 1. assets Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER,
            asset_type TEXT NOT NULL CHECK (asset_type IN ('Video', 'Image', 'Audio', 'Document', 'Logo', 'Trademark')),
            filename TEXT NOT NULL,
            file_uuid TEXT NOT NULL UNIQUE,
            sha256_hash TEXT NOT NULL UNIQUE,
            owner_user_id INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Archived', 'Deleted')),
            fingerprint_status TEXT NOT NULL DEFAULT 'Pending' CHECK (fingerprint_status IN ('Pending', 'Processing', 'Completed', 'Failed', 'N/A')),
            fingerprint_json TEXT,
            metadata_json TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
            FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """)
        
        # 2. scan_jobs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER,
            url TEXT NOT NULL,
            platform TEXT NOT NULL CHECK (platform IN ('YouTube', 'TikTok', 'Instagram', 'Facebook Post', 'Facebook Ad Library', 'Website', 'Other')),
            status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Running', 'Completed', 'Failed', 'Cancelled')),
            progress_percent REAL DEFAULT 0.0,
            error_message TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        );
        """)
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN case_id INTEGER;")
        except sqlite3.OperationalError:
            pass
        
        # 3. scan_results Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            platform TEXT NOT NULL,
            title TEXT,
            uploader TEXT,
            upload_date TEXT,
            metadata_json TEXT,
            screenshot_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES scan_jobs(id) ON DELETE CASCADE
        );
        """)
        
        # 4. case_evidence Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_evidence (
            case_id INTEGER NOT NULL,
            evidence_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (case_id, evidence_id),
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
            FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
        );
        """)
        
        # Add indexers
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_case ON assets(case_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_jobs_status ON scan_jobs(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_results_job ON scan_results(job_id);")
        
        cursor.execute("""
        INSERT INTO schema_migrations (version, migration_name)
        VALUES (11, 'Scan Center and Asset Library tables');
        """)
        print("Scan Center and Asset Library schema migration completed successfully.")

    # 20. Worker Heartbeats Table for Sprint 6 Monitoring
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS worker_heartbeats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL CHECK (status IN ('Idle', 'Processing', 'Terminated')),
        active_job_id INTEGER,
        active_job_type TEXT,
        cpu_load REAL DEFAULT 0.0,
        memory_mb REAL DEFAULT 0.0,
        heartbeat_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_time ON worker_heartbeats(heartbeat_at);")

    # 21. Scan Sessions Table for Sprint 7 Workflow
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_uuid TEXT NOT NULL UNIQUE,
        case_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('Pending', 'Running', 'Paused', 'Cancelled', 'Completed', 'Failed')),
        progress_percent REAL DEFAULT 0.0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    );
    """)
    
    # 22. Scan Session Tasks Table (DAG nodes)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_session_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        task_uuid TEXT NOT NULL UNIQUE,
        task_type TEXT NOT NULL CHECK (task_type IN ('upload', 'preprocess', 'fingerprint', 'search', 'ai_detect', 'collect_evidence', 'reporting')),
        status TEXT NOT NULL CHECK (status IN ('Pending', 'Running', 'Paused', 'Cancelled', 'Completed', 'Failed')),
        depends_on_task_uuid TEXT,
        payload_json TEXT,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_sessions_status ON scan_sessions(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_session_tasks_status ON scan_session_tasks(session_id, status);")

    # 23. Asset Licenses Table for Sprint 8 Asset Intelligence
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asset_licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_id INTEGER NOT NULL,
        license_type TEXT NOT NULL CHECK(license_type IN ('Exclusive', 'Non-Exclusive', 'Creative Commons', 'Public Domain')),
        licensee_name TEXT,
        allowed_platforms TEXT,
        geo_exclusions TEXT,
        expires_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (original_id) REFERENCES originals(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_licenses_original ON asset_licenses(original_id);")

    # 24. Copyright Enforcement Takedown Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS takedown_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evidence_id INTEGER NOT NULL,
        recipient_platform TEXT NOT NULL,
        action_taken TEXT NOT NULL CHECK(action_taken IN ('DMCA Notice', 'Content Block', 'Ad Claim', 'Monetize')),
        status TEXT NOT NULL CHECK(status IN ('Draft', 'Sent', 'Acknowledged', 'Rejected', 'Resolved')),
        legal_signee TEXT,
        sent_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_takedown_logs_evidence ON takedown_logs(evidence_id);")

    # 24b. Notifications Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("SELECT COUNT(*) as cnt FROM notifications;")
    if cursor.fetchone()["cnt"] == 0:
        try:
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, is_read)
                VALUES 
                (1, 'System Update', 'Copyright Security system has been updated to Sprint 9 enterprise specs.', 0),
                (1, 'Initial Visual Scan Complete', 'Visual scan for YouTube URL completed with 0 matches found.', 1),
                (1, 'New Infringement Match', 'Warning: High visual similarity match (85.0%) detected on Facebook Reel!', 0);
            """)
        except Exception:
            pass

    # 25. Immutable Audit logs migration columns (Sprint 9)
    try:
        cursor.execute("ALTER TABLE audit_logs ADD COLUMN previous_entry_hash TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE audit_logs ADD COLUMN entry_hash TEXT;")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_audit_logs_chain
    AFTER INSERT ON audit_logs
    FOR EACH ROW
    WHEN NEW.entry_hash IS NULL
    BEGIN
        UPDATE audit_logs
        SET previous_entry_hash = COALESCE(
            (SELECT entry_hash FROM audit_logs WHERE id < NEW.id ORDER BY id DESC LIMIT 1),
            'GENESIS'
        ),
        entry_hash = compute_audit_hash(
            NEW.user_id, 
            NEW.action, 
            NEW.entity_type, 
            NEW.entity_id, 
            NEW.details_json,
            COALESCE((SELECT entry_hash FROM audit_logs WHERE id < NEW.id ORDER BY id DESC LIMIT 1), 'GENESIS'),
            COALESCE(NEW.created_at, CURRENT_TIMESTAMP)
        )
        WHERE id = NEW.id;
    END;
    """)

    conn.commit()
    conn.close()
    print("Database schema verified and initialized successfully at", DATABASE_PATH)

if __name__ == "__main__":
    init_db()
