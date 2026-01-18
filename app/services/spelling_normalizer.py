"""
Modul untuk normalisasi ejaan lama Indonesia ke ejaan modern (EYD).
Ringan - pure regex tanpa dependency tambahan.

Ejaan yang di-convert:
- Van Ophuijsen (1901-1947): oe → u
- Soewandi (1947-1972): dj, tj, nj, sj, ch, j → j, c, ny, sy, kh, y
"""

import re
from typing import Tuple


# Whitelist kata asing yang TIDAK boleh dikonversi
# Tambahkan kata-kata asing yang sering muncul di dokumen
KATA_ASING = {
    # English words
    "project", "object", "subject", "inject", "reject", "eject",
    "adjacent", "trajectory", "objective", "subjective", "projection",
    "adjective", "conjunction", "injection", "objection", "rejection",
    "adjustment", "major", "junior", "senior",
    # Dutch words (sering di dokumen kolonial)
    "adjunct", "project", "object",
    # Kata modern yang mengandung polab ejaan lama tapi sudah benar (biar gak rusak)
    "penunjukan", "tunjuk", "panjang", "janji", "banjir", "manja",
    # Nama-nama umum yang pakai ejaan lama (optional, bisa di-skip)
}

# Rules konversi - URUTAN PENTING! 
# Proses digraph (2 huruf) dulu sebelum single letter
RULES_EJAAN = [
    # Digraphs harus diproses duluan
    (r'oe', 'u'),      # oetara → utara
    (r'dj', 'j'),      # djalan → jalan
    (r'tj', 'c'),      # tjari → cari
    (r'nj', 'ny'),     # njamuk → nyamuk
    (r'sj', 'sy'),     # sjarat → syarat
    (r'ch', 'kh'),     # chabar → khabar
    # Single letter j → y (hanya di awal kata atau setelah spasi/newline)
    # Ini tricky - "jang" → "yang", tapi "manja" tetap "manja"
]

# Pattern untuk "j" di awal kata yang harus jadi "y"
# Kata-kata umum yang j-nya harus jadi y
KATA_J_KE_Y = {
    "jang": "yang",
    "jangan": "jangan",  # ini tetap j
    "ja": "ya",
    "jaitu": "yaitu",
    "jaitoe": "yaitu",
}


def is_kata_asing(kata: str) -> bool:
    """Cek apakah kata termasuk kata asing yang di-skip"""
    return kata.lower() in KATA_ASING


def normalize_kata(kata: str) -> str:
    """
    Normalize satu kata dari ejaan lama ke modern.
    Skip kata asing.
    """
    if is_kata_asing(kata):
        return kata
    
    hasil = kata
    
    # Cek dulu kata-kata khusus j → y
    kata_lower = kata.lower()
    if kata_lower in KATA_J_KE_Y:
        replacement = KATA_J_KE_Y[kata_lower]
        # Pertahankan kapitalisasi asli
        if kata[0].isupper():
            replacement = replacement.capitalize()
        return replacement
    
    # Apply rules secara berurutan
    for pattern, replacement in RULES_EJAAN:
        # Case insensitive replacement yang preserve case
        hasil = _replace_preserve_case(hasil, pattern, replacement)
    
    return hasil


def _replace_preserve_case(text: str, pattern: str, replacement: str) -> str:
    """
    Replace pattern dengan preserve case asli.
    Contoh: "OE" → "U", "Oe" → "U", "oe" → "u"
    """
    def replacer(match):
        matched = match.group(0)
        if matched.isupper():
            return replacement.upper()
        elif matched[0].isupper():
            return replacement.capitalize()
        else:
            return replacement
    
    return re.sub(pattern, replacer, text, flags=re.IGNORECASE)


def normalize_text(text: str) -> str:
    """
    Normalize seluruh teks dari ejaan lama ke modern.
    
    Args:
        text: Teks hasil OCR dengan ejaan lama
        
    Returns:
        Teks dengan ejaan modern (EYD)
    """
    if not text:
        return text
    
    # Split jadi kata-kata, normalize masing-masing, gabung lagi
    # Pakai regex untuk preserve whitespace dan punctuation
    
    # Pattern untuk split: pisahkan kata dari non-kata
    tokens = re.findall(r'\S+|\s+', text)
    
    hasil = []
    for token in tokens:
        if token.strip():  # Ini kata
            hasil.append(normalize_kata(token))
        else:  # Ini whitespace
            hasil.append(token)
    
    return ''.join(hasil)


def normalize_with_comparison(text: str) -> Tuple[str, str, int]:
    """
    Normalize teks dan return perbandingan.
    
    Args:
        text: Teks asli hasil OCR
        
    Returns:
        Tuple (teks_asli, teks_normalized, jumlah_perubahan)
    """
    if not text:
        return text, text, 0
    
    normalized = normalize_text(text)
    
    # Hitung berapa kata yang berubah
    original_words = text.split()
    normalized_words = normalized.split()
    
    changes = sum(1 for o, n in zip(original_words, normalized_words) if o != n)
    
    return text, normalized, changes


# Quick test
if __name__ == "__main__":
    test_cases = [
        "Oetara adalah arah jang penting",
        "Djalan ini menoedju ke pasar",
        "Tjari barang di toko itoe",
        "Njamuk sangat mengganggu",
        "Sjarat utama adalah kedjujoeran",
        "Chabar baik dari project manager",  # project harus tetap
    ]
    
    print("=== Test Normalisasi Ejaan ===\n")
    for text in test_cases:
        original, normalized, changes = normalize_with_comparison(text)
        print(f"Asli     : {original}")
        print(f"Normal   : {normalized}")
        print(f"Perubahan: {changes} kata\n")
