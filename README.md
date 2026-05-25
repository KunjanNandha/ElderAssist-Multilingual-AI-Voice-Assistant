# 🎙️ ElderAssist — Multilingual AI Voice Assistant

> **MTech DSA Mini Project (DADS CSD40070)**  
> · Kunjan Nandha (1262252041)  


---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [System Architecture](#-system-architecture)
3. [Project Structure](#-project-structure)
4. [Prerequisites](#-prerequisites)
5. [Installation & Setup](#-installation--setup)
6. [How to Run](#-how-to-run)
7. [API Reference](#-api-reference)
8. [Supported Languages](#-supported-languages)
9. [Supported Intents](#-supported-intents)
10. [Model Details](#-model-details)
11. [Datasets Used](#-datasets-used)
12. [Troubleshooting](#-troubleshooting)
13. [References](#-references)

---

## 🏗 Project Overview

ElderAssist is a multilingual AI-powered voice assistant designed **specifically for elderly users** in India who face digital barriers due to regional language diversity and low digital literacy.

### Key Features
- 🎤 **Voice Input** — Record speech directly in browser (no app install needed)
- 🌐 **7+ Languages** — Hindi, Marathi, Gujarati, Tamil, Telugu, Bengali, English
- 🤖 **Automatic Language Detection** — No need to manually select language
- 💡 **Intent Classification** — Understands what the user wants (doctor, medicine, emergency, banking, etc.)
- 🔊 **Text-to-Speech** — Reads responses aloud in the user's language
- 🚨 **Emergency Override** — Always detects emergency keywords regardless of other context
- 📱 **Elderly-Friendly UI** — Large buttons, high contrast, simple layout
- ⌨️ **Text Fallback** — Can also accept typed input

---

## 🏛 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         BROWSER (Frontend)                      │
│   ┌──────────────┐   ┌─────────────────┐   ┌────────────────┐  │
│   │  Mic Button  │   │  Language Select │   │  Text Input    │  │
│   │  (MediaRec.) │   │  (7 languages)   │   │  + Quick BTNs  │  │
│   └──────┬───────┘   └────────┬────────┘   └───────┬────────┘  │
│          │                    │                     │           │
│          └──────── HTTP/POST (FormData / JSON) ─────┘           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Flask API Server   │
                    │      (app.py)        │
                    └─────────┬───────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   ┌──────▼──────┐   ┌────────▼───────┐   ┌──────▼──────┐
   │   Whisper   │   │    Language    │   │    gTTS     │
   │ ASR Model   │   │    Detector    │   │ TTS Engine  │
   │(speech→text)│   │(script-based)  │   │(text→audio) │
   └──────┬──────┘   └────────┬───────┘   └─────────────┘
          │                   │
          └──────────┬────────┘
                     │
            ┌────────▼────────┐
            │ Intent Classifier│
            │ (TF-IDF + LR)   │
            │ 10 intent classes│
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │ Response Engine  │
            │ (multilingual   │
            │  response dict)  │
            └─────────────────┘
```

### Pipeline Flow

```
Audio → [Whisper ASR] → Text → [Language Detector] → Lang Code
                                                          ↓
Response ← [Response Engine] ← [Intent Classifier] ← Intent Tag
    ↓
[gTTS] → MP3 → Browser plays audio
```

---

## 📁 Project Structure

```
ElderAssist/
│
├── app.py                     # Flask backend — main server
├── config.py                  # Configuration (model, ports, languages)
├── requirements.txt           # Python dependencies
├── run.sh                     # One-click startup script (Linux/macOS)
│
├── models/                    # AI/ML model modules
│   ├── __init__.py
│   ├── speech_recognizer.py   # Whisper-based ASR
│   ├── language_detector.py   # Script + keyword based lang detection
│   ├── intent_classifier.py   # TF-IDF + Logistic Regression
│   └── tts_engine.py          # gTTS text-to-speech
│
├── data/
│   └── intents.json           # Multilingual intent patterns + responses
│
└── static/                    # Frontend files
    ├── index.html             # Main UI page
    ├── css/
    │   └── style.css          # Elderly-friendly styling
    ├── js/
    │   └── app.js             # Frontend logic (recording, API calls)
    └── audio/                 # Generated TTS audio (auto-created)
```

---

## ✅ Prerequisites

### Software

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python      | 3.9+    | [python.org](https://python.org) |
| pip         | latest  | `python -m pip install --upgrade pip` |
| ffmpeg      | any     | Required by Whisper |
| Modern browser | Chrome/Firefox/Edge | For microphone API |

### Install ffmpeg

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Windows (winget)
winget install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM       | 4 GB    | 8 GB        |
| CPU       | 2 cores | 4+ cores    |
| Disk      | 1 GB    | 2 GB        |
| GPU       | Not required (CPU works) | NVIDIA GPU (faster) |

> **Whisper Model Sizes** (first run downloads automatically):
> - `tiny`  — 39M params — ~1GB RAM — fastest, good enough for most
> - `base`  — 74M params — ~1GB RAM — **recommended balance** ✅
> - `small` — 244M params — ~2GB RAM — better accuracy
> - `medium`— 769M params — ~5GB RAM — high accuracy
>
> Change model in `config.py`: `WHISPER_MODEL = "tiny"` for slower machines.

---

## 🚀 Installation & Setup

### Option A: Automatic (Linux/macOS)

```bash
# Clone or unzip the project
cd ElderAssist

# Make startup script executable
chmod +x run.sh

# Run! (installs everything automatically on first run)
./run.sh
```

### Option B: Manual (Windows / All OS)

**Step 1 — Create virtual environment**
```bash
cd ElderAssist
python -m venv venv
```

**Step 2 — Activate virtual environment**
```bash
# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

**Step 3 — Install Python packages**
```bash
pip install -r requirements.txt
```

> ⏳ First install takes 5–10 minutes (downloads Whisper, PyTorch, etc.)

**Step 4 — (Optional) Configure model size**

Edit `config.py`:
```python
WHISPER_MODEL = "tiny"   # Fastest, for low-RAM machines
# WHISPER_MODEL = "base"  # Default recommended
```

---

## ▶️ How to Run

```bash
# With virtual environment activated:
python app.py
```

Or use the startup script:
```bash
./run.sh               # Uses 'base' model by default
WHISPER_MODEL=tiny ./run.sh   # Use tiny model (faster)
```

Then open your browser:
```
http://localhost:5000
```

> **First startup is slow** — Whisper downloads the model (~140MB for base). Subsequent starts are fast.

---

## 🌐 API Reference

### Health Check
```
GET /api/health
```
```json
{
  "status": "ok",
  "whisper_model": "base",
  "supported_languages": { "en": "English", "hi": "Hindi (हिन्दी)", ... }
}
```

---

### Process Audio (Full Pipeline)
```
POST /api/process
Content-Type: multipart/form-data

Fields:
  audio     (file)   - Audio file: WebM, WAV, MP3, OGG
  language  (string) - Optional: 'hi', 'mr', 'en', etc.
  tts       (string) - Optional: 'true'/'false' (default: 'true')
```
```json
{
  "success": true,
  "transcription": "मुझे डॉक्टर से मिलना है",
  "language": "hi",
  "language_name": "Hindi",
  "intent": "appointment",
  "confidence": 0.87,
  "response": "मैं आपको डॉक्टर की अपॉइंटमेंट बुक करने में...",
  "audio_url": "/static/audio/tts_hi_abc123.mp3"
}
```

---

### Chat (Text Input)
```
POST /api/chat
Content-Type: application/json

Body:
{
  "text":     "I need to see a doctor",
  "language": "en",       // Optional
  "tts":      true        // Optional
}
```
Response: Same format as `/api/process`

---

### List Languages
```
GET /api/languages
```
```json
{
  "languages": {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "mr": "Marathi (मराठी)",
    "gu": "Gujarati (ગુજરાતી)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "bn": "Bengali (বাংলা)"
  }
}
```

---

## 🌍 Supported Languages

| Code | Language | Script | Sample |
|------|----------|--------|--------|
| `en` | English  | Latin      | "Doctor appointment please" |
| `hi` | Hindi    | Devanagari | "डॉक्टर से मिलना है" |
| `mr` | Marathi  | Devanagari | "डॉक्टरांना भेटायचे आहे" |
| `gu` | Gujarati | Gujarati   | "ડૉક્ટર ઍપોઇન્ટમેન્ટ જોઈએ" |
| `ta` | Tamil    | Tamil      | "டாக்டர் அப்பாயின்ட்மென்ட்" |
| `te` | Telugu   | Telugu     | "డాక్టర్ అపాయింట్‌మెంట్" |
| `bn` | Bengali  | Bengali    | "ডাক্তারের অ্যাপয়েন্টমেন্ট" |

---

## 💡 Supported Intents

| Intent | Description | Examples |
|--------|-------------|---------|
| `greeting` | User says hello | "namaste", "hello", "नमस्ते" |
| `farewell` | User says goodbye | "bye", "alvida", "अलविदा" |
| `appointment` | Book doctor visit | "doctor appointment", "डॉक्टर से मिलना" |
| `medicine_reminder` | Set medicine reminder | "medicine time", "दवाई याद दिलाओ" |
| `emergency` | 🚨 URGENT help needed | "help me", "ambulance", "आपातकाल" |
| `banking` | Banking queries | "bank balance", "बैंक बैलेंस" |
| `weather` | Weather info | "weather today", "मौसम" |
| `government_services` | Govt. scheme help | "aadhaar", "pension", "आधार" |
| `news` | News updates | "latest news", "समाचार" |
| `help` | General help | "what can you do", "मदद" |

> ⚠️ **Emergency intents always override** the classifier — any emergency keyword triggers the emergency response regardless of confidence score.

---

## 🤖 Model Details

### 1. Speech Recognition — OpenAI Whisper
- **Model**: `whisper-base` (configurable)
- **Why**: Natively multilingual, works offline, handles Indian accents
- **Languages**: 99+ languages including all Indian languages
- **Input**: Audio file (WAV/WebM/MP3/OGG)
- **Output**: Text + detected language code

### 2. Language Detection
- **Primary**: Script-based Unicode range detection (Devanagari, Gujarati, Tamil, Telugu, Bengali)
- **Secondary**: `langdetect` library for Latin-script text
- **Special case**: Hindi/Marathi disambiguation via keyword sets (both use Devanagari)
- **Accuracy**: ~95%+ for Indian scripts

### 3. Intent Classification — TF-IDF + Logistic Regression
- **Vectorizer**: Character n-gram TF-IDF (2–4 grams, 10,000 features)
  - Character n-grams work across all scripts without tokenization
- **Classifier**: Logistic Regression (C=5.0, balanced class weights)
- **Training data**: `data/intents.json` (multilingual patterns)
- **Emergency override**: Keyword matching before ML classification
- **Inference time**: < 10ms on CPU

### 4. Text-to-Speech — Google TTS (gTTS)
- **Library**: `gTTS` (Google Text-to-Speech)
- **Speed**: Slow mode (better for elderly comprehension)
- **Caching**: MD5-based file caching to avoid re-generation
- **Output**: MP3 audio file served via Flask

---

## 📊 Datasets Used

| Dataset | Source | Usage |
|---------|--------|-------|
| Mozilla Common Voice (Indian) | [commonvoice.mozilla.org](https://commonvoice.mozilla.org) | Reference/evaluation |
| AI4Bharat Speech Dataset | [ai4bharat.org](https://ai4bharat.org) | Reference/evaluation |
| Custom Intent Patterns | `data/intents.json` (hand-crafted) | Training intent classifier |

---

## 🔧 Troubleshooting

### "Microphone access denied"
- Allow microphone in browser settings
- Use HTTPS or `localhost` (HTTP mic blocked on remote IPs)

### "Could not transcribe audio"
- Ensure ffmpeg is installed: `ffmpeg -version`
- Speak clearly, reduce background noise
- Try a shorter recording

### "Server offline" toast
- Make sure `python app.py` is running
- Check terminal for errors
- Try `http://localhost:5000/api/health` in browser

### Whisper taking too long
- Switch to `tiny` model in `config.py`:
  ```python
  WHISPER_MODEL = "tiny"
  ```

### TTS not working / no audio
- Check internet connection (gTTS requires internet)
- Try a different browser
- Check `static/audio/` for generated .mp3 files

### Import errors
- Re-run `pip install -r requirements.txt` with venv active
- Check Python version: `python --version` (needs 3.9+)

---

## 📚 References

1. Radford, A., et al. "Robust Speech Recognition via Large-Scale Weak Supervision." OpenAI Technical Report, 2022.
2. Wolf, T., et al. "Transformers: State-of-the-Art Natural Language Processing." EMNLP 2020, pp. 38–45.
3. Devlin, J., et al. "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding." NAACL-HLT, 2019.
4. Kakwani, A., et al. "IndicNLPSuite: Monolingual Corpora, Evaluation Benchmarks and Pre-trained Multilingual Language Models for Indian Languages." Findings of EMNLP, 2020.
5. Mozilla Foundation. "Common Voice: A Massively Multilingual Speech Corpus." 2023. https://commonvoice.mozilla.org

---


*ElderAssist — Bridging the Digital Divide for Senior Citizens*
