"""
language_detector.py
Detects the language of text input using multiple methods:
1. langdetect library (primary)
2. Script-based detection (fallback) - detects Devanagari, Tamil, Telugu, etc.
3. Keyword-based detection (secondary fallback)
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import langdetect
try:
    from langdetect import detect, detect_langs, DetectorFactory
    DetectorFactory.seed = 42  # For reproducibility
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not available, using script-based detection only")


# Unicode script ranges for Indian languages
SCRIPT_RANGES = {
    "hi": (0x0900, 0x097F),   # Devanagari (Hindi, Marathi, Nepali)
    "gu": (0x0A80, 0x0AFF),   # Gujarati
    "ta": (0x0B80, 0x0BFF),   # Tamil
    "te": (0x0C00, 0x0C7F),   # Telugu
    "kn": (0x0C80, 0x0CFF),   # Kannada
    "ml": (0x0D00, 0x0D7F),   # Malayalam
    "bn": (0x0980, 0x09FF),   # Bengali
    "pa": (0x0A00, 0x0A7F),   # Punjabi (Gurmukhi)
    "or": (0x0B00, 0x0B7F),   # Odia
}

# Marathi-specific common words (to distinguish from Hindi - both use Devanagari)
MARATHI_KEYWORDS = {
    "आहे", "नाही", "मला", "तुम्ही", "काय", "कसे", "केव्हा", "कुठे",
    "करा", "सांगा", "मदत", "धन्यवाद", "ठीक", "हो", "नाही"
}

HINDI_KEYWORDS = {
    "है", "नहीं", "मुझे", "आप", "क्या", "कैसे", "कब", "कहाँ",
    "करें", "बताएं", "मदद", "धन्यवाद", "ठीक", "हाँ", "नहीं", "हूँ"
}


class LanguageDetector:
    """
    Detects language from text using multiple strategies.
    Optimized for Indian regional languages.
    """

    SUPPORTED = {
        "en": "English",
        "hi": "Hindi",
        "mr": "Marathi",
        "gu": "Gujarati",
        "ta": "Tamil",
        "te": "Telugu",
        "bn": "Bengali",
        "pa": "Punjabi",
        "kn": "Kannada",
        "ml": "Malayalam"
    }

    def detect(self, text: str, whisper_lang: Optional[str] = None) -> str:
        """
        Detect language from text.

        Strategy:
        1. If Whisper already detected the language, trust it (for speech)
        2. Script-based detection (very reliable for Indian scripts)
        3. langdetect (for Latin-script languages)
        4. Default to English

        Args:
            text:        Input text to detect language from
            whisper_lang: Language already detected by Whisper (optional)

        Returns:
            ISO 639-1 language code
        """
        if not text or not text.strip():
            return whisper_lang or "en"

        text = text.strip()

        # 1. Trust Whisper's language detection (it's very accurate for speech)
        if whisper_lang and whisper_lang in self.SUPPORTED:
            # But differentiate Hindi vs Marathi (both Devanagari)
            if whisper_lang == "hi":
                return self._distinguish_hindi_marathi(text)
            return whisper_lang

        # 2. Script-based detection
        script_lang = self._detect_by_script(text)
        if script_lang:
            if script_lang == "hi":
                return self._distinguish_hindi_marathi(text)
            return script_lang

        # 3. langdetect for Latin script
        if LANGDETECT_AVAILABLE:
            try:
                lang = detect(text)
                if lang in self.SUPPORTED:
                    return lang
            except Exception:
                pass

        return "en"

    def _detect_by_script(self, text: str) -> Optional[str]:
        """Detect language based on Unicode script range."""
        char_counts = {lang: 0 for lang in SCRIPT_RANGES}

        for char in text:
            cp = ord(char)
            for lang, (start, end) in SCRIPT_RANGES.items():
                if start <= cp <= end:
                    char_counts[lang] += 1

        if not any(char_counts.values()):
            return None

        dominant = max(char_counts, key=char_counts.get)
        if char_counts[dominant] > 0:
            return dominant
        return None

    def _distinguish_hindi_marathi(self, text: str) -> str:
        """
        Both Hindi and Marathi use Devanagari script.
        Use keyword frequency to distinguish them.
        """
        words = set(text.split())
        marathi_score = len(words & MARATHI_KEYWORDS)
        hindi_score = len(words & HINDI_KEYWORDS)

        if marathi_score > hindi_score:
            return "mr"
        return "hi"

    def get_language_name(self, code: str) -> str:
        """Get human-readable language name from code."""
        return self.SUPPORTED.get(code, "Unknown")
