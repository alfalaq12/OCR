"""
Modul untuk proses OCR.
Mendukung 2 engine: PaddleOCR (Docker) dan Tesseract (local).
"""

import io
import time
import os
from typing import Tuple
from PIL import Image

# cek environment - kalo di docker pake paddleocr, kalo local pake tesseract
USE_PADDLE = os.getenv("OCR_ENGINE", "auto").lower()


class PaddleOCREngine:
    """OCR engine pake PaddleOCR - lebih akurat dan cepat"""
    
    def __init__(self):
        from paddleocr import PaddleOCR
        # init sekali aja biar gak load model terus-terusan
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',  # pake english model, works untuk indonesia juga
            show_log=False,
            use_gpu=False
        )
    
    def baca_gambar(self, gambar: Image.Image) -> str:
        """Ekstrak teks dari gambar"""
        import numpy as np
        
        # convert PIL ke numpy array
        img_array = np.array(gambar.convert("RGB"))
        
        # jalanin OCR
        hasil = self.ocr.ocr(img_array, cls=True)
        
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
    Service utama OCR - otomatis pilih engine terbaik.
    Docker: pake PaddleOCR
    Local Windows: pake Tesseract
    """

    def __init__(self):
        self._engine = None
        self._engine_name = None

    def _get_engine(self):
        """Lazy load engine - biar startup cepat"""
        if self._engine is None:
            # coba paddle dulu
            try:
                if USE_PADDLE == "paddle" or USE_PADDLE == "auto":
                    self._engine = PaddleOCREngine()
                    self._engine_name = "PaddleOCR"
                    print("✅ Menggunakan PaddleOCR engine")
            except ImportError:
                pass
            except Exception as e:
                print(f"⚠️ PaddleOCR gagal load: {e}")
            
            # fallback ke tesseract
            if self._engine is None:
                try:
                    self._engine = TesseractEngine()
                    self._engine_name = "Tesseract"
                    print("✅ Menggunakan Tesseract engine")
                except Exception as e:
                    raise Exception(f"Tidak ada OCR engine yang tersedia: {e}")
        
        return self._engine

    def get_engine_name(self) -> str:
        """Ambil nama engine yang sedang dipakai"""
        self._get_engine()
        return self._engine_name or "Unknown"

    def baca_gambar(self, gambar: Image.Image, bahasa: str = "mixed") -> str:
        """Baca text dari gambar"""
        engine = self._get_engine()
        return engine.baca_gambar(gambar)

    def _convert_pdf_ke_gambar(self, data_file: bytes) -> list:
        """Convert PDF jadi list gambar"""
        try:
            from pdf2image import convert_from_bytes
            return convert_from_bytes(data_file, dpi=200)
        except Exception as e:
            pesan = str(e).lower()
            if "poppler" in pesan or "pdftoppm" in pesan:
                raise Exception(
                    "Poppler belum diinstall. "
                    "Download dari: https://github.com/osber/poppler-windows/releases"
                )
            raise Exception(f"Gagal convert PDF: {str(e)}")

    def proses_file(
        self,
        data_file: bytes,
        nama_file: str,
        bahasa: str = "mixed"
    ) -> Tuple[str, int, int]:
        """
        Proses file (gambar atau PDF).
        Return: (text, jumlah_halaman, waktu_ms)
        """
        waktu_mulai = time.time()

        is_pdf = nama_file.lower().endswith('.pdf')

        if is_pdf:
            list_gambar = self._convert_pdf_ke_gambar(data_file)
            semua_text = []

            for idx, gambar in enumerate(list_gambar):
                text_halaman = self.baca_gambar(gambar, bahasa)
                if text_halaman:
                    semua_text.append(f"--- Halaman {idx + 1} ---\n{text_halaman}")

            text_hasil = "\n\n".join(semua_text)
            jumlah_halaman = len(list_gambar)
        else:
            gambar = Image.open(io.BytesIO(data_file))
            text_hasil = self.baca_gambar(gambar, bahasa)
            jumlah_halaman = 1

        waktu_proses = int((time.time() - waktu_mulai) * 1000)

        return text_hasil, jumlah_halaman, waktu_proses

    # alias buat backward compatibility
    def extract_text_from_bytes(self, file_bytes, filename, language="mixed"):
        return self.proses_file(file_bytes, filename, language)


# singleton instance
ocr_service = OCRService()
