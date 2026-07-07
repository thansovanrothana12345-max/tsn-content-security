import sqlite3
import time
import json
import logging
from backend.database import get_db_connection
from backend.config import Config

logger = logging.getLogger("tsn.cache")

class DetectionCache:
    def __init__(self, use_memory: bool = True, use_db: bool = True):
        self.use_memory = use_memory
        self.use_db = use_db
        self.memory_cache = {} # key -> (value, expires_at)
        
        if self.use_db:
            self._init_db_table()

    def _init_db_table(self):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detection_cache (
                    cache_key TEXT PRIMARY KEY,
                    cache_value TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expiry ON detection_cache(expires_at);")
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite detection_cache table: {e}")
        finally:
            conn.close()

    def get(self, key: str) -> str:
        """Retrieves a cached value for the given key if not expired."""
        now = time.time()
        
        # 1. Check in-memory cache
        if self.use_memory and key in self.memory_cache:
            val, expires_at = self.memory_cache[key]
            if expires_at > now:
                logger.info(f"Cache HIT (memory) for key: {key}")
                return val
            else:
                del self.memory_cache[key]

        # 2. Check SQLite persistent cache
        if self.use_db:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT cache_value, expires_at FROM detection_cache WHERE cache_key = ?;",
                    (key,)
                )
                row = cursor.fetchone()
                if row:
                    val = row["cache_value"] if isinstance(row, sqlite3.Row) else row[0]
                    expires_at = row["expires_at"] if isinstance(row, sqlite3.Row) else row[1]
                    if expires_at > now:
                        logger.info(f"Cache HIT (database) for key: {key}")
                        if self.use_memory:
                            self.memory_cache[key] = (val, expires_at)
                        return val
                    else:
                        cursor.execute("DELETE FROM detection_cache WHERE cache_key = ?;", (key,))
                        conn.commit()
            except Exception as e:
                logger.error(f"Error querying SQLite cache: {e}")
            finally:
                conn.close()

        logger.info(f"Cache MISS for key: {key}")
        return None

    def set(self, key: str, value: str, ttl_seconds: int = None) -> None:
        """Saves a value in the cache with a designated TTL."""
        if ttl_seconds is None:
            # Default to 30 days
            ttl_seconds = int(getattr(Config, "DETECTION_CACHE_TTL", 30 * 24 * 3600))
            
        expires_at = time.time() + ttl_seconds
        
        # 1. Save in memory
        if self.use_memory:
            self.memory_cache[key] = (value, expires_at)

        # 2. Save in SQLite db
        if self.use_db:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO detection_cache (cache_key, cache_value, expires_at)
                    VALUES (?, ?, ?);
                """, (key, value, expires_at))
                conn.commit()
            except Exception as e:
                logger.error(f"Error writing to SQLite cache: {e}")
            finally:
                conn.close()

    def clear(self):
        """Clears both memory and DB caches."""
        if self.use_memory:
            self.memory_cache.clear()
        if self.use_db:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM detection_cache;")
                conn.commit()
            except Exception as e:
                logger.error(f"Error clearing cache table: {e}")
            finally:
                conn.close()
