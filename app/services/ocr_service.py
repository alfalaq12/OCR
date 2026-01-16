"""
Modul untuk proses OCR.
Mendukung 2 engine: PaddleOCR (Docker) dan Tesseract (local).
Sudah dioptimasi untuk performa lebih cepat.
"""

import io
import time
import os
from typing import Tuple, List, Dict, Any
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


def _deskew_image(img_gray, cv2, np):
    """
    Koreksi dokumen yang miring (skewed) secara otomatis.
    Mendeteksi sudut kemiringan dari konten teks dan merotasi untuk meluruskan.
    """
    try:
        # Threshold untuk deteksi konten
        thresh = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        
        # Cari koordinat non-zero pixels (teks)
        coords = np.column_stack(np.where(thresh > 0))
        
        if len(coords) < 100:  # Terlalu sedikit konten, skip deskew
            return img_gray
        
        # Hitung angle dari minimum area rectangle
        angle = cv2.minAreaRect(coords)[-1]
        
        # Koreksi angle
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90
        
        # Skip jika sudah hampir lurus (< 0.5 derajat)
        if abs(angle) < 0.5:
            return img_gray
        
        # Rotasi gambar
        (h, w) = img_gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Hitung ukuran baru untuk menampung gambar yang dirotasi
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        rotated = cv2.warpAffine(img_gray, M, (new_w, new_h), 
                                  flags=cv2.INTER_CUBIC, 
                                  borderMode=cv2.BORDER_REPLICATE)
        print(f"📐 Deskew: koreksi {angle:.1f}°")
        return rotated
        
    except Exception as e:
        print(f"⚠️ Deskew error: {e}, skip deskew")
        return img_gray


def _remove_yellow_background(img_bgr, cv2, np):
    """
    Hilangkan warna kuning/coklat dari kertas tua.
    Konversi ke LAB color space dan enhance channel L (luminance).
    """
    try:
        # Convert ke LAB color space
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE ke L channel saja (luminance)
        # Ini menghilangkan warna kuning sambil mempertahankan kontras teks
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced_l = clahe.apply(l)
        
        # Merge kembali dengan a,b channel yang di-neutralize
        # a dan b mendekati 128 = warna netral (tidak kuning/biru)
        neutral_a = np.full_like(a, 128)
        neutral_b = np.full_like(b, 128)
        
        lab_neutral = cv2.merge([enhanced_l, neutral_a, neutral_b])
        result = cv2.cvtColor(lab_neutral, cv2.COLOR_LAB2BGR)
        
        return result
        
    except Exception as e:
        print(f"⚠️ Background removal error: {e}, skip")
        return img_bgr


def _sharpen_text(img_gray, cv2, np):
    """
    Pertajam huruf yang pudar dengan unsharp masking.
    Lebih halus dari kernel sharpening biasa.
    """
    try:
        # Gaussian blur untuk unsharp mask
        blurred = cv2.GaussianBlur(img_gray, (0, 0), 3)
        
        # Unsharp masking: original + (original - blurred) * amount
        # amount = 2.0 lebih kuat untuk dokumen mesin ketik yang pudar
        sharpened = cv2.addWeighted(img_gray, 2.0, blurred, -1.0, 0)
        
        return sharpened
        
    except Exception as e:
        print(f"⚠️ Sharpen error: {e}, skip")
        return img_gray


def preprocess_gambar(gambar: Image.Image, enhance: bool = True) -> Image.Image:
    """
    Preprocessing KUAT untuk dokumen jadul/pudar.
    
    Fitur:
    1. Convert ke grayscale
    2. Hilangkan warna kuning/coklat kertas tua (jika berwarna)
    3. CLAHE - adaptive contrast enhancement
    4. Morphological dilation - TEBALKAN teks yang tipis/pudar
    5. Unsharp masking - pertajam teks
    
    Output: Grayscale yang sudah di-enhance dengan teks lebih tebal dan gelap.
    """
    if not enhance:
        return gambar
    
    try:
        import cv2
        import numpy as np
        
        # Convert PIL ke OpenCV format
        img_array = np.array(gambar.convert('RGB'))
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # STEP 1: Hilangkan warna kuning/coklat dari kertas tua
        # Konversi ke LAB dan neutralize warna
        try:
            lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            # Neutralize a,b channels (hilangkan warna kuning)
            neutral_a = np.full_like(a, 128)
            neutral_b = np.full_like(b, 128)
            lab_neutral = cv2.merge([l, neutral_a, neutral_b])
            img_neutral = cv2.cvtColor(lab_neutral, cv2.COLOR_LAB2BGR)
            gray = cv2.cvtColor(img_neutral, cv2.COLOR_BGR2GRAY)
            print("✅ Step 1: Warna kuning dihilangkan")
        except Exception:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # STEP 2: CLAHE - tingkatkan kontras secara adaptif
        # clipLimit lebih tinggi (4.0) untuk dokumen yang sangat pudar
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        print("✅ Step 2: Kontras ditingkatkan (CLAHE)")
        
        # STEP 3: Morphological DILATION - TEBALKAN teks yang tipis
        # Kernel kecil (2x2) supaya huruf tidak menyatu
        kernel = np.ones((2, 2), np.uint8)
        # Invert dulu (teks jadi putih), dilate, lalu invert balik
        inverted = cv2.bitwise_not(enhanced)
        dilated = cv2.dilate(inverted, kernel, iterations=1)
        thickened = cv2.bitwise_not(dilated)
        print("✅ Step 3: Teks ditebalkan (Morphological)")
        
        # STEP 4: Unsharp masking - pertajam tepi huruf
        blurred = cv2.GaussianBlur(thickened, (0, 0), 2)
        sharpened = cv2.addWeighted(thickened, 1.8, blurred, -0.8, 0)
        print("✅ Step 4: Teks dipertajam (Unsharp)")
        
        # STEP 5: Final contrast boost - gelapin teks lebih lagi
        # Pake simple contrast adjustment
        alpha = 1.3  # contrast multiplier
        beta = -30   # brightness offset (negatif = lebih gelap)
        final = cv2.convertScaleAbs(sharpened, alpha=alpha, beta=beta)
        print("✅ Step 5: Kontras final disesuaikan")
        
        # Convert balik ke PIL RGB
        result = Image.fromarray(final).convert('RGB')
        
        print("✅ Preprocessing selesai: Dokumen jadul enhanced!")
        return result
        
    except ImportError:
        # Fallback ke PIL-only kalau OpenCV tidak tersedia
        print("⚠️ OpenCV tidak tersedia, pakai fallback PIL preprocessing")
        return _preprocess_pil_fallback(gambar)
    except Exception as e:
        print(f"⚠️ OpenCV preprocessing error: {e}, pakai fallback")
        return _preprocess_pil_fallback(gambar)



def _preprocess_pil_fallback(gambar: Image.Image) -> Image.Image:
    """Fallback preprocessing pakai PIL saja kalau OpenCV tidak ada"""
    from PIL import ImageEnhance
    import numpy as np
    
    # Convert ke grayscale
    if gambar.mode != 'L':
        gambar_gray = gambar.convert('L')
    else:
        gambar_gray = gambar.copy()
    
    # Brightness + Contrast
    enhancer = ImageEnhance.Brightness(gambar_gray)
    gambar_bright = enhancer.enhance(1.3)
    
    enhancer = ImageEnhance.Contrast(gambar_bright)
    gambar_contrast = enhancer.enhance(3.0)
    
    # Simple threshold
    try:
        img_array = np.array(gambar_contrast)
        threshold = np.mean(img_array) + 20
        img_binary = np.where(img_array > threshold, 255, 0).astype(np.uint8)
        gambar_binary = Image.fromarray(img_binary, mode='L')
    except Exception:
        gambar_binary = gambar_contrast.point(lambda x: 255 if x > 140 else 0)
    
    return gambar_binary.convert('RGB')


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
    
    def baca_gambar(self, gambar: Image.Image) -> Tuple[str, List[float]]:
        """Ekstrak teks dari gambar, return (text, confidence_scores)"""
        import numpy as np
        
        # resize dulu kalau kegedean
        gambar = resize_gambar_kalau_perlu(gambar, settings.MAX_IMAGE_DIMENSION)
        
        # convert PIL ke numpy array
        img_array = np.array(gambar.convert("RGB"))
        
        # jalanin OCR - cls sesuai config
        hasil = self.ocr.ocr(img_array, cls=self._cls_enabled)
        
        # ambil teks dan confidence dari hasil
        texts = []
        confidences = []
        if hasil and hasil[0]:
            for line in hasil[0]:
                if line and len(line) >= 2:
                    texts.append(line[1][0])
                    # Confidence ada di line[1][1], biasanya 0-1
                    conf = line[1][1] if len(line[1]) > 1 else 0.8
                    confidences.append(float(conf))
        
        return "\n".join(texts), confidences


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
    
    def baca_gambar(self, gambar: Image.Image, bahasa: str = "mixed") -> Tuple[str, List[float]]:
        """Ekstrak teks dari gambar pake tesseract, return (text, confidence_scores)"""
        import subprocess
        import tempfile
        
        # resize dulu kalau kegedean
        gambar = resize_gambar_kalau_perlu(gambar, settings.MAX_IMAGE_DIMENSION)
        
        # simpen ke file temp
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path_temp = tmp.name
            gambar.save(path_temp, format="PNG")
        
        # Mapping bahasa ke tesseract language code
        # Untuk dokumen Indonesia lama, pakai kombinasi ind+eng
        lang_map = {
            "id": "ind",
            "en": "eng",
            "mixed": "ind+eng",  # Kombinasi untuk dokumen Indonesia dengan kata asing
        }
        lang_code = lang_map.get(bahasa, "ind+eng")
        
        try:
            # Get text
            hasil = subprocess.run(
                [
                    self.tesseract_cmd, 
                    path_temp, 
                    "stdout", 
                    "-l", lang_code,
                    "--oem", "3",  # LSTM OCR Engine
                    "--psm", "6",  # Uniform block of text
                ],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            output = hasil.stdout.strip() if hasil.stdout else ""
            
            # Get confidence with TSV output
            confidences = []
            try:
                tsv_result = subprocess.run(
                    [
                        self.tesseract_cmd, 
                        path_temp, 
                        "stdout", 
                        "-l", lang_code,
                        "--oem", "3",
                        "--psm", "6",
                        "tsv",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if tsv_result.stdout:
                    lines = tsv_result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        parts = line.split('\t')
                        if len(parts) >= 11 and parts[10]:  # conf column
                            try:
                                conf = float(parts[10])
                                if conf > 0:  # Skip -1 (no confidence)
                                    confidences.append(conf / 100.0)  # Normalize to 0-1
                            except ValueError:
                                pass
            except Exception:
                pass  # Fallback: no confidence data
            
            # Default confidence jika tidak ada data
            if not confidences:
                confidences = [0.75]  # Default 75%
            
            return output, confidences
        
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

    def baca_gambar(self, gambar: Image.Image, bahasa: str = "mixed", engine: str = None, enhance: bool = False) -> Tuple[str, List[float]]:
        """Baca text dari gambar dengan engine yang dipilih. Return (text, confidence_scores)"""
        # Preprocessing untuk dokumen jadul/pudar
        if enhance:
            gambar = preprocess_gambar(gambar, enhance=True)
        
        ocr_engine = self._get_engine(engine)
        
        # Tesseract mendukung parameter bahasa
        if isinstance(ocr_engine, TesseractEngine):
            return ocr_engine.baca_gambar(gambar, bahasa)
        else:
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

    def _proses_satu_halaman(self, args: Tuple[int, Image.Image, str, str, bool]) -> Tuple[int, str, List[float]]:
        """Helper buat parallel processing - proses satu halaman PDF"""
        idx, gambar, bahasa, engine, enhance = args
        text, confidences = self.baca_gambar(gambar, bahasa, engine, enhance)
        return idx, text, confidences

    def proses_file(
        self,
        data_file: bytes,
        nama_file: str,
        bahasa: str = "mixed",
        engine: str = None,
        enhance: bool = False
    ) -> Tuple[str, int, int, List[float]]:
        """
        Proses file (gambar atau PDF).
        
        Args:
            data_file: bytes dari file
            nama_file: nama file (untuk deteksi PDF)
            bahasa: bahasa dokumen (id/en/mixed)
            engine: pilihan engine (tesseract/paddle/auto)
            enhance: aktifkan preprocessing untuk dokumen jadul/pudar
        
        Return: (text, jumlah_halaman, waktu_ms, confidence_scores)
        """
        waktu_mulai = time.time()
        all_confidences = []

        is_pdf = nama_file.lower().endswith('.pdf')

        if is_pdf:
            list_gambar = self._convert_pdf_ke_gambar(data_file)
            jumlah_halaman = len(list_gambar)
            
            # parallel processing kalo enabled dan ada lebih dari 1 halaman
            if settings.PARALLEL_PDF_PROCESSING and jumlah_halaman > 1:
                hasil_per_halaman = {}
                confidences_per_halaman = {}
                
                max_workers = min(settings.PDF_WORKERS, jumlah_halaman)
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._proses_satu_halaman, (idx, gambar, bahasa, engine, enhance)): idx
                        for idx, gambar in enumerate(list_gambar)
                    }
                    
                    for future in as_completed(futures):
                        idx, text, confidences = future.result()
                        hasil_per_halaman[idx] = text
                        confidences_per_halaman[idx] = confidences
                
                semua_text = []
                for idx in range(jumlah_halaman):
                    text = hasil_per_halaman.get(idx, "")
                    if text:
                        semua_text.append(f"--- Halaman {idx + 1} ---\n{text}")
                    all_confidences.extend(confidences_per_halaman.get(idx, []))
                
                text_hasil = "\n\n".join(semua_text)
            else:
                semua_text = []
                for idx, gambar in enumerate(list_gambar):
                    text_halaman, confidences = self.baca_gambar(gambar, bahasa, engine, enhance)
                    if text_halaman:
                        semua_text.append(f"--- Halaman {idx + 1} ---\n{text_halaman}")
                    all_confidences.extend(confidences)
                text_hasil = "\n\n".join(semua_text)
        else:
            gambar = Image.open(io.BytesIO(data_file))
            text_hasil, all_confidences = self.baca_gambar(gambar, bahasa, engine, enhance)
            jumlah_halaman = 1

        waktu_proses = int((time.time() - waktu_mulai) * 1000)

        return text_hasil, jumlah_halaman, waktu_proses, all_confidences

    # alias buat backward compatibility
    def extract_text_from_bytes(self, file_bytes, filename, language="mixed", engine=None):
        text, pages, time_ms, _ = self.proses_file(file_bytes, filename, language, engine)
        return text, pages, time_ms


# singleton instance
ocr_service = OCRService()
