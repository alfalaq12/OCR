"""
Modul untuk koreksi hasil OCR menggunakan kamus Indonesia.
Menggunakan fuzzy matching untuk koreksi kata yang mirip.

Fitur:
- Kamus kata Indonesia umum + istilah dokumen resmi
- Fuzzy matching dengan threshold similarity 80%
- Skip kata pendek (<3 huruf), angka, dan simbol
"""

from typing import Tuple, Optional
import re

# Coba import rapidfuzz untuk fuzzy matching yang cepat
try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    print("⚠️ rapidfuzz tidak tersedia, dictionary correction dinonaktifkan")


# ============================================================================
# KAMUS KATA INDONESIA
# Tambahkan kata-kata yang sering muncul di dokumen resmi/lama
# ============================================================================

KAMUS_DOKUMEN = {
    # Instansi Pemerintah
    "departemen", "kementerian", "direktorat", "dirjen", "badan", "lembaga",
    "kantor", "dinas", "pusat", "cabang", "wilayah", "jawatan", "djawatan",
    "sekretariat", "inspektorat", "biro", "bagian", "subbagian", "seksi",
    
    # Bidang Pekerjaan Pemerintah
    "pekerjaan", "umum", "tenaga", "kerja", "keuangan", "pendidikan",
    "kesehatan", "pertanian", "perhubungan", "perindustrian", "kebudayaan",
    "perdagangan", "sosial", "agama", "dalam", "negeri", "luar", "hankam",
    "pertahanan", "keamanan", "kehakiman", "penerangan", "transmigrasi",
    
    # Dokumen & Surat Resmi
    "surat", "keputusan", "keterangan", "peraturan", "undang", "penetapan",
    "nomor", "tanggal", "perihal", "lampiran", "tembusan", "petikan",
    "ditandatangani", "ditetapkan", "menimbang", "mengingat", "memutuskan",
    "menetapkan", "memperhatikan", "membaca", "mendengar", "menyatakan",
    "pertama", "kedua", "ketiga", "keempat", "kelima", "keenam",
    "halaman", "pasal", "ayat", "butir", "huruf", "angka",
    
    # Jabatan
    "direktur", "kepala", "wakil", "sekretaris", "bendahara", "ketua",
    "pegawai", "karyawan", "staf", "pejabat", "menteri", "presiden",
    "gubernur", "bupati", "walikota", "camat", "lurah", "wedana",
    "asisten", "ajudan", "inspektur", "komisaris", "administrator",
    "pangkat", "golongan", "ruang", "tingkat", "eselon",
    
    # Tempat & Alamat
    "jalan", "gedung", "kantor", "rumah", "negara", "daerah", "kramat",
    "jakarta", "bandung", "surabaya", "semarang", "yogyakarta", "medan",
    "palembang", "makassar", "manado", "denpasar", "pontianak", "banjarmasin",
    "provinsi", "kabupaten", "kecamatan", "kelurahan", "desa", "kampung",
    "blok", "nomor", "lantai", "tingkat", "gang", "lorong", "kompleks",
    "timur", "barat", "utara", "selatan", "tengah", "pusat",
    
    # Pulau & Wilayah
    "jawa", "sumatra", "sumatera", "kalimantan", "sulawesi", "papua",
    "bali", "nusa", "tenggara", "maluku", "irian", "borneo",
    
    # Keuangan & Gaji
    "gaji", "tunjangan", "pokok", "rupiah", "pembayaran", "honorarium",
    "anggaran", "belanja", "pendapatan", "pajak", "iuran", "pungutan",
    "sewa", "sebulan", "setahun", "bulanan", "tahunan", "cicilan",
    
    # Waktu & Bulan
    "januari", "februari", "maret", "april", "mei", "juni",
    "juli", "agustus", "september", "oktober", "november", "desember",
    "nopember", "pebruari", "djanuari", "agustus",
    "tahun", "bulan", "hari", "tanggal", "mulai", "sampai", "berakhir",
    "minggu", "senin", "selasa", "rabu", "kamis", "jumat", "sabtu",
    
    # Status & Keterangan
    "berlaku", "tidak", "sudah", "belum", "dapat", "harus", "bersangkutan",
    "wajib", "sesuai", "berdasarkan", "sebagaimana", "tersebut", "terlampir",
    "dibawah", "diatas", "berikut", "demikian", "bahwa", "agar", "supaya",
    "setelah", "ditinggalkan", "ditempati", "dihuni", "digunakan",
    
    # Keluarga & Kependudukan
    "nama", "umur", "jenis", "kelamin", "laki", "perempuan", "wanita", "pria",
    "istri", "suami", "anak", "ayah", "ibu", "kakak", "adik", "nenek", "kakek",
    "lahir", "tempat", "tanggal", "alamat", "pekerjaan", "agama", "bangsa",
    "penghuni", "anggota", "keluarga", "orang", "jiwa",
    
    # Properti & Rumah
    "rumah", "tanah", "bangunan", "pekarangan", "persil", "kavling",
    "tinggal", "tempat", "lama", "baru", "luas", "meter", "persegi",
    "kamar", "ruang", "dapur", "kamar mandi", "garasi", "teras",
    
    # Kata Kerja Umum
    "menyetujui", "menyerahkan", "menerima", "mengajukan", "memohon",
    "memberikan", "menunjuk", "mengangkat", "memberhentikan", "memindahkan",
    "menghuni", "mendirikan", "membangun", "memperbaiki", "merawat",
    
    # Kata Sambung & Preposisi
    "yang", "dan", "atau", "untuk", "dari", "dengan", "pada", "oleh",
    "ini", "itu", "adalah", "sebagai", "kepada", "terhadap", "tentang",
    "dalam", "luar", "atas", "bawah", "sebelum", "sesudah", "antara",
    "akan", "telah", "sedang", "masih", "juga", "serta", "maupun",
    
    # Kata Sifat
    "besar", "kecil", "tinggi", "rendah", "panjang", "pendek", "lebar",
    "baru", "lama", "tua", "muda", "baik", "buruk", "benar", "salah",
    
    # Dokumen Khusus Rumah Negara
    "penunjukan", "penghunian", "penggunaan", "pemeliharaan", "penyerahan",
    "hak", "kewajiban", "syarat", "ketentuan", "larangan", "sanksi",
    
    # Istilah Pemerintahan Lama (ejaan "dj" dan lainnya)
    "djawatan", "djakarta", "djasa", "djuru", "adjudan", "ajudan",
    "djalan", "djl", "djend", "djenderal", "djoeragan",
    "wedana", "demang", "mantri", "djuru tulis", "djuru bayar",
    "persewaan", "perowaan", "rumah dinas", "rumah negara",
    "angka", "pnid", "kartu", "tjap", "stempel", "meterai",
    "gouvernement", "resident", "regentschap", "afdeeling",
    
    # Dokumen Kolonial/Lama
    "staatblad", "bijblad", "besluit", "resolutie", "ordonnantie",
    "burgerlijke", "stand", "akta", "akte", "salinan", "turunan",
}

# Kata-kata dengan kapitalisasi khusus (akan dipertahankan uppercase)
KATA_UPPERCASE = {
    "departemen", "kementerian", "direktorat", "republik", "indonesia",
    "jakarta", "bandung", "surabaya", "jawa", "sumatra", "kalimantan",
    "sulawesi", "papua", "bali", "maluku", "presiden", "menteri",
    "djakarta", "djawa", "nusa", "tenggara", "denpasar",
}


# ============================================================================
# NAMA-NAMA INDONESIA
# Nama umum yang sering muncul di dokumen lama
# ============================================================================

NAMA_INDONESIA = {
    # Nama Laki-laki Umum
    "sujono", "suparman", "hartono", "bambang", "joko", "budi", "agus",
    "ahmad", "muhammad", "mohamad", "moh", "abdul", "ali", "hasan", "umar",
    "udin", "didi", "dede", "asep", "ujang", "yanto", "sugeng", "sutrisno",
    "supardi", "suradi", "sudirman", "sudarno", "sukardi", "suharto",
    "sukarno", "slamet", "rosidi", "ridwan", "rahman", "pudjo", "parto",
    "parman", "paijo", "ngadiman", "ngadino", "mulyono", "mulyo", "karno",
    "kardi", "kamto", "darmo", "darmono", "cipto", "ciptono", "bejo",
    "harjo", "harjono", "wongso", "kasno", "kasiman", "kasman",
    
    # Nama Perempuan Umum
    "ngatirah", "kasminem", "sriati", "sriyati", "sri", "siti", "dewi",
    "ratna", "yanti", "kartini", "aminah", "fatimah", "aisha", "aisyah",
    "nurhaliza", "sumiati", "sumirah", "sumini", "suparni", "supami",
    "tuminah", "tumini", "waginah", "waginem", "warsinah", "warsini",
    "parmi", "parmini", "parminah", "sarmi", "sarmini", "sarminah",
    "lastri", "lestari", "kasmirah", "kasmini", "kasminah", "wagiyem",
    "wagirah", "sutinah", "sutini", "sutinem", "ngatini", "ngatinem",
    "rubiyah", "rubiyem", "satinem", "satinah", "tumiyem", "marni",
    
    # Prefix/Title Nama
    "ng", "raden", "rd", "mas", "mbak", "nyi", "ki", "haji", "hajjah",
    "hadji", "hadjah", "tuan", "nyonya", "nona", "rr", "krt", "kra",
    "roro", "gusti", "andi", "daeng", "oei", "tan", "liem", "kwee",
    
    # Nama Keluarga/Marga
    "prawirodirjo", "prawiro", "mangku", "mangkunegara", "paku", "pakubuwono",
    "hamengku", "hamengkubuwono", "sosro", "sosrodiningrat", "gondokusumo",
}

# Gabungkan nama ke kamus untuk fuzzy matching
KAMUS_DOKUMEN.update(NAMA_INDONESIA)


# ============================================================================
# PHRASE CORRECTIONS
# Koreksi frasa yang sering salah dibaca OCR
# Format: "frasa_salah": "frasa_benar"
# ============================================================================

PHRASE_CORRECTIONS = {
    # Header dokumen yang sering salah - DEPARTEMEN
    "departntn": "departemen",
    "departtmen": "departemen",
    "departnen": "departemen",
    "departmon": "departemen",
    "departomon": "departemen",
    "depatemen": "departemen",
    "dopartemen": "departemen",
    "departemn": "departemen",
    "deprtemen": "departemen",
    "dpartemen": "departemen",
    "departemem": "departemen",
    "departnen": "departemen",
    
    # PEKERJAAN UMUM
    "pcaai": "pekerjaan",
    "pkaai": "pekerjaan",
    "pkerjaan": "pekerjaan",
    "pekrjaan": "pekerjaan",
    "pekerjan": "pekerjaan",
    "ptsyaai": "pekerjaan",
    "pekerjaa": "pekerjaan",
    "pokerjan": "pekerjaan",
    "pckerjaan": "pekerjaan",
    "pekcrjaan": "pekerjaan",
    
    # Combined header errors
    "departntnptsyaai": "departemen pekerjaan umum",
    "departntnpcaai": "departemen pekerjaan umum",
    "departomenpekerjaan": "departemen pekerjaan umum",
    
    # PUSAT DJAWATAN GEDUNG NEGARA
    "camat": "djawatan",
    "caagtcigara": "gedung negara",
    "tenggara": "gedung negara",
    "pusatcaagtcigara": "pusat djawatan gedung negara",
    "pusat camat tenggara": "pusat djawatan gedung negara",
    
    # Instansi
    "djawaton": "djawatan",
    "djawuten": "djawatan",
    "djwatan": "djawatan",
    "gecung": "gedung",
    "gedun": "gedung",
    "gsdung": "gedung",
    "negera": "negara",
    "nogara": "negara",
    "negora": "negara",
    "nfg": "negara",
    "ngara": "negara",
    
    # KETERANGAN PENUNDJUKAN
    "kantor angka": "keterangan",
    "angka penunjukan": "penundjukan",
    "penunjukan": "penundjukan",
    
    # Alamat
    "jkrtn": "jakarta",
    "jakrta": "jakarta",
    "jakart": "jakarta",
    "djakrta": "djakarta",
    "krmet": "kramat",
    "kramet": "kramat",
    
    # Format Tanggal Lama
    "tgl": "tanggal",
    "bln": "bulan",
    "thn": "tahun",
    "th": "tahun",
    
    # Bulan - ejaan lama & OCR errors
    "djanuari": "januari",
    "danuari": "januari",
    "djanu": "januari",
    "pebruari": "februari",
    "peb": "februari",
    "febr": "februari",
    "mrt": "maret",
    "aprl": "april",
    "djuni": "juni",
    "djuli": "juli",
    "agustoes": "agustus",
    "agsts": "agustus",
    "nopember": "november",
    "noombo": "november",
    "nopmber": "november",
    "novmber": "november",
    "nov": "november",
    "desemb": "desember",
    "dec": "desember",
    
    # Kata-kata umum yang sering error
    "ketarangan": "keterangan",
    "ketrangan": "keterangan",
    "keterangn": "keterangan",
    "berllaku": "berlaku",
    "berlku": "berlaku",
    "bercgser": "bergesar",
    
    # Properti & Rumah
    "rmah": "rumah",
    "runh": "rumah",
    "rumh": "rumah",
    "tmpat": "tempat",
    "tempt": "tempat",
    "tompt": "tempat",
    "tinga1": "tinggal",
    "tingal": "tinggal",
    
    # Kata kerja
    "citinggal": "ditinggalkan",
    "ditinggal": "ditinggalkan",
    "ditempti": "ditempati",
    "ditempatl": "ditempati",
    "monciri": "menghuni",
    "menciri": "menghuni",
    
    # Jabatan
    "kpala": "kepala",
    "kepal": "kepala",
    "direkur": "direktur",
    "direktr": "direktur",
    "gicn": "bagian",
    
    # Keuangan
    "gadji": "gaji",
    "pokol": "pokok",
    "seblan": "sebulan",
    "sbulan": "sebulan",
    
    # Keluarga
    "histri": "istri",
    "istr": "istri",
    "suam": "suami",
    "ank": "anak",
    "anaks": "anak",
    "tanaks": "anak",
    "kakeks": "kakak",
    
    # Dokumen
    "halman": "halaman",
    "halamn": "halaman",
    "nomoa": "nomor",
    "nomr": "nomor",
    "srat": "surat",
    "surt": "surat",
    "katp": "kartu",
    "pnid": "penunjukan identitas",
    
    # OCR Errors Umum (dari sample user)
    "mastoreoicig": "maryorejo",
    "kotaoran": "kotamadya",
    "persowaan": "persewaan",
}


def _is_valid_word(kata: str) -> bool:
    """
    Cek apakah kata valid untuk dikoreksi.
    Skip: kata pendek, angka, simbol, kata dengan titik/tanda baca
    """
    if not kata or len(kata) < 3:
        return False
    
    # Skip jika mengandung angka
    if any(c.isdigit() for c in kata):
        return False
    
    # Skip jika bukan huruf semua
    if not kata.replace('-', '').replace("'", '').isalpha():
        return False
    
    return True


def _find_best_match(kata: str, threshold: int = 65) -> Optional[str]:
    """
    Cari kata terdekat dari kamus menggunakan fuzzy matching.
    
    Args:
        kata: Kata yang akan dikoreksi
        threshold: Minimum similarity score (0-100)
    
    Returns:
        Kata yang dikoreksi atau None jika tidak ditemukan
    """
    if not HAS_RAPIDFUZZ:
        return None
    
    kata_lower = kata.lower()
    
    # Jika kata sudah ada di kamus, return langsung
    if kata_lower in KAMUS_DOKUMEN:
        return None  # Tidak perlu koreksi
    
    # Cari match terbaik
    result = process.extractOne(
        kata_lower,
        KAMUS_DOKUMEN,
        scorer=fuzz.ratio,
        score_cutoff=threshold
    )
    
    if result:
        match, score, _ = result
        # Pertahankan kapitalisasi asli
        if kata.isupper():
            return match.upper()
        elif kata[0].isupper():
            return match.capitalize()
        else:
            return match
    
    return None


def correct_word(kata: str) -> str:
    """
    Koreksi satu kata menggunakan phrase corrections dan kamus.
    
    Args:
        kata: Kata asli dari OCR
        
    Returns:
        Kata yang sudah dikoreksi, atau kata asli jika tidak perlu koreksi
    """
    if not kata:
        return kata
    
    kata_lower = kata.lower()
    
    # Step 1: Cek phrase corrections dulu (exact match)
    if kata_lower in PHRASE_CORRECTIONS:
        corrected = PHRASE_CORRECTIONS[kata_lower]
        # Pertahankan kapitalisasi asli
        if kata.isupper():
            return corrected.upper()
        elif kata[0].isupper():
            return corrected.capitalize()
        return corrected
    
    # Step 2: Kalau tidak ada di phrase corrections, coba fuzzy matching
    if not _is_valid_word(kata):
        return kata
    
    corrected = _find_best_match(kata)
    return corrected if corrected else kata


# Multi-word phrase corrections (run before word-by-word correction)
MULTI_WORD_CORRECTIONS = {
    # Header dokumen pemerintah lama
    "pusat camat tenggara": "pusat djawatan gedung negara",
    "pusat camat tenagara": "pusat djawatan gedung negara",
    "pusat caamat tanggara": "pusat djawatan gedung negara",
    "pusat djawatan gedung2 negara": "pusat djawatan gedung negara",
    "kantor angka penunjukan": "keterangan penundjukan",
    "angka penunjukan rumah": "penundjukan rumah",
    "rumah ng utara": "rumah negara",
    "departemen ptsyaai dan tenaga": "departemen pekerjaan umum dan tenaga",
    "departntnptsyaai dan tenaga": "departemen pekerjaan umum dan tenaga",
    "departemen pcaai dan tenaga": "departemen pekerjaan umum dan tenaga",
    "departma perumahan": "departemen perumahan",
    "untul monciari rumah": "untuk menghuni rumah",
    "untuk monciari rumah": "untuk menghuni rumah",
    "bercgs-r-an surat": "berdasarkan surat",
    "barcgs-r-an surat": "berdasarkan surat",
    "keterangan lantai": "keterangan lain-lain",
    "d juml.h penghuni": "djumlah penghuni",
    "d jumlh penghuni": "djumlah penghuni",
    "juml.h penghuni": "djumlah penghuni",
}


def _apply_multi_word_corrections(text: str) -> str:
    """
    Apply multi-word phrase corrections.
    Case-insensitive matching, preserve original case style.
    """
    text_lower = text.lower()
    result = text
    
    for wrong, correct in MULTI_WORD_CORRECTIONS.items():
        # Find case-insensitive
        idx = text_lower.find(wrong)
        if idx != -1:
            # Get original segment to check case
            original_segment = result[idx:idx+len(wrong)]
            
            # Determine case style
            if original_segment.isupper():
                replacement = correct.upper()
            elif original_segment[0].isupper():
                replacement = correct.title()
            else:
                replacement = correct
            
            # Replace
            result = result[:idx] + replacement + result[idx+len(wrong):]
            text_lower = result.lower()  # Update for next iteration
            print(f"📝 Koreksi frasa: '{wrong}' -> '{correct}'")
    
    return result


def correct_text(text: str) -> str:
    """
    Koreksi seluruh teks menggunakan kamus.
    
    1. Apply multi-word phrase corrections first
    2. Then word-by-word corrections
    
    Args:
        text: Teks hasil OCR
        
    Returns:
        Teks yang sudah dikoreksi
    """
    if not text or not HAS_RAPIDFUZZ:
        return text
    
    # Step 1: Apply multi-word phrase corrections first
    text = _apply_multi_word_corrections(text)
    
    # Step 2: Split berdasarkan whitespace dan non-word characters
    # Preserve delimiter untuk reconstruct
    tokens = re.findall(r'\S+|\s+', text)
    
    hasil = []
    for token in tokens:
        if token.strip():  # Ini kata
            # Pisahkan punctuation dari kata
            # Contoh: "Rumah." -> "Rumah" + "."
            match = re.match(r'^([^\w]*)([\w\-\']+)([^\w]*)$', token)
            if match:
                prefix, word, suffix = match.groups()
                corrected = correct_word(word)
                hasil.append(prefix + corrected + suffix)
            else:
                hasil.append(token)
        else:  # Whitespace
            hasil.append(token)
    
    return ''.join(hasil)


def correct_with_stats(text: str) -> Tuple[str, int]:
    """
    Koreksi teks dan hitung jumlah kata yang dikoreksi.
    
    Args:
        text: Teks hasil OCR
        
    Returns:
        Tuple (teks_dikoreksi, jumlah_koreksi)
    """
    if not text or not HAS_RAPIDFUZZ:
        return text, 0
    
    # Apply multi-word phrase corrections first
    text = _apply_multi_word_corrections(text)
    
    tokens = re.findall(r'\S+|\s+', text)
    
    hasil = []
    corrections = 0
    
    for token in tokens:
        if token.strip():
            match = re.match(r'^([^\w]*)([\w\-\']+)([^\w]*)$', token)
            if match:
                prefix, word, suffix = match.groups()
                corrected = correct_word(word)
                if corrected != word:
                    corrections += 1
                hasil.append(prefix + corrected + suffix)
            else:
                hasil.append(token)
        else:
            hasil.append(token)
    
    return ''.join(hasil), corrections


# Quick test
if __name__ == "__main__":
    test_cases = [
        "DEPARTNN PCAAI DAN TENAGA",
        "Jelan Kramet 63 Jakrta",
        "Rumah tersebut dibawah ini",
        "Gaji pokok Rp. 277",
        "Nomoa 2078",
    ]
    
    print("=== Test Dictionary Correction ===\n")
    for text in test_cases:
        corrected, count = correct_with_stats(text)
        print(f"Asli    : {text}")
        print(f"Koreksi : {corrected}")
        print(f"Jumlah  : {count} kata\n")
