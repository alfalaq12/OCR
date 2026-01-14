"""
Modul untuk proses OCR.
Mendukung 2 engine: PaddleOCR (Docker) dan Tesseract (local).
Sudah dioptimasi untuk performa lebih cepat.
"""

import io
import time
import os
from typing import Tuple, List
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.config import settings

# cek environment - kalo di docker pake paddleocr, kalo local pake tesseract
USE_PADDLE = os.getenv("OCR_ENGINE", "auto").lower()


def resize_gambar_kalau_perlu(gambar: Image.Image, max_dimension: int) -> Image.Image:
    """
    Resize gambar kalau terlalu gede.
    Gambar gede bikin OCR lambat, resize ke max_dimension tetep akurat.
    """
    width, height = gambar.size
    
    if width <= max_dimension and height <= max_dimension:
        return gambar
    
    # hitung ratio biar aspect ratio tetep sama
    if width > height:
        ratio = max_dimension / width
    else:
        ratio = max_dimension / height
    
    new_width = int(width * ratio)
    new_height = int(height * ratio)
    
    # pake LANCZOS buat kualitas resize terbaik
    return gambar.resize((new_width, new_height), Image.LANCZOS)


def preprocess_gambar(gambar: Image.Image, enhance: bool = True) -> Image.Image:
    """
    Preprocessing gambar untuk dokumen jadul/pudar.
    - Convert ke grayscale
    - Tingkatkan contrast
    - Denoise (optional)
    
    Ini membantu OCR baca dokumen scan yang pudar/buram.
    """
    if not enhance:
        return gambar
    
    from PIL import ImageEnhance, ImageFilter
    
    # Convert ke grayscale dulu
    if gambar.mode != 'L':
        gambar_gray = gambar.convert('L')
    else:
        gambar_gray = gambar.copy()
    
    # Tingkatkan contrast - bikin teks lebih gelap, background lebih terang
    enhancer = ImageEnhance.Contrast(gambar_gray)
    gambar_contrast = enhancer.enhance(2.0)  # 2x contrast
    
    # Tingkatkan sharpness - bikin tepi huruf lebih jelas
    enhancer = ImageEnhance.Sharpness(gambar_contrast)
    gambar_sharp = enhancer.enhance(1.5)  # 1.5x sharpness
    
    # Brightness adjustment - sedikit lebih terang biar background putih
    enhancer = ImageEnhance.Brightness(gambar_sharp)
    gambar_bright = enhancer.enhance(1.1)  # 10% lebih terang
    
    # Convert balik ke RGB untuk compatibility dengan OCR engines
    return gambar_bright.convert('RGB')


class PaddleOCREngine:
    """OCR engine pake PaddleOCR - lebih akurat dan cepat"""
    
    def __init__(self):
        from paddleocr import PaddleOCR
        # init sekali aja biar gak load model terus-terusan
        # use_angle_cls diambil dari config - matiin kalo dokumen udah lurus
        self.ocr = PaddleOCR(
            use_angle_cls=settings.USE_ANGLE_CLS,
            lang='en',  # pake english model, works untuk indonesia juga
            show_log=False,
            use_gpu=False
        )
        self._cls_enabled = settings.USE_ANGLE_CLS
    
    def baca_gambar(self, gambar: Image.Image) -> str:
        """Ekstrak teks dari gambar"""
        import numpy as np
        
        # resize dulu kalau kegedean
        gambar = resize_gambar_kalau_perlu(gambar, settings.MAX_IMAGE_DIMENSION)
        
        # convert PIL ke numpy array
        img_array = np.array(gambar.convert("RGB"))
        
        # jalanin OCR - cls sesuai config
        hasil = self.ocr.ocr(img_array, cls=self._cls_enabled)
        
        # ambil teks dari hasil
        texts = []
        if hasil and hasil[0]:
            for line in hasil[0]:
                if line and len(line) >= 2:
                    texts.append(line[1][0])
        
        return "\n".join(texts)


class TesseractEngine:
    """OCR engine pake Tesseract - buat local development"""
    
    def __init__(self):
        import subprocess
        # cari lokasi tesseract
        self.tesseract_cmd = self._cari_tesseract()
    
    def _cari_tesseract(self) -> str:
        """Cari dimana tesseract diinstall"""
        import subprocess
        lokasi_umum = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "tesseract"
        ]
        
        for path in lokasi_umum:
            if os.path.exists(path):
                return path
            try:
                hasil = subprocess.run([path, "--version"], capture_output=True)
                if hasil.returncode == 0:
                    return path
            except FileNotFoundError:
                continue
        
        return "tesseract"
    
    def baca_gambar(self, gambar: Image.Image) -> str:
        """Ekstrak teks dari gambar pake tesseract"""
        import subprocess
        import tempfile
        
        # resize dulu kalau kegedean
        gambar = resize_gambar_kalau_perlu(gambar, settings.MAX_IMAGE_DIMENSION)
        
        # simpen ke file temp
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path_temp = tmp.name
            gambar.save(path_temp, format="PNG")
        
        try:
            hasil = subprocess.run(
                [self.tesseract_cmd, path_temp, "stdout", "-l", "eng", "--oem", "3", "--psm", "6"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            output = hasil.stdout
            return output.strip() if output else ""
        
        except Exception as e:
            raise Exception(f"Tesseract error: {str(e)}")
        finally:
            if os.path.exists(path_temp):
                try:
                    os.remove(path_temp)
                except:
                    pass


class OCRService:
    """
    Service utama OCR - support multiple engines.
    
    Engine yang tersedia:
    - tesseract: Lebih cepat, cocok untuk dokumen jelas
    - paddle: Lebih akurat, cocok untuk dokumen buram/kurang jelas
    
    Fitur:
    - Pilih engine per request
    - Image resize otomatis untuk gambar gede
    - Parallel processing untuk PDF multi-halaman
    - Thread-safe engine initialization
    """

    def __init__(self):
        self._tesseract_engine = None
        self._paddle_engine = None
        self._default_engine = None
        self._default_engine_name = None
        self._lock = __import__('threading').Lock()
        self._available_engines = []

    def init_engine(self):
        """
        Initialize semua engine yang tersedia saat startup.
        """
        with self._lock:
            # try Tesseract
            try:
                self._tesseract_engine = TesseractEngine()
                self._available_engines.append("tesseract")
                print("✅ Tesseract engine ready")
            except Exception as e:
                print(f"⚠️ Tesseract tidak tersedia: {e}")
            
            # try PaddleOCR
            try:
                if USE_PADDLE in ["paddle", "auto"]:
                    self._paddle_engine = PaddleOCREngine()
                    self._available_engines.append("paddle")
                    print("✅ PaddleOCR engine ready")
            except ImportError:
                print("⚠️ PaddleOCR tidak tersedia (not installed)")
            except Exception as e:
                print(f"⚠️ PaddleOCR gagal load: {e}")
            
            # set default engine
            if USE_PADDLE == "tesseract" and self._tesseract_engine:
                self._default_engine = self._tesseract_engine
                self._default_engine_name = "tesseract"
            elif USE_PADDLE == "paddle" and self._paddle_engine:
                self._default_engine = self._paddle_engine
                self._default_engine_name = "paddle"
            elif self._paddle_engine:
                self._default_engine = self._paddle_engine
                self._default_engine_name = "paddle"
            elif self._tesseract_engine:
                self._default_engine = self._tesseract_engine
                self._default_engine_name = "tesseract"
            else:
                raise Exception("Tidak ada OCR engine yang tersedia!")
            
            print(f"📌 Default engine: {self._default_engine_name}")
        
        return self._default_engine

    def get_engine_name(self) -> str:
        """Ambil nama default engine"""
        return self._default_engine_name or "Unknown"
    
    def get_available_engines(self) -> list:
        """Ambil daftar engine yang tersedia"""
        return self._available_engines.copy()

    def _get_engine(self, engine_name: str = None):
        """
        Ambil engine berdasarkan nama.
        Kalau engine_name None atau 'auto', pakai default.
        """
        if engine_name is None or engine_name == "auto":
            return self._default_engine
        
        engine_name = engine_name.lower()
        
        if engine_name == "tesseract":
            if self._tesseract_engine is None:
                raise Exception("Tesseract engine tidak tersedia")
            return self._tesseract_engine
        elif engine_name in ["paddle", "paddleocr"]:
            if self._paddle_engine is None:
                raise Exception("PaddleOCR engine tidak tersedia")
            return self._paddle_engine
        else:
            raise Exception(f"Engine tidak dikenal: {engine_name}. Pilihan: tesseract, paddle")

    def baca_gambar(self, gambar: Image.Image, bahasa: str = "mixed", engine: str = None, enhance: bool = False) -> str:
        """Baca text dari gambar dengan engine yang dipilih"""
        # Force Tesseract saat enhance aktif untuk mencegah crash PaddleOCR
        if enhance and settings.FORCE_TESSERACT_FOR_ENHANCE and self._tesseract_engine:
            engine = "tesseract"
            print(f"🔄 Auto-switch ke Tesseract karena enhance=true")
        
        # Preprocessing untuk dokumen jadul/pudar
        if enhance:
            gambar = preprocess_gambar(gambar, enhance=True)
        
        ocr_engine = self._get_engine(engine)
        return ocr_engine.baca_gambar(gambar)

    def _convert_pdf_ke_gambar(self, data_file: bytes) -> list:
        """Convert PDF jadi list gambar dengan DPI dari config"""
        try:
            from pdf2image import convert_from_bytes
            return convert_from_bytes(data_file, dpi=settings.PDF_DPI)
        except Exception as e:
            pesan = str(e).lower()
            if "poppler" in pesan or "pdftoppm" in pesan:
                raise Exception(
                    "Poppler belum diinstall. "
                    "Download dari: https://github.com/osber/poppler-windows/releases"
                )
            raise Exception(f"Gagal convert PDF: {str(e)}")

    def _proses_satu_halaman(self, args: Tuple[int, Image.Image, str, str, bool]) -> Tuple[int, str]:
        """Helper buat parallel processing - proses satu halaman PDF"""
        idx, gambar, bahasa, engine, enhance = args
        text = self.baca_gambar(gambar, bahasa, engine, enhance)
        return idx, text

    def proses_file(
        self,
        data_file: bytes,
        nama_file: str,
        bahasa: str = "mixed",
        engine: str = None,
        enhance: bool = False
    ) -> Tuple[str, int, int]:
        """
        Proses file (gambar atau PDF).
        
        Args:
            data_file: bytes dari file
            nama_file: nama file (untuk deteksi PDF)
            bahasa: bahasa dokumen (id/en/mixed)
            engine: pilihan engine (tesseract/paddle/auto)
            enhance: aktifkan preprocessing untuk dokumen jadul/pudar
        
        Return: (text, jumlah_halaman, waktu_ms)
        """
        waktu_mulai = time.time()

        is_pdf = nama_file.lower().endswith('.pdf')

        if is_pdf:
            list_gambar = self._convert_pdf_ke_gambar(data_file)
            jumlah_halaman = len(list_gambar)
            
            # parallel processing kalo enabled dan ada lebih dari 1 halaman
            if settings.PARALLEL_PDF_PROCESSING and jumlah_halaman > 1:
                hasil_per_halaman = {}
                
                max_workers = min(settings.PDF_WORKERS, jumlah_halaman)
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._proses_satu_halaman, (idx, gambar, bahasa, engine, enhance)): idx
                        for idx, gambar in enumerate(list_gambar)
                    }
                    
                    for future in as_completed(futures):
                        idx, text = future.result()
                        hasil_per_halaman[idx] = text
                
                semua_text = []
                for idx in range(jumlah_halaman):
                    text = hasil_per_halaman.get(idx, "")
                    if text:
                        semua_text.append(f"--- Halaman {idx + 1} ---\n{text}")
                
                text_hasil = "\n\n".join(semua_text)
            else:
                semua_text = []
                for idx, gambar in enumerate(list_gambar):
                    text_halaman = self.baca_gambar(gambar, bahasa, engine, enhance)
                    if text_halaman:
                        semua_text.append(f"--- Halaman {idx + 1} ---\n{text_halaman}")
                text_hasil = "\n\n".join(semua_text)
        else:
            gambar = Image.open(io.BytesIO(data_file))
            text_hasil = self.baca_gambar(gambar, bahasa, engine, enhance)
            jumlah_halaman = 1

        waktu_proses = int((time.time() - waktu_mulai) * 1000)

        return text_hasil, jumlah_halaman, waktu_proses

    # alias buat backward compatibility
    def extract_text_from_bytes(self, file_bytes, filename, language="mixed", engine=None):
        return self.proses_file(file_bytes, filename, language, engine)


# singleton instance
ocr_service = OCRService()
