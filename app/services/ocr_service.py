"""
Modul untuk proses OCR pakai Tesseract
Author: Tim Development
"""

import io
import time
import subprocess
import tempfile
import os
from typing import Tuple
from PIL import Image


class OCRService:
    """
    Kelas utama buat handle semua proses OCR.
    Pake Tesseract yang dipanggil langsung via subprocess
    biar lebih stabil dan gak ribet sama dependency.
    """

    def __init__(self):
        # cari lokasi tesseract waktu pertama kali init
        self.tesseract_cmd = self._cari_tesseract()
        self.poppler_path = self._cari_poppler()

    def _cari_tesseract(self) -> str:
        """Cari dimana tesseract diinstall"""
        lokasi_umum = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",  # linux
            "/usr/local/bin/tesseract",  # mac homebrew
            "tesseract"  # kalo udah di PATH
        ]
        
        for path in lokasi_umum:
            if os.path.exists(path):
                return path
            # coba jalanin, siapa tau ada di PATH
            try:
                hasil = subprocess.run([path, "--version"], capture_output=True)
                if hasil.returncode == 0:
                    return path
            except FileNotFoundError:
                continue
        
        return "tesseract"

    def _cari_poppler(self) -> str:
        """Cari folder bin poppler buat convert PDF"""
        lokasi_umum = [
            r"C:\poppler\bin",
            r"C:\Program Files\poppler\bin",
            r"C:\poppler-24.02.0\Library\bin",
        ]
        
        for path in lokasi_umum:
            if os.path.exists(path):
                return path
        
        return None

    def _convert_bahasa(self, bahasa: str) -> str:
        """Konversi kode bahasa ke format tesseract"""
        if bahasa == "id":
            return "ind"
        elif bahasa == "en":
            return "eng"
        else:
            # default english aja biar aman, kadang ind gak keinstall
            return "eng"

    def baca_gambar(self, gambar: Image.Image, bahasa: str = "mixed") -> str:
        """
        Baca text dari gambar pake tesseract.
        Gambar disimpen dulu ke file temp, abis itu diproses.
        """
        kode_bahasa = self._convert_bahasa(bahasa)
        
        # simpen ke file sementara
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path_temp = tmp.name
            gambar.save(path_temp, format="PNG")
        
        try:
            # jalanin tesseract
            perintah = [
                self.tesseract_cmd,
                path_temp,
                "stdout",
                "-l", kode_bahasa,
                "--oem", "3",
                "--psm", "6"
            ]
            
            hasil = subprocess.run(
                perintah,
                capture_output=True,
                text=True,
                timeout=120  # timeout 2 menit
            )
            
            if hasil.returncode != 0:
                pesan_error = hasil.stderr or "Gagal proses OCR"
                raise Exception(f"Error tesseract: {pesan_error}")
            
            output = hasil.stdout
            if output is None:
                return ""
            
            return output.strip()
        
        except subprocess.TimeoutExpired:
            raise Exception("Proses OCR timeout, coba file yang lebih kecil")
        except FileNotFoundError:
            raise Exception(f"Tesseract gak ketemu di: {self.tesseract_cmd}")
        finally:
            # hapus file temp
            if os.path.exists(path_temp):
                try:
                    os.remove(path_temp)
                except:
                    pass

    def _convert_pdf_ke_gambar(self, data_file: bytes) -> list:
        """Convert PDF jadi list gambar buat diproses satu-satu"""
        try:
            from pdf2image import convert_from_bytes
            
            opsi = {"dpi": 200}
            if self.poppler_path:
                opsi["poppler_path"] = self.poppler_path
            
            return convert_from_bytes(data_file, **opsi)
        
        except Exception as e:
            pesan = str(e).lower()
            if "poppler" in pesan or "pdftoppm" in pesan:
                raise Exception(
                    "Poppler belum diinstall. "
                    "Download dulu dari: https://github.com/osber/poppler-windows/releases "
                    "terus extract ke C:\\poppler"
                )
            raise Exception(f"Gagal convert PDF: {str(e)}")

    def proses_file(
        self,
        data_file: bytes,
        nama_file: str,
        bahasa: str = "mixed"
    ) -> Tuple[str, int, int]:
        """
        Fungsi utama buat proses file (gambar atau PDF).
        Return: (text hasil, jumlah halaman, waktu proses dalam ms)
        """
        waktu_mulai = time.time()

        # cek apakah PDF atau gambar
        is_pdf = nama_file.lower().endswith('.pdf')

        if is_pdf:
            # convert dulu ke gambar
            list_gambar = self._convert_pdf_ke_gambar(data_file)
            semua_text = []

            for idx, gambar in enumerate(list_gambar):
                text_halaman = self.baca_gambar(gambar, bahasa)
                if text_halaman:
                    semua_text.append(f"--- Halaman {idx + 1} ---\n{text_halaman}")

            text_hasil = "\n\n".join(semua_text)
            jumlah_halaman = len(list_gambar)
        else:
            # langsung proses sebagai gambar
            gambar = Image.open(io.BytesIO(data_file))
            text_hasil = self.baca_gambar(gambar, bahasa)
            jumlah_halaman = 1

        waktu_proses = int((time.time() - waktu_mulai) * 1000)

        return text_hasil, jumlah_halaman, waktu_proses

    # alias biar compatible sama kode lama
    def extract_text_from_bytes(self, file_bytes, filename, language="mixed"):
        return self.proses_file(file_bytes, filename, language)


# instance singleton biar gak bikin ulang terus
ocr_service = OCRService()
