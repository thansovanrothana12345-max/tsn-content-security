# Database Design

The platform utilizes a local SQLite database engine stored at `storage/database.db`.

---

## 1. SQLite Relational Schema

### A. Users Table
*   **Purpose**: Log credentials and user roles.
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Admin', 'Editor', 'Reviewer', 'Guest')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### B. Sessions Table
*   **Purpose**: Store active user session tokens.
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### C. Cases Table
*   **Purpose**: Log case folders.
```sql
CREATE TABLE cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(title) > 0),
    description TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Resolved', 'Closed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### D. Originals Table
*   **Purpose**: Log original reference files.
```sql
CREATE TABLE originals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    file_uuid TEXT NOT NULL UNIQUE,
    storage_provider TEXT NOT NULL CHECK (storage_provider IN ('local', 's3', 'r2')),
    filesize INTEGER NOT NULL CHECK (filesize > 0),
    duration REAL NOT NULL CHECK (duration >= 0.0),
    fingerprint_json TEXT, -- Serialized visual/acoustic fingerprint sequence
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);
```

### E. Evidence Table
*   **Purpose**: Log infringing leak matches.
```sql
CREATE TABLE evidence (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);
```

---

## 2. Index Configurations
```sql
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_originals_case ON originals(case_id);
CREATE INDEX idx_evidence_case ON evidence(case_id);
CREATE INDEX idx_evidence_similarity ON evidence(similarity_score);
```
