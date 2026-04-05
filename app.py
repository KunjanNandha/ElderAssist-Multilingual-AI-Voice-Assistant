"""
app.py  —  ElderAssist Backend (Flask)
========================================
Routes:
  GET  /                  → Serve frontend
  POST /api/transcribe    → Audio → text (Whisper)
  POST /api/chat          → Text → intent + response + TTS
  POST /api/process       → Full pipeline: audio → text → intent → TTS
  GET  /api/languages     → List supported languages
  GET  /api/health        → Health check
  GET  /static/audio/<f>  → Serve generated audio files
"""

import os
import logging
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

import config
from models import SpeechRecognizer, LanguageDetector, IntentClassifier, TTSEngine, ReminderScheduler

# ─────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Flask app
# ─────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="static")
CORS(app)  # Allow frontend to call API from any origin

app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# ─────────────────────────────────────────────
# Model initialization (lazy — loaded on first request)
# ─────────────────────────────────────────────
_models = {}


def get_models():
    """Initialize models once and cache them."""
    if not _models:
        logger.info("Initializing AI models...")
        start = time.time()

        _models["speech"] = SpeechRecognizer(model_size=config.WHISPER_MODEL)
        _models["lang_detector"] = LanguageDetector()
        _models["intent"] = IntentClassifier(config.INTENTS_FILE)
        _models["tts"] = TTSEngine(config.UPLOAD_FOLDER)
        _models["reminders"] = ReminderScheduler(
            tts_engine=_models["tts"],
            storage_path=os.path.join(config.BASE_DIR, "data", "reminders.json")
        )
        _models["reminders"].start()

        logger.info(f"All models loaded in {time.time()-start:.1f}s")
    return _models


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main HTML frontend."""
    return send_file(os.path.join(app.static_folder, "index.html"))


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "whisper_model": config.WHISPER_MODEL,
        "supported_languages": config.SUPPORTED_LANGUAGES
    })


@app.route("/api/languages")
def languages():
    """Return list of supported languages."""
    return jsonify({
        "languages": config.SUPPORTED_LANGUAGES
    })


@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    """
    Transcribe audio file to text using Whisper.

    Request: multipart/form-data
        audio    - Audio file (WAV, WebM, MP3, etc.)
        language - Optional: hint the language ('hi', 'en', etc.)

    Response JSON:
        text     - Transcribed text
        language - Detected language code
        success  - Boolean
    """
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    language_hint = request.form.get("language", None)

    if audio_file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    try:
        models = get_models()
        audio_bytes = audio_file.read()
        result = models["speech"].transcribe_bytes(
            audio_bytes,
            filename=audio_file.filename or "audio.webm"
        )
        return jsonify(result)

    except Exception as e:
        logger.error(f"Transcription route error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Process text input: detect language, classify intent, generate response + TTS.

    Request JSON:
        text      - User's text message
        language  - Optional: override language detection ('hi', 'en', etc.)
        tts       - Optional: generate TTS audio (default: true)
        whisper_lang - Optional: language detected by Whisper (for better accuracy)

    Response JSON:
        text      - Original user text
        language  - Detected language code
        language_name - Full language name
        intent    - Classified intent tag
        confidence - Intent confidence score (0-1)
        response  - Text response in detected language
        audio_url - URL to generated MP3 (if tts=true)
        success   - Boolean
    """
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    lang_override = data.get("language", None)
    generate_tts = data.get("tts", True)
    whisper_lang = data.get("whisper_lang", None)

    if not text:
        return jsonify({"success": False, "error": "No text provided"}), 400

    try:
        models = get_models()

        # 1. Detect language
        language = lang_override or models["lang_detector"].detect(text, whisper_lang)
        lang_name = models["lang_detector"].get_language_name(language)

        # 2. Classify intent
        intent_tag, confidence = models["intent"].classify(text)

        # 3. Get response in detected language
        response_text = models["intent"].get_response(intent_tag, language)

        # 4. Generate TTS audio
        audio_url = None
        if generate_tts:
            audio_path = models["tts"].synthesize(response_text, language, slow=True)
            if audio_path:
                audio_filename = os.path.basename(audio_path)
                audio_url = f"/static/audio/{audio_filename}"

        return jsonify({
            "success": True,
            "text": text,
            "language": language,
            "language_name": lang_name,
            "intent": intent_tag,
            "confidence": round(confidence, 3),
            "response": response_text,
            "audio_url": audio_url
        })

    except Exception as e:
        logger.error(f"Chat route error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/process", methods=["POST"])
def process_audio():
    """
    Full pipeline: Audio → Transcription → Language Detection → Intent → Response + TTS

    Request: multipart/form-data
        audio       - Audio file (WAV, WebM, MP3)
        language    - Optional language override
        tts         - Optional: generate TTS (default: true)

    Response JSON: Same as /api/chat plus:
        transcription - The transcribed text from speech
    """
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    lang_override = request.form.get("language", None)
    generate_tts = request.form.get("tts", "true").lower() == "true"

    try:
        models = get_models()

        # Step 1: Transcribe speech
        audio_bytes = audio_file.read()
        transcription = models["speech"].transcribe_bytes(
            audio_bytes,
            filename=audio_file.filename or "audio.webm"
        )

        if not transcription["success"] or not transcription["text"]:
            return jsonify({
                "success": False,
                "error": "Could not transcribe audio. Please speak clearly and try again.",
                "transcription": ""
            }), 422

        text = transcription["text"]
        whisper_lang = transcription.get("language")

        # Step 2: Detect language (using Whisper's detection + our detector)
        language = lang_override or models["lang_detector"].detect(text, whisper_lang)
        lang_name = models["lang_detector"].get_language_name(language)

        # Step 3: Classify intent
        intent_tag, confidence = models["intent"].classify(text)

        # Step 4: Generate response
        response_text = models["intent"].get_response(intent_tag, language)

        # Step 5: Generate TTS
        audio_url = None
        if generate_tts:
            audio_path = models["tts"].synthesize(response_text, language, slow=True)
            if audio_path:
                audio_filename = os.path.basename(audio_path)
                audio_url = f"/static/audio/{audio_filename}"

        return jsonify({
            "success": True,
            "transcription": text,
            "text": text,
            "language": language,
            "language_name": lang_name,
            "intent": intent_tag,
            "confidence": round(confidence, 3),
            "response": response_text,
            "audio_url": audio_url
        })

    except Exception as e:
        logger.error(f"Process route error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/static/audio/<filename>")
def serve_audio(filename):
    """Serve generated TTS audio files."""
    return send_from_directory(config.UPLOAD_FOLDER, filename)


@app.route("/api/reminders", methods=["GET"])
def list_reminders():
    """Return all medicine reminders."""
    try:
        models = get_models()
        return jsonify({"success": True, "reminders": models["reminders"].get_all()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reminders", methods=["POST"])
def add_reminder():
    """
    Add a medicine reminder.

    Request JSON:
        medicine_name  - Name of the medicine
        times          - List of "HH:MM" strings OR
        frequency      - int (1–4): auto-space times through the day
        language       - Language code (default: 'en')
        notes          - Optional notes
    """
    data = request.get_json(force=True, silent=True) or {}
    medicine = data.get("medicine_name", "").strip()
    times     = data.get("times", [])
    frequency = data.get("frequency")
    language  = data.get("language", "en")
    notes     = data.get("notes", "")

    if not medicine:
        return jsonify({"success": False, "error": "medicine_name is required"}), 400

    if not times and not frequency:
        return jsonify({"success": False, "error": "Provide 'times' or 'frequency'"}), 400

    try:
        models = get_models()
        reminder = models["reminders"].add_reminder(
            medicine_name=medicine,
            times=times,
            language=language,
            notes=notes,
            frequency=int(frequency) if frequency else None
        )
        return jsonify({"success": True, "reminder": reminder.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reminders/<reminder_id>", methods=["DELETE"])
def delete_reminder(reminder_id):
    """Delete a reminder by ID."""
    try:
        models = get_models()
        removed = models["reminders"].remove_reminder(reminder_id)
        if removed:
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Reminder not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reminders/<reminder_id>/toggle", methods=["POST"])
def toggle_reminder(reminder_id):
    """Toggle a reminder active/inactive."""
    try:
        models = get_models()
        new_state = models["reminders"].toggle_reminder(reminder_id)
        if new_state is None:
            return jsonify({"success": False, "error": "Reminder not found"}), 404
        return jsonify({"success": True, "active": new_state})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.errorhandler(413)
def too_large(e):
    return jsonify({"success": False, "error": "Audio file too large (max 16MB)"}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("  ElderAssist AI Voice Assistant")
    logger.info(f"  Starting on http://{config.HOST}:{config.PORT}")
    logger.info(f"  Whisper model: {config.WHISPER_MODEL}")
    logger.info("=" * 50)

    # Preload models on startup
    get_models()

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
