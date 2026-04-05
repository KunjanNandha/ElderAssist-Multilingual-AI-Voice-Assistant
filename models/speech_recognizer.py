"""
speech_recognizer.py
Handles speech-to-text conversion using OpenAI Whisper.
Whisper natively supports 99+ languages including all major Indian languages.
"""

import whisper
import numpy as np
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """
    Multilingual speech recognizer using OpenAI Whisper.
    Automatically detects language and transcribes speech.
    """

    def __init__(self, model_size: str = "base"):
        """
        Initialize the Whisper model.

        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                        'tiny'  - Fastest, least accurate (~39M params)
                        'base'  - Good balance for CPU (~74M params)  ← Recommended
                        'small' - Better accuracy (~244M params)
                        'medium'- High accuracy (~769M params)
        """
        logger.info(f"Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)
        self.model_size = model_size
        logger.info("Whisper model loaded successfully")

    def transcribe_file(self, audio_path: str, language: str = None) -> dict:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file (WAV, MP3, WebM, etc.)
            language:   Optional language hint (e.g., 'hi', 'mr', 'en')
                        If None, Whisper will auto-detect the language.

        Returns:
            dict with keys:
                'text'     - Transcribed text
                'language' - Detected language code
                'segments' - Time-stamped segments
                'success'  - Boolean
        """
        try:
            if not os.path.exists(audio_path):
                return {"success": False, "error": "Audio file not found"}

            # Transcribe with Whisper
            options = {
                "task": "transcribe",
                "fp16": False,  # Use FP32 for CPU compatibility
            }

            if language and language != "auto":
                options["language"] = language

            result = self.model.transcribe(audio_path, **options)

            return {
                "success": True,
                "text": result["text"].strip(),
                "language": result.get("language", "en"),
                "segments": result.get("segments", [])
            }

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "language": "en"
            }

    def transcribe_bytes(self, audio_bytes: bytes, filename: str = "audio.webm") -> dict:
        """
        Transcribe audio from bytes (e.g., uploaded file content).

        Args:
            audio_bytes: Raw audio bytes
            filename:    Original filename for format detection

        Returns:
            Same as transcribe_file()
        """
        try:
            # Write to temp file
            suffix = os.path.splitext(filename)[1] or ".webm"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            result = self.transcribe_file(tmp_path)

            # Cleanup
            os.unlink(tmp_path)
            return result

        except Exception as e:
            logger.error(f"Error transcribing bytes: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "language": "en"
            }

    def detect_language(self, audio_path: str) -> str:
        """
        Detect the language of speech in an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            ISO 639-1 language code (e.g., 'hi', 'en', 'ta')
        """
        try:
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            _, probs = self.model.detect_language(mel)
            return max(probs, key=probs.get)
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return "en"
