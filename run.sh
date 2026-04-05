#!/bin/bash
# ─────────────────────────────────────────────────────────
#  ElderAssist — Startup Script
#  Usage: ./run.sh
# ─────────────────────────────────────────────────────────

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No color

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║         🎙️  ElderAssist AI             ║"
echo "  ║   Multilingual Voice Assistant        ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# ── Check Python ──────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✔ Python ${PYTHON_VERSION}${NC}"

# ── Check ffmpeg ──────────────────────────────────────────
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠ ffmpeg not found. Whisper needs ffmpeg to process audio.${NC}"
    echo "  Install: sudo apt install ffmpeg  (Ubuntu/Debian)"
    echo "           brew install ffmpeg       (macOS)"
    echo "           winget install ffmpeg     (Windows)"
    echo ""
fi

# ── Create virtual environment ────────────────────────────
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# ── Activate venv ─────────────────────────────────────────
source venv/bin/activate

# ── Install dependencies ──────────────────────────────────
echo -e "${YELLOW}Installing dependencies (first run may take a few minutes)...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo -e "${GREEN}✔ All dependencies installed${NC}"

# ── Create directories ────────────────────────────────────
mkdir -p static/audio data

# ── Set environment ───────────────────────────────────────
export FLASK_ENV=development
export WHISPER_MODEL="${WHISPER_MODEL:-base}"   # Change to 'tiny' for faster startup
export PORT="${PORT:-5000}"
export HOST="${HOST:-0.0.0.0}"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  🚀 Starting ElderAssist..."
echo -e "  🌐 URL: ${GREEN}http://localhost:${PORT}${NC}"
echo -e "  📦 Whisper model: ${YELLOW}${WHISPER_MODEL}${NC}"
echo -e "  💡 Press Ctrl+C to stop"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Launch Flask ──────────────────────────────────────────
python3 app.py
