import io
import time
import subprocess
import tempfile
import os
from typing import Tuple
from PIL import Image


class OCRService:
    """Service for OCR processing using Tesseract (direct subprocess call)"""

    def __init__(self):
        # Tesseract executable path
        self.tesseract_cmd = self._find_tesseract()
        # Poppler path for PDF conversion
        self.poppler_path = self._find_poppler()

    def _find_tesseract(self) -> str:
        """Find Tesseract executable"""
        paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "tesseract"
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
            try:
                result = subprocess.run([path, "--version"], capture_output=True)
                if result.returncode == 0:
                    return path
            except FileNotFoundError:
                continue
        
        return "tesseract"

    def _find_poppler(self) -> str:
        """Find Poppler bin directory"""
        paths = [
            r"C:\poppler\bin",
            r"C:\Program Files\poppler\bin",
            r"C:\poppler-24.02.0\Library\bin",
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
        
        return None

    def _get_lang_code(self, language: str) -> str:
        """Convert language param to Tesseract language code"""
        if language == "id":
            return "ind"
        elif language == "en":
            return "eng"
        else:
            return "eng"  # Default to English to avoid missing language data error

    def extract_text_from_image(self, image: Image.Image, language: str = "mixed") -> str:
        """Extract text from a PIL Image using Tesseract subprocess"""
        lang_code = self._get_lang_code(language)
        
        # Save image to temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            image.save(tmp_path, format="PNG")
        
        try:
            # Run Tesseract
            cmd = [
                self.tesseract_cmd,
                tmp_path,
                "stdout",
                "-l", lang_code,
                "--oem", "3",
                "--psm", "6"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown Tesseract error"
                raise Exception(f"Tesseract error: {error_msg}")
            
            output = result.stdout
            if output is None:
                return ""
            
            return output.strip()
        
        except subprocess.TimeoutExpired:
            raise Exception("OCR processing timeout (>120s)")
        except FileNotFoundError:
            raise Exception(f"Tesseract not found at: {self.tesseract_cmd}")
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

    def _convert_pdf_to_images(self, file_bytes: bytes) -> list:
        """Convert PDF to list of PIL Images"""
        try:
            from pdf2image import convert_from_bytes
            
            kwargs = {"dpi": 200}
            if self.poppler_path:
                kwargs["poppler_path"] = self.poppler_path
            
            return convert_from_bytes(file_bytes, **kwargs)
        
        except Exception as e:
            error_str = str(e).lower()
            if "poppler" in error_str or "pdftoppm" in error_str:
                raise Exception(
                    "Poppler is not installed or not found. "
                    "Please install Poppler and add to PATH, or set poppler_path. "
                    "Download from: https://github.com/osber/poppler-windows/releases"
                )
            raise Exception(f"PDF conversion error: {str(e)}")

    def extract_text_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        language: str = "mixed"
    ) -> Tuple[str, int, int]:
        """
        Extract text from file bytes (image or PDF)
        Returns: (extracted_text, page_count, processing_time_ms)
        """
        start_time = time.time()

        # Check if PDF
        is_pdf = filename.lower().endswith('.pdf')

        if is_pdf:
            # Convert PDF to images
            images = self._convert_pdf_to_images(file_bytes)
            all_text = []

            for i, img in enumerate(images):
                page_text = self.extract_text_from_image(img, language)
                if page_text:
                    all_text.append(f"--- Page {i + 1} ---\n{page_text}")

            text = "\n\n".join(all_text)
            pages = len(images)
        else:
            # Process as image
            image = Image.open(io.BytesIO(file_bytes))
            text = self.extract_text_from_image(image, language)
            pages = 1

        processing_time = int((time.time() - start_time) * 1000)

        return text, pages, processing_time


# Singleton instance
ocr_service = OCRService()
