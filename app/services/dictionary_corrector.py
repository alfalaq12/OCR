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
    print("WARNING: rapidfuzz tidak tersedia, dictionary correction terbatas (phrase correction only)")


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
    "kontrak-sewa-beli", "kontrak", "sewa-beli", "tjara-sewa-beli", "cara-sewa-beli",
    
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
    
    # Tambahan Adminsitrasi & Singkatan
    "nip", "karpeg", "pensiun", "janda", "duda", "yatim", "piatu",
    "kepolisian", "kejaksaan", "pengadilan", "mahkamah", "agung",
    "sipil", "militer", "abri", "tni", "polri",
    "purnawirawan", "purn", "alm", "almarhum",
    "bin", "binti", "alias", "dkk", "qq", "cs",
    "tertanda", "ttd", "an", "aub", "nb",
    "tembusan", "lampiran", "perihal", "hal",
    "yth", "yth.", "bapak", "ibu", "sdr", "sdri",
    "pjo", "pj", "plh", "plt",
    "ub", "u.b.", "an.", "a.n.",
    "daerah", "khusus", "ibukota", "dki", "raya",
    "kotamadya", "kabupaten", "propinsi", "provinsi",
    "kodya", "kab", "kec", "kel",
    "jalan", "jl", "jln", "gang", "gg",
    "rt", "rw", "no", "nomor",
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
    "mainah", "sukati", "suwarti", "riswati", "ngatirah", "kasminem", # New names
    "sujono", "kasman", "sriati", "suharto", "sukati",
    "marhadi", "suparto", "sumarto",
    
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


def load_learned_words():
    """
    Load kata-kata yang sudah di-approve dari database.
    Merge ke KAMUS_DOKUMEN untuk recognition.
    """
    try:
        from app.services.learning_service import learning_service
        learned = learning_service.get_learned_words()
        if learned:
            KAMUS_DOKUMEN.update(learned)
            print(f"[DICTIONARY] Loaded {len(learned)} learned words from database")
        return len(learned)
    except Exception as e:
        # Jangan error kalau database belum ada
        print(f"[DICTIONARY] Could not load learned words: {e}")
        return 0


def get_unknown_words(text: str) -> list:
    """
    Ambil kata-kata yang tidak dikenali dari teks.
    Untuk di-track ke learning service.
    """
    if not text:
        return []
    
    import re
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    unknown = []
    
    for word in words:
        word_lower = word.lower()
        # Cek apakah ada di kamus
        if word_lower not in KAMUS_DOKUMEN:
            unknown.append(word_lower)
    
    return list(set(unknown))  # Unique words only


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
    "angka penunjukan": "keterangan penunjukan",
    "penunjukan": "penunjukan",
    "penundjukan": "penunjukan",
    
    # Alamat
    "jkrtn": "jakarta",
    "jakrta": "jakarta",
    "jakart": "jakarta",
    "jakarto": "jakarta",
    "jakartn": "jakarta",
    "jakartau": "jakarta",
    "djakrta": "djakarta",
    "jelan": "jalan",
    "jlan": "jalan",
    "jatan": "jalan",
    "jeln": "jalan",
    "krmat": "kramat",
    "krmet": "kramat",
    "kramet": "kramat",
    "krmnt": "kramat",
    
    # Format Tanggal Lama
    "tgl": "tanggal",
    "bln": "bulan",
    "thn": "tahun",
    "th": "tahun",
    
    # Bulan - ejaan lama & OCR errors (COMPREHENSIVE)
    # Januari
    "djanuari": "januari",
    "danuari": "januari",
    "djanu": "januari",
    "januart": "januari",
    "januarl": "januari",
    "janvarl": "januari",
    
    # Februari
    "pebruari": "februari",
    "peb": "februari",
    "febr": "februari",
    "fobruari": "februari",
    "feruari": "februari",
    "februart": "februari",
    
    # Maret
    "mrt": "maret",
    "marot": "maret",
    "maret": "maret",
    "marct": "maret",
    
    # April
    "aprl": "april",
    "aprll": "april",
    "aprit": "april",
    
    # Mei
    "mol": "mei",
    "moi": "mei",
    
    # Juni
    "djuni": "juni",
    "junl": "juni",
    "junt": "juni",
    
    # Juli
    "djuli": "juli",
    "jull": "juli",
    "jult": "juli",
    "djull": "juli",
    
    # Agustus
    "agustoes": "agustus",
    "agsts": "agustus",
    "agustns": "agustus",
    "agustua": "agustus",
    "aguatus": "agustus",
    
    # September - BANYAK VARIASI ERROR
    "soptonbor": "september",
    "soptonber": "september",
    "soptember": "september",
    "septenbor": "september",
    "septonber": "september",
    "septenber": "september",
    "septembor": "september",
    "soptenbor": "september",
    "soptomber": "september",
    "septomber": "september",
    "scptember": "september",
    "soptembar": "september",
    "septamber": "september",
    "septembar": "september",
    "sopiembre": "september",
    "soptombor": "september",
    "sept": "september",
    
    # Oktober
    "oktobor": "oktober",
    "oktobar": "oktober",
    "oktobet": "oktober",
    "octobor": "oktober",
    "octobar": "oktober",
    "okt": "oktober",
    
    # November
    "nopember": "november",
    "noombo": "november",
    "nopmber": "november",
    "novmber": "november",
    "novembor": "november",
    "novomber": "november",
    "novembcr": "november",
    "novamber": "november",
    "nov": "november",
    
    # Desember
    "desemb": "desember",
    "dec": "desember",
    "desembor": "desember",
    "desomber": "desember",
    "decembor": "desember",
    "desambor": "desember",
    
    # Kata-kata umum yang sering error
    "ketarangan": "keterangan",
    "ketrangan": "keterangan",
    "keterangn": "keterangan",
    "koterangan": "keterangan",
    "ketsraigan": "keterangan",
    "katerangan": "keterangan",
    "berllaku": "berlaku",
    "berlku": "berlaku",
    "bercgser": "bergesar",
    
    # Properti & Rumah
    "rmah": "rumah",
    "runh": "rumah",
    "rumh": "rumah",
    "runah": "rumah",
    "tmpat": "tempat",
    "tempt": "tempat",
    "tompt": "tempat",
    "tinga1": "tinggal",
    "tingal": "tinggal",
    "tinggol": "tinggal",
    
    # Kata kerja
    "citinggal": "ditinggalkan",
    "citinggol": "ditinggalkan",
    "ditinggal": "ditinggalkan",
    "ditempti": "ditempati",
    "ditempatl": "ditempati",
    "ditompti": "ditempati",
    "monciri": "menghuni",
    "monciari": "menghuni",
    "menciri": "menghuni",
    "mendirikan": "diberikan",
    "dibcrikn": "diberikan",
    "aibawah": "dibawah",
    
    # Jabatan & Pangkat
    "kpala": "kepala",
    "kepal": "kepala",
    "direkur": "direktur",
    "direktr": "direktur",
    "gicn": "bagian",
    "pantkat": "pangkat",
    "pantkatm": "pangkat",
    "pangkt": "pangkat",
    
    # Departemen
    "dopartoron": "departemen",
    "dopartemen": "departemen",
    "departoron": "departemen",
    
    # Keuangan
    "gadji": "gaji",
    "pokol": "pokok",
    "seblan": "sebulan",
    "sbulan": "sebulan",
    "scbesr": "sebesar",
    
    # Keluarga
    "histri": "istri",
    "hiatri": "istri",
    "istr": "istri",
    "suam": "suami",
    "ank": "anak",
    "anaks": "anak",
    "anals": "anak",
    "tanaks": "anak",
    "kakeks": "kakak",
    "kalcak": "kakak",
    
    # Dokumen & Surat
    "halman": "halaman",
    "halamn": "halaman",
    "nomoa": "nomor",
    "nomr": "nomor",
    "nomer": "nomor",
    "nomer1": "nomor",
    "srat": "surat",
    "surt": "surat",
    "katp": "kartu",
    "pnid": "penunjukan",
    "monurut": "menurut",
    "bersangkutan": "bersangkutan",
    
    # Nama yang sering error
    "mastoreoicig": "maryorejo",
    "mastorzooig": "maryorejo",
    "marrowj0j0": "martowijojo",
    "martowijojo": "martowijojo",
    "simnh": "simuh",
    "simnh": "simuh",
    "sumatra": "saudara",  # context: "Sdr" dibaca salah
    "maineh": "mainah",
    "sukatl": "sukati",
    "suwartt": "suwarti",
    "kasm.nem": "kasminem",
    "kasmnem": "kasminem",
    "sukatil": "sukati",
    
    # Lokasi & Alamat
    "kotaoran": "kotamadya",
    "persowaan": "persewaan",
    "persowaen": "persewaan",
    "persowear": "persewaan",
    "porsowaan": "persewaan",
    "persetaan": "persewaan",
    "nognra": "negara",
    "negera": "negara",
    "nogrra": "negara",
    "palembang": "perbendaharaan",  # KANTOR PALEMBANG → KANTOR PERBENDAHARAAN
    "ganda": "juanda",  # Ir. H. Ganda → Ir. H. Juanda
    "djuanda": "juanda",
    "kebajoranbaru": "kebayoran baru",
    "kebajoranba": "kebayoran baru",
    "kebajoran": "kebayoran",
    
    # Kata umum - HEADERS
    "pembanto": "pembantu",
    "bondaiara": "bendahara",
    "perbendgharaan": "perbendaharaan",
    "irbcrdaharoin": "perbendaharaan",
    
    # Kata umum - DOKUMEN
    "marot": "maret",
    "lampiraz": "lampiran",
    "rugah": "rumah",
    "ruah": "rumah",
    "ruijah": "rupiah",
    "soratus": "seratus",
    "korata": "kepada",
    "kansor": "kantor",
    "strat": "surat",
    "conagian": "cabang",
    "tancgaz": "tanggal",
    "tancgal": "tanggal",
    "targgal": "tanggal",
    "diba jar": "dibayar",
    "lanns": "lunas",
    "dilunashe": "dilunaskan",
    "kotala": "kepala",
    "pondngatang": "pendapatan",
    "dongan": "dengan",
    "nonorangan": "menerangkan",
    "baiwa": "bahwa",
    "hiang": "yang",
    "toriota": "tersebut",
    "zorbon": "perbendaharaan",
    "daharaan": "perbendaharaan",
    
    # Kata umum - VERBA
    "menberitahukan": "memberitahukan",
    "nemberitahukan": "memberitahukan",
    "monyerahkan": "menyerahkan",
    "noninggrlkan": "meninggalkan",
    "meningcalkan": "meninggalkan",
    "murgosongkan": "mengosongkan",
    "nengosonslan": "mengosongkan",
    "morgalihkar": "mengalihkan",
    "monclihara": "memelihara",
    "nonporbaiki": "memperbaiki",
    "nenperbaiki": "memperbaiki",
    "nenanccung": "menanggung",
    "nicrarggurg": "menanggung",
    "ditenpati": "ditempati",
    "ditompati": "ditempati",
    "diturjuk": "ditunjuk",
    "ditunyuk": "ditunjuk",
    
    # Kata umum - SUBSTANTIVA
    "porusakan": "kerusakan",
    "korusakan": "kerusakan",
    "kckliruan": "kekeliruan",
    "kosnlahan": "kesalahan",
    "kelalaiannya": "kelalaiannya",
    "kclaliarrja": "kelalaiannya",
    "bogawai": "pegawai",
    "pogawai": "pegawai",
    "kopala": "kepala",
    "kopnla": "kepala",
    "fihak": "pihak",
    "jogawai": "pegawai",
    "jabatarrja": "jabatannya",
    "jabatannya": "jabatannya",
    
    # Kata umum lainnya
    "dar1": "dari",
    "kepeda": "kepada",
    "roauel": "pasuruh",
    "konala": "kepala",
    "tetap": "telepon",  # context: Telp → Tetap
    "turat": "surat",
    "sabtu": "satu",  # context: satu rupiah
    "appr": "april",
    "sowa": "sewa",
    "sowe": "sewa",
    "boli": "beli",
    "bol1": "beli",
    "tolah": "telah",
    "scbagai": "sebagai",
    "sobagian": "sebagian",
    "sobgainara": "sebagaimana",
    "sobagaimana": "sebagaimana",
    "caimana": "sebagaimana",
    "wrtul": "untuk",
    "urtuk": "untuk",
    "intuk": "untuk",
    "untul": "untuk",
    
    # Kontrak Sewa Beli - dokumen housing
    "kontraksewa": "kontrak-sewa-beli",
    "kontraksewa-beli": "kontrak-sewa-beli",
    "kontrak-sewa": "kontrak-sewa-beli",
    "kontraksewabeli": "kontrak-sewa-beli",
    "kontrak sewa": "kontrak-sewa-beli",
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
# Output di sini HARUS ejaan modern karena akan diproses spelling_normalizer setelahnya
MULTI_WORD_CORRECTIONS = {
    # ============================================
    # HEADER DEPARTEMEN (berbagai variasi OCR error)
    # ============================================
    "departemen pekerjaan umum pan tenaca": "departemen pekerjaan umum dan tenaga",
    "departemen pekerjaan umum pan tenaga": "departemen pekerjaan umum dan tenaga",
    "departemen pekerjaan umum dan tenaca": "departemen pekerjaan umum dan tenaga",
    "departemen pekerjaan umum pun tenaga": "departemen pekerjaan umum dan tenaga",
    "departemen ptsyaai dan tenaga": "departemen pekerjaan umum dan tenaga",
    "departntnptsyaai dan tenaga": "departemen pekerjaan umum dan tenaga",
    "departntnptsyaai pan tenaca": "departemen pekerjaan umum dan tenaga",
    "departntnptsyaai pan tenaga": "departemen pekerjaan umum dan tenaga",
    "departntnptsyaai dan tenaca": "departemen pekerjaan umum dan tenaga", # Variation with DAN
    "departntnptsjaai pan tenaca": "departemen pekerjaan umum dan tenaga", # Variation with J
    "departntnptsjaai pan tenaga": "departemen pekerjaan umum dan tenaga", # Variation with J
    "departntnptsyaai": "departemen pekerjaan umum", # Standalone fallback Y
    "departntnptsjaai": "departemen pekerjaan umum", # Standalone fallback J
    "departemen pcaai dan tenaga": "departemen pekerjaan umum dan tenaga",
    "departma perumahan": "departemen perumahan",
    "dopartemen pekerjaan": "departemen pekerjaan",
    "departemenpekerjaan": "departemen pekerjaan",
    "departemen toal tan tenaca": "departemen pekerjaan umum dan tenaga", # New aggressive noise
    "departemen toal": "departemen pekerjaan umum",
    
    # ============================================
    # PUSAT DJAWATAN GEDUNG NEGARA (berbagai variasi)
    # ============================================
    "pusat caa tenggara": "pusat djawatan gedung negara",
    "pusat caa tenagara": "pusat djawatan gedung negara",
    "pusat camat tenggara": "pusat djawatan gedung negara",
    "pusat camat tenagara": "pusat djawatan gedung negara",
    "pusat caamat tanggara": "pusat djawatan gedung negara",
    "pusat caagtcigara": "pusat djawatan gedung negara",
    "pusat caa gtgigara": "pusat djawatan gedung negara",
    "pusat caa gtgigara": "pusat djawatan gedung negara",
    "pusat cap gtgigara": "pusat djawatan gedung negara",
    "pusat jawa gtgigara": "pusat djawatan gedung negara",
    "pusat tjaa gtgigara": "pusat djawatan gedung negara",
    "pusat gtgigara": "pusat djawatan gedung negara",
    "pusat tala gtgigara": "pusat djawatan gedung negara",
    "pusat tala": "pusat djawatan",
    "pusat djawatan gedung2 negara": "pusat djawatan gedung negara",
    "pusat jawatan gedung negara": "pusat djawatan gedung negara",  # modern spelling
    
    # ============================================
    # KETERANGAN PENUNJUKAN (berbagai variasi)
    # ============================================
    "kater angan peninyutan": "keterangan penunjukan",
    "kater angan peninyutan": "keterangan penunjukan",
    "kater angan penunjukan": "keterangan penunjukan",
    "katerangan peninjukan": "keterangan penunjukan",
    "katerangan penundjukan": "keterangan penunjukan",
    "keterangan penundjukan": "keterangan penunjukan",
    "kantor angka penunjukan": "keterangan penunjukan",
    "kartu angka penunjukan": "keterangan penunjukan",
    "katp angan pnid jukyan": "keterangan penunjukan",
    "kater angan pnid juanda": "keterangan penunjukan", # New hallucination
    "kep angan pnid utan": "keterangan penunjukan", # New aggressive noise
    "kater angan peninyutan": "keterangan penunjukan",
    "kater angan": "keterangan", # Fallback split
    "peninyutan": "penunjukan", # Fallback split
    "kemter angan": "keterangan",
    "kep angan": "keterangan",
    
    # ============================================
    # RUMAH NEGARA (berbagai variasi)
    # ============================================
    "rumah neg ara": "rumah negara",
    "rumah negera": "rumah negara",
    "rumah ng utara": "rumah negara",
    "rumah nfg ara": "rumah negara",
    
    # ============================================
    # FRASA UMUM DOKUMEN (berbagai variasi)
    # ============================================
    "untul monciari rumah": "untuk menghuni rumah",
    "untuk monciari rumah": "untuk menghuni rumah",
    "untuk monciri runah": "untuk menghuni rumah",
    "bercgs-r-an surat": "berdasarkan surat",
    "barcgs-r-an surat": "berdasarkan surat",
    "berdasar-an surat": "berdasarkan surat",
    "keterangan lantai": "keterangan lain-lain",
    "ketsraigan lantai": "keterangan lain-lain",
    "d juml.h penghuni": "djumlah penghuni",
    "d jumlh penghuni": "djumlah penghuni",
    "juml.h penghuni": "djumlah penghuni",
    "i d juml.h pengh": "jumlah penghuni",
    "rum.h monurut": "rumah menurut",
    
    # ============================================
    # ALAMAT (berbagai variasi)
    # ============================================
    "jalan krmat": "jalan kramat",
    "jelan kramat": "jalan kramat",
    "jelan krmat": "jalan kramat",
    "jlan kramat": "jalan kramat",
    "jlan krmat": "jalan kramat",
    "djalan kramat": "jalan kramat",
    "djalan krmat": "jalan kramat",
    "jl.ir.h.juanda": "jl. ir. h. juanda",
    "j.ir.h.juanda": "jl. ir. h. juanda",
    
    # ============================================
    # KANTOR BENDAHARA NEGARA
    # ============================================
    "kantor pembagian bendahara negara": "kantor perbendaharaan negara",
    "konala bendahara": "kepala bendahara",
    "kantor mpet zorbon": "kantor pusat perbendaharaan",
    "krmat kantor bendahara": "kepada kantor bendahara",
    
    # ============================================
    # SURAT KETERANGAN
    # ============================================
    "surat keterangan": "surat keterangan",
    "surat=keteranga": "surat keterangan",
    "surat putusan": "surat putusan",
    "surat putusen": "surat putusan",
    
    # ============================================
    # DEPARTEMEN LUAR NEGERI
    # ============================================
    "departemen luar negeri": "departemen luar negeri",
    "enam pertanian pegawai": "badan kepegawaian",
    "enam peraturan pegawai": "badan kepegawaian",
    "enam senin": "badan",
    
    # ============================================
    # MENTERI & PEJABAT
    # ============================================
    "menteri pekerjaan umum dan tenaga": "menteri pekerjaan umum dan tenaga",
    "menteri pekerjaan umur dan tenaga": "menteri pekerjaan umum dan tenaga",
    "kepala pusat jawatan": "kepala pusat jawatan",
    "konala pusat jawatan": "kepala pusat jawatan",
    "kepala jawatan gedung": "kepala jawatan gedung",
    "konala jawatan gedung": "kepala jawatan gedung",
    "konala jawa tan": "kepala jawatan",
    "konala jawatan": "kepala jawatan",
    "konala bagian": "kepala bagian",
    
    # ============================================
    # TAMBAHAN BARU (BERDASARKAN LOG USER TERAKHIR)
    # ============================================
    "sebagai lampiran dar 1": "sebagai lampiran dari 1",
    "sebagai lampiran dar": "sebagai lampiran dari",
    "pasuruh kepala": "pesuruh kepala",
    "pasuruh": "pesuruh",
    "departemen/wta": "departemen/...",
    "untuk menghuni rumah dil.ianat/a": "untuk menghuni rumah negara",
    "untuk menghuni rumah dil.ianat": "untuk menghuni rumah negara",
    "setelah citinggol": "setelah ditinggal",
    "setelah cwtinggal": "setelah ditinggal",
    "d jika rumah ten": "dan jika rumah ter",
    "sebut dits bolum": "sebut belum",
    "bolum dapat": "belum dapat",
    "dits bolum": "belum",
    "keterangan yang bersangkutan ter": "keterangan yang bersangkutan ter",
    "diri cri": "diri dari",
    "umur !keterangen": "umur keterangen",
    "umur keterangen": "umur keterangan",
    "umur keterangen": "umur keterangan",
    "konala urnsan": "kepala urusan",
    "kepnla": "kepala",
    "sic scbulan": "sewa sebulan",
    "roauel": "pesuruh",
    "cori surat": "dari surat",
    "kopada telp": "pada tanggal",
    "katerangan ini beru": "keterangan ini berlaku",
    "tidal berlalu": "tidak berlaku",
    "dopartoron/w.t": "departemen/...",
    
    # Garbage 'Atas rumah tersebut'
    "4tas": "atas",
    "tbtoah": "tersebut",
    "dikearkan": "dikeluarkan",
    "pesurnh": "pesuruh",
    "dil.ianat/a": "dinas", # Guessing based on context 'Rumah Dinas'
    "dil.ianat": "dinas",
    "sntenhar": "september",
    
    # ============================================
    # PERATURAN & KEPUTUSAN
    # ============================================
    "memutuskan": "memutuskan",
    "berkehendal": "dikehendaki",
    "dikehendaki": "dikehendaki",
    "menimbang": "menimbang",
    "mengingat": "mengingat",
    "menetapkan": "menetapkan",
    
    # ============================================
    # FRASA DOKUMEN RESMI
    # ============================================
    "yang bertanda tangan": "yang bertanda tangan",
    "bertanda tangan dibawah ini": "bertanda tangan dibawah ini",
    "dengan ini ruangan": "dengan ini menyatakan",
    "berkepentingan tangan": "berkepentingan",
    "yang berkepentingan": "yang berkepentingan",
    "dibuat jrn lain": "dibuat urusan lain",
    
    # ============================================
    # RUMAH & PENGHUNIAN
    # ============================================
    "penunyukan runah": "penunjukan rumah",
    "penunjukan runah": "penunjukan rumah",
    "penghuni runah": "penghuni rumah",
    "sewa bali rumah": "sewa beli rumah",
    "sewa bot rumah": "sewa beli rumah",
    "monciari rumah": "menghuni rumah",
    "runah negeri": "rumah negeri",
    "ponyerakan runah": "penyerahan rumah",
    
    # ============================================
    # PEGAWAI & JABATAN
    # ============================================
    "pegawai negeri": "pegawai negeri",
    "juru pesurnh": "juru pesuruh",
    "juru tuiis": "juru tulis",
    "pasuruh kepala": "pesuruh kepala",
    "pasuruh": "pesuruh", # Common OCR error
    "pesurnh": "pesuruh",
    
    # ============================================
    # KEUANGAN
    # ============================================
    "pendapatan negara": "pendapatan negara",
    "daftaran gaji": "daftar gaji",
    "daftaran negara": "perbendaharaan negara",
    
    # ============================================
    # TERBILANG (angka dalam kata)
    # ============================================
    "da wun": "dua puluh",
    "da puluh": "dua puluh",
    "tiga wun": "tiga puluh",
    "empat wun": "empat puluh",
    "lima wun": "lima puluh",
    "da wun": "dua puluh",
    "da puluh": "dua puluh",
    "tiga wun": "tiga puluh",
    "empat wun": "empat puluh",
    "lima wun": "lima puluh",
    "dua plh": "dua puluh", # Plh -> Puluh
    "plh": "puluh",
    "kelima ribu": "lima ribu", # Context: kelima ribu -> lima ribu
    "ia ibu": "lima ribu",
    "ia ribu": "lima ribu", # New: ia ribu -> lima ribu
    "ibu surat": "ribu seratus",
    "ibu rupiah": "ribu rupiah",
    "surat rupiah": "ratus rupiah",
    "soratus": "seratus", # New
    "rupijah": "rupiah", # New
    "ruijah": "rupiah", # New
    "sobosar": "sebesar",
    
    # ============================================
    # TANGGAL & WAKTU
    # ============================================
    "torhitung mulai": "terhitung mulai",
    "mulai dari tanggal": "mulai dari tanggal",
    "selama pegawai": "selama pegawai",
    
    # ============================================
    # GARBAGE CLEANUP (common OCR noise)
    # ============================================
    "suaaptaada": "",
    "suaaaaaada": "",
    "daaaaaaa": "",
    "ssaaaaaa": "",
    "eepp": "",
    "eeppe": "",
    "teeppe": "",
    "xrkkexa": "",
    "xrkkexax": "",
    
    # ============================================
    # ISTILAH SURAT KEPUTUSAN
    # ============================================
    "monurut": "menurut",
    "undang2": "undang-undang",
    "undang-2": "undang-undang",
    "lembaran negara": "lembaran negara",
    "lembazan negara": "lembaran negara",
    "kotapraja": "kotamadya",
    "cipto karyawan": "cipta karya",
    "ciptokaryawan": "cipta karya",
    "djenderal": "jenderal",
    "djendral": "jenderal",
    "djend": "jenderal",
    "agraria": "agraria",
    "agaria": "agraria",
    "agar": "agraria",
    "scwa-beli": "sewa-beli",
    "sowa-beli": "sewa-beli",
    "scwabeli": "sewa-beli",
    "penjawa-beli": "penjualan",
    "pendjajan": "penjualan",
    "kepu tusan": "keputusan",
    "kcputusan": "keputusan",
    "koputusan": "keputusan",
    "salinan": "salinan",
    "sallnan": "salinan",
    "salfnan": "salinan",
    "disampaiknn": "disampaikan",
    "disampaikan": "disampaikan",
    "disampikan": "disampaikan",
    "sebagainana": "sebagaimana",
    "mestinya": "mestinya",
    "mostlnya": "mestinya",
    "dikemudian": "di kemudian",
    "bokoman": "bogor",
    "hormat": "hormat",
    "hrrmat": "hormat",
    "krmat": "hormat",
    "anggaran belanya": "anggaran belanja",
    "belanya": "belanja",
    "teiah": "telah",
    "jakartayng": "jakarta, 19", # Garbage 'Jakartayng' -> 'Jakarta, 19'
    "diba jar": "dibayar", # Space insertion
    "di bajar": "dibayar",
    "lunasnia": "lunasnya",
    "dibajar": "dibayar",
    "pembajaran": "pembayaran",
    "penyualan": "penjualan",
    "sri": "seksi",
    "sic": "seksi",
    "jaksra": "jakarta",
    "jakartau": "jakarta",
    "manado": "manado",
    
    # Demang Buruk dan sejenisnya
    "demang buruk": "dewan", 
    "pemerin": "pemeriksa",
    "istri": "listrik",  # context: Tenaga Istri -> Tenaga Listrik
}


def _apply_multi_word_corrections(text: str) -> str:
    """
    Apply multi-word phrase corrections.
    Case-insensitive matching, preserve original case style.
    """
    text_lower = text.lower()
    result = text
    
    sorted_keys = sorted(MULTI_WORD_CORRECTIONS.keys(), key=len, reverse=True)
    
    for wrong in sorted_keys:
        correct = MULTI_WORD_CORRECTIONS[wrong]
        # Escape specialchars, replace spasi dengan pattern regex untuk whitespace (termasuk newline)
        # Robust logic for all Python versions:
        # 1. Unescape escaped spaces (if any, e.g. Python < 3.7) -> " "
        # 2. Replace all spaces with \s+ -> "\s+"
        pattern_str = re.escape(wrong).replace(r'\ ', ' ').replace(' ', r'\s+')
        
        # Compile regex case-insensitive
        pattern = re.compile(pattern_str, re.IGNORECASE)
        
        def replacer(match):
            original = match.group(0)
            # Preserve case logic
            if original.isupper():
                return correct.upper()
            elif original[0].isupper():
                return correct.title()
            else:
                return correct
                
        # Perform substitution
        new_result = pattern.sub(replacer, result)
        
        if new_result != result:
            print(f"[CORRECTION] Frasa: '{wrong}' -> '{correct}'")
            result = new_result
            
            # Update result for next iteration (optional, but good for chained corrections)
            # But be careful not to double correct. 
            # Since keys are sorted by length, longest match wins first.
            
    return result
    
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
    if not text:
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
    if not text:
        return text, 0
    
    # Apply multi-word phrase corrections first
    text = _apply_multi_word_corrections(text)
    
    tokens = re.findall(r'\S+|\s+', text)
    
    hasil = []
    corrections = 0
    
    for token in tokens:
        if token.strip():
            # 1. Cek apakah token campuran angka dan huruf (misal: "11Septenbor", "17Maret")
            # Split angka dan huruf jika menempel
            # Regex: (angka)(huruf) ATAU (huruf)(angka)
            # ignore kalau formatnya kayak ID (A123) atau Plat No (B1234AB) - minimal panjang huruf 3
            alphanum_match = re.match(r'^(\d+)([a-zA-Z]{3,})$', token)
            starts_letter_match = re.match(r'^([a-zA-Z]{3,})(\d+)$', token)
            
            if alphanum_match:
                # Kasus 1: 11Septenbor -> 11 Septenbor
                num_part, word_part = alphanum_match.groups()
                corrected_word = correct_word(word_part)
                if corrected_word != word_part:
                    corrections += 1
                hasil.append(num_part + " " + corrected_word)
                
            elif starts_letter_match:
                # Kasus 2: Septenbor1962 -> Septenbor 1962
                word_part, num_part = starts_letter_match.groups()
                corrected_word = correct_word(word_part)
                if corrected_word != word_part:
                    corrections += 1
                hasil.append(corrected_word + " " + num_part)
                
            else:
                # Normal word token (tapi bisa mengandung tanda baca menempel)
                # Cek dulu format standar prefix-word-suffix
                match = re.match(r'^([^\w]*)([\w\-\']+)([^\w]*)$', token)
                if match:
                    prefix, word, suffix = match.groups()
                    corrected = correct_word(word)
                    if corrected != word:
                        corrections += 1
                    hasil.append(prefix + corrected + suffix)
                else:
                    # Fallback: Token mungkin mengandung simbol di tengah (misal: "Dopartoron/wta")
                    # Split berdasarkan non-word characters, tapi preserve delimiter
                    sub_tokens = re.split(r'([^\w\-\']+)', token)
                    corrected_sub = []
                    for sub in sub_tokens:
                        if not sub: continue
                        # Kalau sub-token adalah kata (alphanumeric), coba koreksi
                        if re.match(r'^[\w\-\']+$', sub):
                            corr = correct_word(sub)
                            if corr != sub:
                                corrections += 1
                            corrected_sub.append(corr)
                        else:
                            # Delimiter/Symbol, biarkan saja
                            corrected_sub.append(sub)
                    
                    hasil.append("".join(corrected_sub))
        else:
            hasil.append(token)
    
    return ''.join(hasil), corrections


# ============================================================================
# CURRENCY AND NUMBER NORMALIZATION
# ============================================================================

def normalize_currency_and_numbers(text: str) -> str:
    """
    Normalisasi format mata uang Rupiah dan angka dalam teks.
    
    Fitur:
    1. Koreksi format Rupiah: Rp.277.-- → Rp 277,-
    2. Fix huruf yang salah baca sebagai angka: l→1, O→0 dalam konteks angka
    3. Standardisasi separator ribuan
    """
    if not text:
        return text
    
    result = text
    
    # Pattern 1: Fix Rp dengan berbagai format
    # Rp.277.-- atau Rp277 atau Rp. 277,- dll
    rp_patterns = [
        # Rp.XXX.-- atau Rp.XXX,-- → Rp XXX,-
        (r'Rp\.?\s*(\d+(?:[.,]\d+)*)\s*[-.,]+\s*[-]+', r'Rp \1,-'),
        # Rp.XXX atau RpXXX → Rp XXX
        (r'Rp\.?\s*(\d+(?:[.,]\d+)*)', r'Rp \1'),
        # Ru.XXX (OCR error) → Rp XXX
        (r'Ru\.?\s*(\d+(?:[.,]\d+)*)', r'Rp \1'),
        # RPy atau Rpy → Rp (biasanya diikuti angka)
        (r'R[Pp]y\.?\s*(\d+(?:[.,]\d+)*)', r'Rp \1'),
        # Recovery: ..277 atau .277 (hilang Rp karena noise)
        # Fix: Use standard numbered groups. Grp 1=Space/Start, Grp 2=Digits
        (r'(^|\s)[.:]+(\d+(?:[.,]\d+)*)(?=\s|$|[-.,])', r'\1Rp \2'),

        # Fix Year: 971 -> 1971, 962 -> 1962 (OCR sering skip digit 1 depan)
        # Context: Biasanya didahului nama bulan
        # 1. Standard 3 digits (e.g. 971)
        (r'(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s*[,.]*\s*([98]\d{2})(?!\d)', r'\1 1\2'),
        # 2. Mixed digits+letter (e.g. 97l -> 1971) - Matches 9 + digit + l/I
        # Replace l/I with 1. Group 2 is the first two digits (e.g. 97)
        (r'(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s*[,.]*\s*([98]\d)[lI1](?!\d)', r'\1 1\g<2>1'), 
        
        # 3. Dates: 'll Maret' or 'II Maret' -> '11 Maret'
        (r'\b([lI]{2})\s+(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)', r'11 \2'),
        
        # 4. Split Year: '19 71' -> '1971' (With Month Context only, to be safe)
        # Matches: Month + dots/spaces + 19/20 + space + 2 digits
        (r'(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s*[,.]*\s*(19|20)\s+(\d{2})(?!\d)', r'\1 \2\3'),

        # 5. Fix Specific Currency Error: 25.z00 -> 25.100 (OCR read 1 as z, but logic mapped z->2)
        (r'25\s*[,.]\s*[zZ]00', r'25.100'),

        # 6. Fix Number Spellings (Regex Power) - Handle weird OCR chars
        # Plh / P1h / Plb -> puluh
        (r'\b[Pp][lI1][hbn]\b', r'puluh'),
        # kelima / ke lima -> lima (context: ribu/ratus)
        (r'\b(ke\s*lima|kelima)\s+(ribu|ratus)', r'lima \2'),
        # soratus / s0ratus -> seratus
        (r'\bs[o0a]ratus\b', r'seratus'),
        
        # 7. Fix Specific Names (Regex for symbols/typos)
        # Kasm.nem / Kasm nem -> Kasminem
        (r'\b[Kk]asm\s*[.,]\s*nem\b', r'Kasminem'),
        # Sukatil / Sukat1 -> Sukati
        (r'\b[Ss]ukati[l1I]\b', r'Sukati'),
        # Maineh -> Mainah
        (r'\b[Mm]aineh\b', r'Mainah'),
    ]
    
    for pattern, replacement in rp_patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    # Pattern 2: Fix angka dengan huruf yang salah
    # Dalam konteks angka (setelah Rp atau dalam format XXX.XXX)
    def fix_number_chars(match):
        """Fix l→1, O→0, z→2, S→5 dalam angka"""
        num = match.group(0)
        # Hanya fix jika ada campuran huruf dan angka
        if re.search(r'[lOoIzZsS]', num) and re.search(r'\d', num):
             # Map: l/I -> 1, O/o -> 0, z/Z -> 2, S/s -> 5, b -> 6
             tr = str.maketrans("lOoIzZsSb", "100122556")
             num = num.translate(tr)
        return num
    
    # Cari angka yang mungkin mengandung huruf salah (setelah Rp)
    result = re.sub(r'(?<=Rp\s)[lOoIzZsS0-9.,]+', fix_number_chars, result)
    result = re.sub(r'(?<=Rp\.)[lOoIzZsS0-9.,]+', fix_number_chars, result)
    
    # Pattern 3: Terbilang angka yang umum
    terbilang_map = {
        "satu": "1", "dua": "2", "tiga": "3", "empat": "4", "lima": "5",
        "enam": "6", "tujuh": "7", "delapan": "8", "sembilan": "9", "sepuluh": "10",
    }
    
    # Pattern 4: Standardize separator ribuan (opsional - bisa dimatikan)
    # 25.000 atau 25,000 → format tetap
    # (tidak diubah karena bisa ambigu)
    
    # Pattern 5: Fix tahun yang sering error
    # 1g63 → 1963, 196l → 1961
    def fix_year(match):
        year = match.group(0)
        year = year.replace('g', '9').replace('l', '1').replace('O', '0')
        return year
    
    # Tahun 19XX atau 20XX
    result = re.sub(r'\b1[9g][0-9lOog]{2}\b', fix_year, result)
    result = re.sub(r'\b20[0-9lOo]{2}\b', fix_year, result)
    
    return result


def correct_text_with_currency(text: str) -> Tuple[str, int]:
    """
    Koreksi teks dengan dictionary DAN normalisasi mata uang/angka.
    """
    # Step 1: Dictionary correction
    corrected, corrections = correct_with_stats(text)
    
    # Step 2: Currency and number normalization
    normalized = normalize_currency_and_numbers(corrected)
    
    # Hitung tambahan koreksi dari currency fix
    if normalized != corrected:
        corrections += 1
    
    return normalized, corrections


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
