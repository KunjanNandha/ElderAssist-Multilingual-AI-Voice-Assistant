import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Whisper model configuration
# Options: 'tiny', 'base', 'small', 'medium', 'large'
# 'tiny' or 'base' recommended for CPU-only machines
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "mr": "Marathi (मराठी)",
    "gu": "Gujarati (ગુજરાતી)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "bn": "Bengali (বাংলা)"
}

# Language to gTTS language code mapping
GTTS_LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "mr": "mr",
    "gu": "gu",
    "ta": "ta",
    "te": "te",
    "bn": "bn"
}

# Flask settings
DEBUG = os.getenv("DEBUG", "True") == "True"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))

# Upload and audio settings
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "audio")
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

# Intent data
INTENTS_FILE = os.path.join(BASE_DIR, "data", "intents.json")

# Emergency contacts
EMERGENCY_CONTACTS = {
    "police": "100",
    "ambulance": "108",
    "emergency": "112",
    "senior_helpline": "14567",
    "health_helpline": "104",
    "women_helpline": "181",
    "aadhaar": "1947"
}
