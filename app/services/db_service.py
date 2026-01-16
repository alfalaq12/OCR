"""
Database service pake SQLite.
Nyimpen history OCR dan manage API keys.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager
import secrets
import hashlib
import os


class DatabaseService:
    """Handle semua operasi database - history OCR dan API keys"""

    def __init__(self, db_path: str = None):
        # Default: gunakan data directory untuk Docker, atau local untuk development
        if db_path is None:
            data_dir = os.environ.get("DATA_DIR", "data")
            # Buat direktori jika belum ada
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "ocr_history.db")
        self.db_path = db_path
        self._setup_tabel()

    def _setup_tabel(self):
        """Bikin tabel kalo belum ada"""
        with self._konek() as conn:
            # tabel buat nyimpen history request OCR
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ocr_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    pages INTEGER DEFAULT 1,
                    language TEXT DEFAULT 'mixed',
                    processing_time_ms INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 1,
                    error_message TEXT,
                    error_code TEXT,
                    text_preview TEXT,
                    api_key TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # tabel buat manage API keys
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT UNIQUE NOT NULL,
                    key_prefix TEXT NOT NULL,
                    name TEXT NOT NULL,
                    is_admin INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    requests_count INTEGER DEFAULT 0,
                    last_used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    revoked_at TIMESTAMP
                )
            """)
            
            # tabel buat auto-learn dictionary
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learned_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    is_approved INTEGER DEFAULT 0,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP
                )
            """)
            conn.commit()

    @contextmanager
    def _konek(self):
        """Buka koneksi database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _hash_key(self, key: str) -> str:
        """Hash API key biar aman disimpen"""
        return hashlib.sha256(key.encode()).hexdigest()

    # ==================== API Key Management ====================

    def bikin_api_key(self, nama: str, is_admin: bool = False) -> dict:
        """Generate API key baru"""
        # format: sk-ocr-{random 32 karakter}
        random_part = secrets.token_hex(16)
        full_key = f"sk-ocr-{random_part}"
        key_prefix = f"sk-ocr-{random_part[:8]}..."
        key_hash = self._hash_key(full_key)

        with self._konek() as conn:
            cursor = conn.execute("""
                INSERT INTO api_keys (key_hash, key_prefix, name, is_admin)
                VALUES (?, ?, ?, ?)
            """, (key_hash, key_prefix, nama, 1 if is_admin else 0))
            conn.commit()

            return {
                "id": cursor.lastrowid,
                "key": full_key,  # cuma dikasih sekali ini!
                "key_prefix": key_prefix,
                "name": nama,
                "is_admin": is_admin,
                "message": "Simpen key ini baik-baik, gak akan ditampilin lagi!"
            }

    def validasi_api_key(self, key: str) -> Optional[dict]:
        """Cek apakah API key valid"""
        key_hash = self._hash_key(key)

        with self._konek() as conn:
            cursor = conn.execute("""
                SELECT id, key_prefix, name, is_admin, is_active
                FROM api_keys
                WHERE key_hash = ? AND is_active = 1
            """, (key_hash,))
            row = cursor.fetchone()

            if row:
                # update statistik pemakaian
                conn.execute("""
                    UPDATE api_keys 
                    SET requests_count = requests_count + 1, last_used_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), row["id"]))
                conn.commit()

                return {
                    "id": row["id"],
                    "key_prefix": row["key_prefix"],
                    "name": row["name"],
                    "is_admin": bool(row["is_admin"]),
                    "is_active": bool(row["is_active"])
                }
        return None

    def cek_admin_key(self, key: str) -> bool:
        """Cek apakah key ini punya akses admin"""
        info = self.validasi_api_key(key)
        return info is not None and info.get("is_admin", False)

    def list_api_keys(self) -> List[dict]:
        """Ambil semua API keys (tanpa key aslinya)"""
        with self._konek() as conn:
            cursor = conn.execute("""
                SELECT id, key_prefix, name, is_admin, is_active, 
                       requests_count, last_used_at, created_at, revoked_at
                FROM api_keys
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def cabut_api_key(self, key_id: int) -> bool:
        """Nonaktifkan API key"""
        with self._konek() as conn:
            cursor = conn.execute("""
                UPDATE api_keys 
                SET is_active = 0, revoked_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), key_id))
            conn.commit()
            return cursor.rowcount > 0

    def stats_api_key(self) -> dict:
        """Ambil statistik API keys"""
        with self._konek() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_keys,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_keys,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as revoked_keys,
                    SUM(requests_count) as total_requests
                FROM api_keys
            """)
            row = cursor.fetchone()
            return {
                "total_keys": row[0] or 0,
                "active_keys": row[1] or 0,
                "revoked_keys": row[2] or 0,
                "total_requests": row[3] or 0
            }

    # ==================== History OCR ====================

    def catat_request(
        self,
        filename: str,
        file_size: int,
        pages: int,
        language: str,
        processing_time_ms: int,
        success: bool,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        text_preview: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> int:
        """Catat request OCR ke database"""
        with self._konek() as conn:
            cursor = conn.execute("""
                INSERT INTO ocr_history 
                (filename, file_size, pages, language, processing_time_ms, 
                 success, error_message, error_code, text_preview, api_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                filename, file_size, pages, language, processing_time_ms,
                1 if success else 0, error_message, error_code,
                text_preview[:500] if text_preview else None,
                api_key
            ))
            conn.commit()
            return cursor.lastrowid

    def ambil_history(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """Ambil history dengan pagination"""
        with self._konek() as conn:
            cursor = conn.execute("""
                SELECT id, filename, file_size, pages, language, 
                       processing_time_ms, success, error_message, created_at
                FROM ocr_history
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def hitung_total(self) -> int:
        """Hitung total record history"""
        with self._konek() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM ocr_history")
            return cursor.fetchone()[0]

    def ambil_stats(self) -> dict:
        """Ambil statistik OCR"""
        with self._konek() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    AVG(processing_time_ms) as avg_processing_time,
                    SUM(pages) as total_pages_processed
                FROM ocr_history
            """)
            row = cursor.fetchone()
            return {
                "total_requests": row[0] or 0,
                "successful": row[1] or 0,
                "failed": row[2] or 0,
                "avg_processing_time_ms": round(row[3] or 0, 2),
                "total_pages_processed": row[4] or 0
            }

    # alias buat backward compatibility
    def generate_api_key(self, name, is_admin=False):
        return self.bikin_api_key(name, is_admin)
    
    def validate_api_key(self, key):
        return self.validasi_api_key(key)
    
    def is_admin_key(self, key):
        return self.cek_admin_key(key)
    
    def revoke_api_key(self, key_id):
        return self.cabut_api_key(key_id)
    
    def get_api_key_stats(self):
        return self.stats_api_key()
    
    def log_request(self, **kwargs):
        return self.catat_request(**kwargs)
    
    def get_history(self, limit=50, offset=0):
        return self.ambil_history(limit, offset)
    
    def get_total_count(self):
        return self.hitung_total()
    
    def get_stats(self):
        return self.ambil_stats()


# singleton
db_service = DatabaseService()
