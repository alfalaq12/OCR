"""
Service untuk menghitung Quality Score hasil OCR.

Composite scoring berdasarkan:
- Confidence Engine (40%): Rata-rata confidence dari OCR
- Dictionary Match (30%): Persentase kata yang ada di kamus
- Correction Rate (30%): Inverse dari persentase koreksi

Output: Skor 0-100 dengan label Excellent/Good/Fair/Poor
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
import re

# Import kamus dari dictionary_corrector
try:
    from app.services.dictionary_corrector import KAMUS_DOKUMEN, HAS_RAPIDFUZZ
except ImportError:
    KAMUS_DOKUMEN = set()
    HAS_RAPIDFUZZ = False


@dataclass
class QualityScoreResult:
    """Hasil scoring kualitas OCR"""
    overall: int              # 0-100
    label: str                # Excellent/Good/Fair/Poor
    confidence: float         # 0-100
    dictionary_match: float   # 0-100
    correction_rate: float    # 0-100 (higher = fewer corrections needed)
    total_words: int
    matched_words: int
    corrected_words: int


# Bobot untuk setiap komponen
WEIGHT_CONFIDENCE = 0.40
WEIGHT_DICTIONARY = 0.30
WEIGHT_CORRECTION = 0.30


def _get_quality_label(score: int) -> str:
    """
    Tentukan label kualitas berdasarkan score.
    
    85-100: Excellent ⭐
    70-84:  Good ✅
    50-69:  Fair ⚠️
    0-49:   Poor ❌
    """
    if score >= 85:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Fair"
    else:
        return "Poor"


def _extract_words(text: str) -> List[str]:
    """
    Ekstrak kata-kata dari teks untuk analisis.
    Skip angka, simbol, dan kata pendek (<3 huruf).
    """
    if not text:
        return []
    
    # Split berdasarkan non-word characters
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    return words


def _calculate_dictionary_match(words: List[str]) -> Tuple[float, int, int]:
    """
    Hitung persentase kata yang ada di kamus.
    
    Returns: (match_percentage, matched_count, total_count)
    """
    if not words:
        return 100.0, 0, 0
    
    matched = 0
    for word in words:
        if word.lower() in KAMUS_DOKUMEN:
            matched += 1
    
    total = len(words)
    percentage = (matched / total * 100) if total > 0 else 100.0
    
    return percentage, matched, total


def _calculate_correction_rate(total_words: int, corrected_words: int) -> float:
    """
    Hitung skor berdasarkan correction rate.
    Semakin sedikit koreksi = skor lebih tinggi.
    
    Formula: 100 - (corrected / total * 100)
    """
    if total_words == 0:
        return 100.0
    
    correction_percentage = (corrected_words / total_words) * 100
    # Inverse: 100% correction = 0 score, 0% correction = 100 score
    score = max(0, 100 - correction_percentage)
    
    return score


def _calculate_confidence_score(confidence_scores: List[float]) -> float:
    """
    Hitung rata-rata confidence dari OCR engine.
    Confidence biasanya dalam range 0-1 atau 0-100.
    """
    if not confidence_scores:
        return 75.0  # Default kalau tidak ada data
    
    avg = sum(confidence_scores) / len(confidence_scores)
    
    # Normalize ke 0-100 jika dalam range 0-1
    if avg <= 1.0:
        avg = avg * 100
    
    return min(100.0, max(0.0, avg))


def calculate_quality_score(
    text: str,
    confidence_scores: Optional[List[float]] = None,
    dictionary_corrections: int = 0
) -> QualityScoreResult:
    """
    Hitung composite quality score untuk hasil OCR.
    
    Args:
        text: Teks hasil OCR
        confidence_scores: List confidence values dari OCR engine (0-1 atau 0-100)
        dictionary_corrections: Jumlah kata yang dikoreksi oleh dictionary_corrector
    
    Returns:
        QualityScoreResult dengan breakdown lengkap
    """
    # Ekstrak kata untuk analisis
    words = _extract_words(text)
    total_words = len(words)
    
    # 1. Confidence Score (dari engine)
    confidence_score = _calculate_confidence_score(confidence_scores or [])
    
    # 2. Dictionary Match Score
    dict_match_percentage, matched_words, _ = _calculate_dictionary_match(words)
    
    # 3. Correction Rate Score
    correction_score = _calculate_correction_rate(total_words, dictionary_corrections)
    
    # Composite Score
    overall = int(
        confidence_score * WEIGHT_CONFIDENCE +
        dict_match_percentage * WEIGHT_DICTIONARY +
        correction_score * WEIGHT_CORRECTION
    )
    overall = min(100, max(0, overall))
    
    label = _get_quality_label(overall)
    
    return QualityScoreResult(
        overall=overall,
        label=label,
        confidence=round(confidence_score, 1),
        dictionary_match=round(dict_match_percentage, 1),
        correction_rate=round(correction_score, 1),
        total_words=total_words,
        matched_words=matched_words,
        corrected_words=dictionary_corrections
    )


# Quick test
if __name__ == "__main__":
    test_text = """
    DEPARTEMEN PEKERJAAN UMUM
    Jalan Kramat Jakarta
    Nomor 2078 tanggal 15 November 1965
    Kepada Yth. Direktur
    """
    
    result = calculate_quality_score(
        text=test_text,
        confidence_scores=[0.92, 0.88, 0.95, 0.78, 0.85],
        dictionary_corrections=3
    )
    
    print("=== Quality Score Test ===")
    print(f"Overall: {result.overall}/100 ({result.label})")
    print(f"├─ Confidence: {result.confidence}%")
    print(f"├─ Dictionary Match: {result.dictionary_match}%")
    print(f"├─ Correction Rate: {result.correction_rate}%")
    print(f"└─ Words: {result.matched_words}/{result.total_words} matched, {result.corrected_words} corrected")
