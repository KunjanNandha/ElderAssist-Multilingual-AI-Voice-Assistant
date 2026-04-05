"""
tts_engine.py
Converts text responses to speech using Google Text-to-Speech (gTTS).
Supports all major Indian languages with natural voice output.
"""

import os
import hashlib
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not available. Text-to-speech will be disabled.")


# gTTS language code mapping (some differ from ISO 639-1)
GTTS_LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "mr": "mr",
    "gu": "gu",
    "ta": "ta",
    "te": "te",
    "bn": "bn",
    "pa": "pa",
    "kn": "kn",
    "ml": "ml"
}

# Languages where gTTS support may be limited — fallback to Hindi TTS
FALLBACK_LANG = {
    "mr": "hi",   # gTTS has limited Marathi — Hindi is similar
}


class TTSEngine:
    """
    Text-to-speech engine with multilingual support.
    Caches generated audio files to reduce API calls.
    """

    def __init__(self, audio_dir: str):
        """
        Args:
            audio_dir: Directory to store generated audio files
        """
        self.audio_dir = audio_dir
        os.makedirs(audio_dir, exist_ok=True)
        logger.info(f"TTS Engine initialized. Audio dir: {audio_dir}")

    def synthesize(self, text: str, language: str = "en",
                   slow: bool = True) -> Optional[str]:
        """
        Convert text to speech and save as MP3.

        Args:
            text:     Text to speak
            language: Language code (e.g., 'hi', 'ta', 'en')
            slow:     Speak slowly (recommended for elderly users)

        Returns:
            Path to generated MP3 file, or None if failed
        """
        if not GTTS_AVAILABLE:
            logger.warning("gTTS not available, cannot synthesize speech")
            return None

        if not text or not text.strip():
            return None

        # Remove emoji characters (gTTS can't pronounce them)
        clean_text = self._remove_emoji(text)
        clean_text = clean_text[:500]  # Limit length

        # Check cache first
        cached = self._get_cached_path(clean_text, language, slow)
        if cached and os.path.exists(cached):
            return cached

        try:
            # Get gTTS language code
            gtts_lang = GTTS_LANG_MAP.get(language, "en")
            
            # Try primary language
            audio_path = self._generate_audio(clean_text, gtts_lang, slow)
            
            if audio_path:
                return audio_path

            # Fallback to English
            logger.warning(f"TTS failed for {language}, falling back to English")
            return self._generate_audio(clean_text, "en", slow)

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return None

    def _generate_audio(self, text: str, lang: str, slow: bool) -> Optional[str]:
        """Generate audio file using gTTS."""
        try:
            filename = self._make_filename(text, lang, slow)
            filepath = os.path.join(self.audio_dir, filename)

            if os.path.exists(filepath):
                return filepath

            tts = gTTS(text=text, lang=lang, slow=slow)
            tts.save(filepath)
            logger.info(f"Generated TTS audio: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"gTTS error for lang={lang}: {e}")
            return None

    def _make_filename(self, text: str, lang: str, slow: bool) -> str:
        """Create a unique filename based on content hash."""
        content = f"{text}:{lang}:{slow}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"tts_{lang}_{hash_val}.mp3"

    def _get_cached_path(self, text: str, lang: str, slow: bool) -> Optional[str]:
        """Return cached file path if it exists."""
        filename = self._make_filename(text, lang, slow)
        filepath = os.path.join(self.audio_dir, filename)
        return filepath if os.path.exists(filepath) else None

    def _remove_emoji(self, text: str) -> str:
        """Remove emoji characters that gTTS cannot handle."""
        import re
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "🚨🏥💊🏦🌤📰🏛"
            "]+", flags=re.UNICODE
        )
        return emoji_pattern.sub("", text).strip()

    def cleanup_old_files(self, max_age_hours: int = 24):
        """Remove audio files older than max_age_hours."""
        try:
            now = time.time()
            for f in os.listdir(self.audio_dir):
                if f.startswith("tts_") and f.endswith(".mp3"):
                    filepath = os.path.join(self.audio_dir, f)
                    if now - os.path.getmtime(filepath) > max_age_hours * 3600:
                        os.remove(filepath)
                        logger.debug(f"Removed old TTS file: {f}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
