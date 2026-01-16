"""
Audit Logger Service untuk tracking aksi sensitif.
Requirement untuk compliance instansi pemerintah.
"""

from datetime import datetime
from typing import Optional
import json


class AuditLogger:
    """
    Service untuk mencatat audit log aksi sensitif.
    Logs disimpan di database untuk compliance dan forensik.
    """
    
    # Event types untuk kategorisasi
    EVENT_API_KEY_CREATED = "API_KEY_CREATED"
    EVENT_API_KEY_REVOKED = "API_KEY_REVOKED"
    EVENT_WORDS_IMPORTED = "WORDS_IMPORTED"
    EVENT_WORDS_EXPORTED = "WORDS_EXPORTED"
    EVENT_WORD_APPROVED = "WORD_APPROVED"
    EVENT_WORD_REJECTED = "WORD_REJECTED"
    EVENT_AUTH_FAILED = "AUTH_FAILED"
    EVENT_RATE_LIMITED = "RATE_LIMITED"
    
    def __init__(self):
        self._ensure_table()
    
    def _get_db(self):
        """Get database connection dari db_service"""
        from app.services.db_service import db_service
        return db_service
    
    def _ensure_table(self):
        """Buat tabel audit_logs kalau belum ada"""
        db = self._get_db()
        with db._konek() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    actor TEXT,
                    ip_address TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Index untuk query cepat
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type 
                ON audit_logs(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at 
                ON audit_logs(created_at)
            """)
            conn.commit()
    
    def log(
        self, 
        event_type: str, 
        actor: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """
        Catat audit log.
        
        Args:
            event_type: Tipe event (pakai konstanta EVENT_*)
            actor: API key prefix atau identifier pelaku
            ip_address: IP address request
            details: Dictionary berisi detail tambahan
        """
        db = self._get_db()
        details_json = json.dumps(details) if details else None
        
        with db._konek() as conn:
            conn.execute("""
                INSERT INTO audit_logs (event_type, actor, ip_address, details)
                VALUES (?, ?, ?, ?)
            """, (event_type, actor, ip_address, details_json))
            conn.commit()
    
    def get_logs(
        self, 
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """Ambil audit logs dengan filter opsional"""
        db = self._get_db()
        
        with db._konek() as conn:
            if event_type:
                cursor = conn.execute("""
                    SELECT id, event_type, actor, ip_address, details, created_at
                    FROM audit_logs
                    WHERE event_type = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (event_type, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT id, event_type, actor, ip_address, details, created_at
                    FROM audit_logs
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            logs = []
            for row in cursor.fetchall():
                log_entry = dict(row)
                # Parse JSON details
                if log_entry.get('details'):
                    try:
                        log_entry['details'] = json.loads(log_entry['details'])
                    except:
                        pass
                logs.append(log_entry)
            
            return logs
    
    def get_stats(self) -> dict:
        """Ambil statistik audit logs"""
        db = self._get_db()
        
        with db._konek() as conn:
            cursor = conn.execute("""
                SELECT 
                    event_type,
                    COUNT(*) as count
                FROM audit_logs
                GROUP BY event_type
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row['event_type']] = row['count']
            
            # Total
            cursor = conn.execute("SELECT COUNT(*) FROM audit_logs")
            stats['total'] = cursor.fetchone()[0]
            
            return stats


# Singleton instance
audit_logger = AuditLogger()
