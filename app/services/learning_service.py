"""
Service untuk auto-learn kata baru ke dictionary.

Fitur:
- Track kata yang tidak dikenali
- Auto-approve kalau muncul >= FREQUENCY_THRESHOLD kali
- Load learned words untuk dipakai dictionary_corrector
"""

from typing import List, Set, Optional
from datetime import datetime
import re


# Threshold: kata harus muncul minimal 5 kali untuk auto-approve
FREQUENCY_THRESHOLD = 5

# Minimum panjang kata untuk di-track
MIN_WORD_LENGTH = 3


class LearningService:
    """Service untuk manage auto-learning dictionary"""
    
    def __init__(self):
        self._learned_words_cache: Set[str] = set()
        self._cache_loaded = False
    
    def _get_db(self):
        """Get database connection dari db_service"""
        from app.services.db_service import db_service
        return db_service
    
    def _is_valid_word(self, word: str) -> bool:
        """Cek apakah kata valid untuk di-track"""
        if not word or len(word) < MIN_WORD_LENGTH:
            return False
        
        # Skip kalau ada angka
        if any(c.isdigit() for c in word):
            return False
        
        # Harus huruf semua (bisa ada - atau ')
        if not word.replace('-', '').replace("'", '').isalpha():
            return False
        
        return True
    
    def track_unknown_words(self, unknown_words: List[str]) -> int:
        """
        Track kata-kata yang tidak dikenali ke database.
        Return jumlah kata baru yang di-approve.
        """
        if not unknown_words:
            return 0
        
        db = self._get_db()
        newly_approved = 0
        
        with db._konek() as conn:
            for word in unknown_words:
                word_lower = word.lower().strip()
                
                if not self._is_valid_word(word_lower):
                    continue
                
                # Cek apakah kata sudah ada
                cursor = conn.execute(
                    "SELECT id, frequency, is_approved FROM learned_words WHERE word = ?",
                    (word_lower,)
                )
                row = cursor.fetchone()
                
                if row:
                    # Update frequency dan last_seen
                    new_freq = row['frequency'] + 1
                    is_approved = row['is_approved']
                    
                    # Auto-approve kalau mencapai threshold
                    if new_freq >= FREQUENCY_THRESHOLD and not is_approved:
                        conn.execute("""
                            UPDATE learned_words 
                            SET frequency = ?, last_seen = ?, is_approved = 1, approved_at = ?
                            WHERE id = ?
                        """, (new_freq, datetime.now().isoformat(), datetime.now().isoformat(), row['id']))
                        newly_approved += 1
                        print(f"[AUTO-LEARN] Kata '{word_lower}' approved! (freq={new_freq})")
                    else:
                        conn.execute("""
                            UPDATE learned_words 
                            SET frequency = ?, last_seen = ?
                            WHERE id = ?
                        """, (new_freq, datetime.now().isoformat(), row['id']))
                else:
                    # Insert kata baru
                    conn.execute("""
                        INSERT INTO learned_words (word, frequency, first_seen, last_seen)
                        VALUES (?, 1, ?, ?)
                    """, (word_lower, datetime.now().isoformat(), datetime.now().isoformat()))
                
            conn.commit()
        
        # Refresh cache kalau ada kata baru yang di-approve
        if newly_approved > 0:
            self._refresh_cache()
        
        return newly_approved
    
    def get_pending_words(self, limit: int = 50) -> List[dict]:
        """Ambil kata-kata yang belum di-approve"""
        db = self._get_db()
        
        with db._konek() as conn:
            cursor = conn.execute("""
                SELECT id, word, frequency, first_seen, last_seen
                FROM learned_words
                WHERE is_approved = 0
                ORDER BY frequency DESC, last_seen DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_approved_words(self) -> List[dict]:
        """Ambil kata-kata yang sudah di-approve"""
        db = self._get_db()
        
        with db._konek() as conn:
            cursor = conn.execute("""
                SELECT id, word, frequency, approved_at
                FROM learned_words
                WHERE is_approved = 1
                ORDER BY approved_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def approve_word(self, word: str) -> bool:
        """Approve kata secara manual"""
        db = self._get_db()
        word_lower = word.lower().strip()
        
        with db._konek() as conn:
            cursor = conn.execute("""
                UPDATE learned_words 
                SET is_approved = 1, approved_at = ?
                WHERE word = ? AND is_approved = 0
            """, (datetime.now().isoformat(), word_lower))
            conn.commit()
            
            if cursor.rowcount > 0:
                self._refresh_cache()
                return True
        return False
    
    def reject_word(self, word: str) -> bool:
        """Hapus kata dari tracking"""
        db = self._get_db()
        word_lower = word.lower().strip()
        
        with db._konek() as conn:
            cursor = conn.execute(
                "DELETE FROM learned_words WHERE word = ?",
                (word_lower,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_learned_words(self) -> Set[str]:
        """
        Ambil semua kata yang sudah di-approve.
        Pakai cache untuk performa.
        """
        if not self._cache_loaded:
            self._refresh_cache()
        return self._learned_words_cache.copy()
    
    def _refresh_cache(self):
        """Refresh cache learned words dari database"""
        db = self._get_db()
        
        with db._konek() as conn:
            cursor = conn.execute(
                "SELECT word FROM learned_words WHERE is_approved = 1"
            )
            self._learned_words_cache = {row['word'] for row in cursor.fetchall()}
            self._cache_loaded = True
    
    def get_stats(self) -> dict:
        """Ambil statistik learning"""
        db = self._get_db()
        
        with db._konek() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_tracked,
                    SUM(CASE WHEN is_approved = 1 THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END) as pending
                FROM learned_words
            """)
            row = cursor.fetchone()
            return {
                "total_tracked": row[0] or 0,
                "approved": row[1] or 0,
                "pending": row[2] or 0,
                "threshold": FREQUENCY_THRESHOLD
            }


# Singleton instance
learning_service = LearningService()
