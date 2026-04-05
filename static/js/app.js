/**
 * ElderAssist Frontend — app.js
 * Handles: voice recording, API communication, UI updates
 */

// ── CONFIG ──────────────────────────────────────────────
const API_BASE = window.location.origin;
const API = {
  process:    `${API_BASE}/api/process`,
  chat:       `${API_BASE}/api/chat`,
  transcribe: `${API_BASE}/api/transcribe`,
  health:     `${API_BASE}/api/health`,
};

// ── STATE ────────────────────────────────────────────────
let selectedLanguage = "auto";
let mediaRecorder    = null;
let audioChunks      = [];
let isRecording      = false;
let recordingTimer   = null;
let recordingSeconds = 0;
let conversationHistory = [];

// ── DOM REFS ─────────────────────────────────────────────
const micBtn       = document.getElementById("micBtn");
const micIcon      = document.getElementById("micIcon");
const micHint      = document.getElementById("micHint");
const recordTimer  = document.getElementById("recordTimer");
const timerValue   = document.getElementById("timerValue");
const textInput    = document.getElementById("textInput");
const sendBtn      = document.getElementById("sendBtn");
const statusText   = document.getElementById("statusText");
const statusDot    = document.querySelector(".status-dot");
const loadingOverlay = document.getElementById("loadingOverlay");
const loadingText    = document.getElementById("loadingText");
const responseCard   = document.getElementById("responseCard");
const transcriptBox  = document.getElementById("transcriptBox");
const transcriptText = document.getElementById("transcriptText");
const langChip       = document.getElementById("langChip");
const intentChip     = document.getElementById("intentChip");
const confChip       = document.getElementById("confChip");
const responseBubble = document.getElementById("responseBubble");
const responseText   = document.getElementById("responseText");
const audioControls  = document.getElementById("audioControls");
const playBtn        = document.getElementById("playBtn");
const playIcon       = document.getElementById("playIcon");
const playLabel      = document.getElementById("playLabel");
const responseAudio  = document.getElementById("responseAudio");
const historyCard    = document.getElementById("historyCard");
const historyList    = document.getElementById("historyList");
const clearBtn       = document.getElementById("clearBtn");

// ── LANGUAGE SELECTION ───────────────────────────────────
document.getElementById("langGrid").addEventListener("click", (e) => {
  const btn = e.target.closest(".lang-btn");
  if (!btn) return;

  document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  selectedLanguage = btn.dataset.lang;
  showToast(`Language: ${btn.querySelector(".lang-name").textContent}`, "success");
});

// ── QUICK ACTION BUTTONS ─────────────────────────────────
document.querySelectorAll(".quick-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const query = btn.dataset.query;
    textInput.value = query;
    submitText(query);
  });
});

// ── SEND BUTTON ──────────────────────────────────────────
sendBtn.addEventListener("click", () => {
  const text = textInput.value.trim();
  if (!text) { showToast("Please type a message first", "error"); return; }
  submitText(text);
});

textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    const text = textInput.value.trim();
    if (text) submitText(text);
  }
});

// ── MIC BUTTON ───────────────────────────────────────────
micBtn.addEventListener("click", () => {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
});

async function startRecording() {
  try {
    // Request microphone permission
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream, {
      mimeType: getSupportedMimeType()
    });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      processRecording();
    };

    mediaRecorder.start(100); // Collect data every 100ms
    isRecording = true;

    // UI feedback
    micBtn.classList.add("recording");
    micIcon.textContent = "⏹️";
    micHint.textContent = "Recording… Tap to stop";
    recordTimer.style.display = "block";
    recordingSeconds = 0;
    setStatus("recording", "Recording…");

    recordingTimer = setInterval(() => {
      recordingSeconds++;
      const m = Math.floor(recordingSeconds / 60);
      const s = recordingSeconds % 60;
      timerValue.textContent = `${m}:${s.toString().padStart(2, "0")}`;

      // Auto-stop after 30 seconds
      if (recordingSeconds >= 30) {
        showToast("Max recording length reached", "");
        stopRecording();
      }
    }, 1000);

  } catch (err) {
    console.error("Mic error:", err);
    showToast("Microphone access denied. Please allow mic permission.", "error");
  }
}

function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === "inactive") return;

  clearInterval(recordingTimer);
  mediaRecorder.stop();
  isRecording = false;

  micBtn.classList.remove("recording");
  micIcon.textContent = "🎙️";
  micHint.textContent = "Processing your speech…";
  recordTimer.style.display = "none";
  setStatus("thinking", "Processing…");
}

async function processRecording() {
  if (audioChunks.length === 0) {
    micHint.textContent = "Press the button and speak";
    setStatus("ready", "Ready");
    return;
  }

  const mimeType = getSupportedMimeType();
  const extension = mimeType.includes("webm") ? "webm" :
                    mimeType.includes("ogg")  ? "ogg"  : "mp4";

  const blob = new Blob(audioChunks, { type: mimeType });

  // Show loading
  showLoading("Transcribing your speech…");

  try {
    const formData = new FormData();
    formData.append("audio", blob, `recording.${extension}`);
    if (selectedLanguage !== "auto") {
      formData.append("language", selectedLanguage);
    }
    formData.append("tts", "true");

    const response = await fetch(API.process, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    hideLoading();

    if (data.success) {
      displayResponse(data, true);
    } else {
      showToast(data.error || "Could not understand audio. Please try again.", "error");
      setStatus("ready", "Ready");
    }

  } catch (err) {
    hideLoading();
    console.error("Process error:", err);
    showToast("Connection error. Is the server running?", "error");
    setStatus("ready", "Ready");
  }

  micHint.textContent = "Press the button and speak";
}

// ── SUBMIT TEXT ───────────────────────────────────────────
async function submitText(text) {
  showLoading("Understanding your message…");
  setStatus("thinking", "Thinking…");

  try {
    const payload = {
      text,
      tts: true,
    };
    if (selectedLanguage !== "auto") {
      payload.language = selectedLanguage;
    }

    const response = await fetch(API.chat, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    hideLoading();

    if (data.success) {
      displayResponse(data, false);
    } else {
      showToast(data.error || "Something went wrong. Please try again.", "error");
      setStatus("ready", "Ready");
    }

  } catch (err) {
    hideLoading();
    console.error("Chat error:", err);
    showToast("Connection error. Is the server running?", "error");
    setStatus("ready", "Ready");
  }
}

// ── DISPLAY RESPONSE ─────────────────────────────────────
function displayResponse(data, isVoice) {
  // Show transcript (if voice)
  if (isVoice && data.transcription) {
    transcriptBox.style.display = "block";
    transcriptText.textContent = data.transcription;
  } else {
    transcriptBox.style.display = "none";
  }

  // Meta chips
  const langNames = {
    en: "🇬🇧 English", hi: "🇮🇳 Hindi", mr: "🏔️ Marathi",
    gu: "🦁 Gujarati", ta: "🌺 Tamil", te: "🌿 Telugu", bn: "🎨 Bengali"
  };

  const intentNames = {
    greeting:           "👋 Greeting",
    farewell:           "👋 Farewell",
    appointment:        "🏥 Appointment",
    medicine_reminder:  "💊 Medicine",
    emergency:          "🚨 Emergency",
    banking:            "🏦 Banking",
    weather:            "🌤️ Weather",
    government_services:"🏛️ Govt. Services",
    news:               "📰 News",
    help:               "❓ Help"
  };

  langChip.textContent   = langNames[data.language] || `🌐 ${data.language}`;
  intentChip.textContent = intentNames[data.intent]  || `💡 ${data.intent}`;
  confChip.textContent   = `📊 ${Math.round(data.confidence * 100)}%`;

  // Response text
  responseText.textContent = data.response;

  // Emergency styling
  if (data.intent === "emergency") {
    responseBubble.classList.add("emergency");
  } else {
    responseBubble.classList.remove("emergency");
  }

  // Audio controls
  if (data.audio_url) {
    responseAudio.src = API_BASE + data.audio_url;
    audioControls.style.display = "flex";

    // Auto-play for voice input
    if (isVoice) {
      setTimeout(() => playAudio(), 400);
    }
  } else {
    audioControls.style.display = "none";
  }

  // Show response card
  responseCard.style.display = "block";
  responseCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

  // Add to history
  addToHistory({
    userText:  data.transcription || data.text || textInput.value,
    response:  data.response,
    intent:    data.intent,
    language:  data.language,
    langName:  langNames[data.language] || data.language,
    intentName: intentNames[data.intent] || data.intent,
  });

  // Clear text input
  textInput.value = "";
  setStatus("ready", "Ready");
}

// ── AUDIO PLAYBACK ────────────────────────────────────────
function playAudio() {
  if (!responseAudio.src) return;

  if (responseAudio.paused) {
    responseAudio.play()
      .then(() => {
        playIcon.textContent  = "⏸️";
        playLabel.textContent = "Pause";
      })
      .catch(err => console.warn("Audio play failed:", err));
  } else {
    responseAudio.pause();
    playIcon.textContent  = "▶️";
    playLabel.textContent = "Play Response";
  }
}

playBtn.addEventListener("click", playAudio);

responseAudio.addEventListener("ended", () => {
  playIcon.textContent  = "▶️";
  playLabel.textContent = "Play Response";
});

// ── HISTORY ───────────────────────────────────────────────
function addToHistory(item) {
  conversationHistory.unshift(item);
  if (conversationHistory.length > 20) conversationHistory.pop();

  renderHistory();
  historyCard.style.display = "block";
}

function renderHistory() {
  historyList.innerHTML = conversationHistory.map((item, i) => `
    <div class="history-item">
      <div class="history-item-user">You: ${escapeHTML(item.userText)}</div>
      <div class="history-item-response">${escapeHTML(item.response)}</div>
      <div class="history-item-meta">
        <span class="history-tag">${item.langName}</span>
        <span class="history-tag">${item.intentName}</span>
      </div>
    </div>
  `).join("");
}

clearBtn.addEventListener("click", () => {
  conversationHistory = [];
  historyList.innerHTML = "";
  historyCard.style.display = "none";
  showToast("History cleared", "");
});

// ── UI HELPERS ────────────────────────────────────────────
function setStatus(type, text) {
  statusText.textContent = text;
  statusDot.className = "status-dot";
  if (type !== "ready") statusDot.classList.add(type);
}

function showLoading(msg = "Processing…") {
  loadingText.textContent = msg;
  loadingOverlay.style.display = "flex";
}

function hideLoading() {
  loadingOverlay.style.display = "none";
}

let toastTimer = null;
function showToast(msg, type = "") {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
  }

  clearTimeout(toastTimer);
  toast.textContent = msg;
  toast.className = `toast ${type}`;

  // Force reflow
  void toast.offsetWidth;
  toast.classList.add("show");

  toastTimer = setTimeout(() => {
    toast.classList.remove("show");
  }, 3000);
}

function escapeHTML(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

function getSupportedMimeType() {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
    "audio/mp4",
  ];
  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return "";
}

// ── HEALTH CHECK ──────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(API.health);
    if (res.ok) {
      const data = await res.json();
      setStatus("ready", "Ready");
      console.log("ElderAssist backend:", data);
    } else {
      setStatus("error", "Server offline");
      showToast("Backend not reachable. Please start the server.", "error");
    }
  } catch {
    setStatus("error", "Server offline");
    showToast("Backend not reachable. Run: python app.py", "error");
  }
}

// ── KEYBOARD SHORTCUT ─────────────────────────────────────
document.addEventListener("keydown", (e) => {
  // Space bar = toggle recording (when not in textarea)
  if (e.code === "Space" && document.activeElement !== textInput) {
    e.preventDefault();
    if (isRecording) stopRecording();
    else startRecording();
  }
  // Escape = stop recording
  if (e.code === "Escape" && isRecording) {
    stopRecording();
  }
});

// ── INIT ──────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  checkHealth();

  // Check mic availability
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    micBtn.disabled = true;
    micHint.textContent = "Voice not supported in this browser. Please use Chrome.";
  }

  // Large text toggle (accessibility)
  const savedLargeText = localStorage.getItem("elderassist-largetext");
  if (savedLargeText === "true") document.body.classList.add("large-text");
});
