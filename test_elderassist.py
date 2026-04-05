"""
test_elderassist.py
Unit + integration tests for ElderAssist.

Run: python test_elderassist.py
Or:  python -m pytest test_elderassist.py -v
"""

import sys
import os
import json
import time
import unittest
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─────────────────────────────────────────────────────────
# Colours for terminal output
# ─────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def print_header(title):
    print(f"\n{CYAN}{BOLD}{'─'*55}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{'─'*55}{RESET}")


def print_result(name, passed, detail=""):
    icon = f"{GREEN}✔{RESET}" if passed else f"{RED}✘{RESET}"
    print(f"  {icon}  {name}" + (f"  {YELLOW}({detail}){RESET}" if detail else ""))


# ═════════════════════════════════════════════════════════
# 1. Language Detector Tests
# ═════════════════════════════════════════════════════════

class TestLanguageDetector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from models.language_detector import LanguageDetector
        cls.detector = LanguageDetector()

    def test_english_detection(self):
        lang = self.detector.detect("Hello, I need a doctor appointment")
        self.assertEqual(lang, "en")

    def test_hindi_devanagari(self):
        lang = self.detector.detect("मुझे डॉक्टर से मिलना है")
        self.assertIn(lang, ["hi", "mr"])  # Both Devanagari

    def test_marathi_keywords(self):
        lang = self.detector.detect("मला डॉक्टरांना भेटायचे आहे")
        self.assertEqual(lang, "mr")

    def test_gujarati_script(self):
        lang = self.detector.detect("ડૉક્ટર ઍપોઇન્ટમેન્ટ જોઈએ")
        self.assertEqual(lang, "gu")

    def test_tamil_script(self):
        lang = self.detector.detect("மருத்துவர் சந்திப்பு வேண்டும்")
        self.assertEqual(lang, "ta")

    def test_telugu_script(self):
        lang = self.detector.detect("డాక్టర్ అపాయింట్‌మెంట్ కావాలి")
        self.assertEqual(lang, "te")

    def test_bengali_script(self):
        lang = self.detector.detect("ডাক্তারের অ্যাপয়েন্টমেন্ট দরকার")
        self.assertEqual(lang, "bn")

    def test_empty_text_returns_default(self):
        lang = self.detector.detect("")
        self.assertEqual(lang, "en")

    def test_whisper_lang_overrides(self):
        # If Whisper detected 'ta', respect it
        lang = self.detector.detect("hello", whisper_lang="ta")
        self.assertEqual(lang, "ta")

    def test_get_language_name(self):
        self.assertEqual(self.detector.get_language_name("hi"), "Hindi")
        self.assertEqual(self.detector.get_language_name("ta"), "Tamil")
        self.assertIn("Unknown", self.detector.get_language_name("xx"))


# ═════════════════════════════════════════════════════════
# 2. Intent Classifier Tests
# ═════════════════════════════════════════════════════════

class TestIntentClassifier(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from models.intent_classifier import IntentClassifier
        cls.clf = IntentClassifier("data/intents.json")

    def _assert_intent(self, text, expected_intent, min_conf=0.3):
        intent, conf = self.clf.classify(text)
        self.assertEqual(intent, expected_intent,
            f"Text: '{text}' → got '{intent}' (conf={conf:.2f}), expected '{expected_intent}'")
        self.assertGreaterEqual(conf, min_conf,
            f"Confidence {conf:.2f} below threshold {min_conf}")

    # ── English ──
    def test_greeting_en(self):
        self._assert_intent("hello there", "greeting")

    def test_farewell_en(self):
        self._assert_intent("goodbye", "farewell")

    def test_appointment_en(self):
        self._assert_intent("I need a doctor appointment", "appointment")

    def test_medicine_en(self):
        self._assert_intent("medicine reminder tablet", "medicine_reminder")

    def test_emergency_en(self):
        intent, conf = self.clf.classify("Emergency help needed ambulance")
        self.assertEqual(intent, "emergency")
        self.assertEqual(conf, 1.0, "Emergency should always have confidence 1.0")

    def test_banking_en(self):
        self._assert_intent("bank balance account", "banking")

    def test_weather_en(self):
        self._assert_intent("weather today temperature", "weather")

    def test_government_en(self):
        self._assert_intent("aadhaar card government", "government_services")

    def test_news_en(self):
        self._assert_intent("latest news today", "news")

    def test_help_en(self):
        self._assert_intent("what can you do for me", "help")

    # ── Hindi ──
    def test_greeting_hi(self):
        self._assert_intent("नमस्ते", "greeting")

    def test_appointment_hi(self):
        self._assert_intent("डॉक्टर", "appointment")

    def test_emergency_hi(self):
        intent, conf = self.clf.classify("आपातकाल मदद करो")
        self.assertEqual(intent, "emergency")

    def test_medicine_hi(self):
        self._assert_intent("दवाई गोली", "medicine_reminder")

    # ── Gujarati ──
    def test_emergency_gu(self):
        intent, conf = self.clf.classify("ઇમર્જન્સી ઍમ્બ્યુલન્સ")
        self.assertEqual(intent, "emergency")

    # ── Tamil ──
    def test_appointment_ta(self):
        self._assert_intent("டாக்டர் மருத்துவமனை", "appointment")

    # ── Response generation ──
    def test_response_in_hindi(self):
        resp = self.clf.get_response("greeting", "hi")
        self.assertIsInstance(resp, str)
        self.assertTrue(len(resp) > 10)

    def test_response_in_english(self):
        resp = self.clf.get_response("emergency", "en")
        self.assertIn("112", resp)  # Emergency number must be in response

    def test_response_fallback_to_english(self):
        resp = self.clf.get_response("greeting", "zz")  # Unknown lang
        self.assertIsInstance(resp, str)

    def test_top_intents(self):
        results = self.clf.get_top_intents("help me doctor", n=3)
        self.assertEqual(len(results), 3)
        for tag, conf in results:
            self.assertIsInstance(tag, str)
            self.assertIsInstance(conf, float)

    def test_empty_text(self):
        intent, conf = self.clf.classify("")
        self.assertEqual(intent, "help")

    def test_all_intents_loaded(self):
        intents = self.clf.get_all_intents()
        expected = {
            "greeting", "farewell", "appointment", "medicine_reminder",
            "emergency", "banking", "weather", "government_services", "news", "help"
        }
        self.assertTrue(expected.issubset(set(intents)),
            f"Missing intents: {expected - set(intents)}")


# ═════════════════════════════════════════════════════════
# 3. TTS Engine Tests
# ═════════════════════════════════════════════════════════

class TestTTSEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from models.tts_engine import TTSEngine
        cls.audio_dir = tempfile.mkdtemp()
        cls.tts = TTSEngine(cls.audio_dir)

    def test_english_tts(self):
        path = self.tts.synthesize("Hello, how are you?", "en")
        if path:  # Skip if gTTS has no internet
            self.assertTrue(os.path.exists(path))
            self.assertTrue(path.endswith(".mp3"))

    def test_hindi_tts(self):
        path = self.tts.synthesize("नमस्ते", "hi")
        if path:
            self.assertTrue(os.path.exists(path))

    def test_caching_same_content(self):
        p1 = self.tts.synthesize("Test message", "en")
        p2 = self.tts.synthesize("Test message", "en")
        if p1 and p2:
            self.assertEqual(p1, p2, "Same content should return cached file")

    def test_emoji_removal(self):
        clean = self.tts._remove_emoji("Hello 🚨🏥 World")
        self.assertEqual(clean, "Hello  World")

    def test_empty_text_returns_none(self):
        result = self.tts.synthesize("", "en")
        self.assertIsNone(result)


# ═════════════════════════════════════════════════════════
# 4. Reminder Scheduler Tests
# ═════════════════════════════════════════════════════════

class TestReminderScheduler(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from models.reminder_scheduler import ReminderScheduler
        cls.storage = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        cls.sched = ReminderScheduler(tts_engine=None, storage_path=cls.storage)

    def test_add_reminder(self):
        r = self.sched.add_reminder("Metformin", times=["08:00", "20:00"], language="en")
        self.assertIn(r.id, self.sched.reminders)

    def test_add_reminder_with_frequency(self):
        r = self.sched.add_reminder("Aspirin", times=[], frequency=3, language="hi")
        self.assertEqual(len(r.times), 3)

    def test_reminder_message_english(self):
        r = self.sched.add_reminder("Vitamin D", times=["09:00"], language="en")
        msg = r.get_message()
        self.assertIn("Vitamin D", msg)
        self.assertIn("Medicine", msg)

    def test_reminder_message_hindi(self):
        r = self.sched.add_reminder("Paracetamol", times=["10:00"], language="hi")
        msg = r.get_message()
        self.assertIn("Paracetamol", msg)

    def test_toggle_reminder(self):
        r = self.sched.add_reminder("Test Med", times=["12:00"])
        original_state = r.active
        new_state = self.sched.toggle_reminder(r.id)
        self.assertEqual(new_state, not original_state)

    def test_remove_reminder(self):
        r = self.sched.add_reminder("Temp Med", times=["15:00"])
        result = self.sched.remove_reminder(r.id)
        self.assertTrue(result)
        self.assertNotIn(r.id, self.sched.reminders)

    def test_persistence_save_and_load(self):
        from models.reminder_scheduler import ReminderScheduler
        self.sched.add_reminder("Persisted Med", times=["08:00"], language="ta")
        # Load fresh instance from same file
        sched2 = ReminderScheduler(tts_engine=None, storage_path=self.storage)
        names = [r.medicine_name for r in sched2.reminders.values()]
        self.assertIn("Persisted Med", names)

    def test_generate_times_frequency_1(self):
        from models.reminder_scheduler import ReminderScheduler
        times = ReminderScheduler._generate_times(1)
        self.assertEqual(len(times), 1)

    def test_generate_times_frequency_3(self):
        from models.reminder_scheduler import ReminderScheduler
        times = ReminderScheduler._generate_times(3)
        self.assertEqual(len(times), 3)


# ═════════════════════════════════════════════════════════
# 5. Flask API Integration Tests
# ═════════════════════════════════════════════════════════

class TestFlaskAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Import app but DON'T start the server — use test client
        import app as flask_app
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["WTF_CSRF_ENABLED"] = False
        cls.client = flask_app.app.test_client()

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "ok")
        self.assertIn("whisper_model", data)

    def test_languages_endpoint(self):
        resp = self.client.get("/api/languages")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("languages", data)
        self.assertIn("en", data["languages"])
        self.assertIn("hi", data["languages"])

    def test_chat_english(self):
        resp = self.client.post(
            "/api/chat",
            data=json.dumps({"text": "hello", "language": "en", "tts": False}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["intent"], "greeting")
        self.assertIn("response", data)

    def test_chat_hindi(self):
        resp = self.client.post(
            "/api/chat",
            data=json.dumps({"text": "नमस्ते", "tts": False}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["intent"], "greeting")

    def test_chat_emergency(self):
        resp = self.client.post(
            "/api/chat",
            data=json.dumps({"text": "emergency help ambulance", "tts": False}),
            content_type="application/json"
        )
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["intent"], "emergency")
        self.assertEqual(data["confidence"], 1.0)

    def test_chat_appointment(self):
        resp = self.client.post(
            "/api/chat",
            data=json.dumps({"text": "I need a doctor appointment", "tts": False}),
            content_type="application/json"
        )
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["intent"], "appointment")

    def test_chat_missing_text(self):
        resp = self.client.post(
            "/api/chat",
            data=json.dumps({}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertFalse(data["success"])

    def test_index_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"ElderAssist", resp.data)

    def test_404_returns_json(self):
        resp = self.client.get("/api/nonexistent")
        self.assertEqual(resp.status_code, 404)


# ═════════════════════════════════════════════════════════
# 6. Data/Config Tests
# ═════════════════════════════════════════════════════════

class TestDataAndConfig(unittest.TestCase):

    def test_intents_json_structure(self):
        with open("data/intents.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("intents", data)
        for intent in data["intents"]:
            self.assertIn("tag", intent)
            self.assertIn("patterns", intent)
            self.assertIn("responses", intent)
            self.assertGreater(len(intent["patterns"]), 0)
            self.assertIn("en", intent["responses"])

    def test_config_whisper_model(self):
        import config
        self.assertIn(config.WHISPER_MODEL, ["tiny", "base", "small", "medium", "large"])

    def test_config_supported_languages(self):
        import config
        self.assertIn("en", config.SUPPORTED_LANGUAGES)
        self.assertIn("hi", config.SUPPORTED_LANGUAGES)
        self.assertGreaterEqual(len(config.SUPPORTED_LANGUAGES), 5)

    def test_config_emergency_contacts(self):
        import config
        self.assertIn("ambulance", config.EMERGENCY_CONTACTS)
        self.assertEqual(config.EMERGENCY_CONTACTS["ambulance"], "108")
        self.assertEqual(config.EMERGENCY_CONTACTS["emergency"], "112")


# ═════════════════════════════════════════════════════════
# MAIN — pretty terminal output
# ═════════════════════════════════════════════════════════

def run_tests():
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║          ElderAssist — Test Suite                    ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════╝{RESET}")

    suites = [
        ("Language Detector",    TestLanguageDetector),
        ("Intent Classifier",    TestIntentClassifier),
        ("TTS Engine",           TestTTSEngine),
        ("Reminder Scheduler",   TestReminderScheduler),
        ("Flask API",            TestFlaskAPI),
        ("Data & Config",        TestDataAndConfig),
    ]

    total_passed = total_failed = 0

    for suite_name, test_class in suites:
        print_header(suite_name)
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
        result = runner.run(suite)

        passed = result.testsRun - len(result.failures) - len(result.errors)
        failed = len(result.failures) + len(result.errors)
        total_passed += passed
        total_failed += failed

        for test, _ in result.failures + result.errors:
            print_result(str(test).split(" ")[0], False, "FAILED")
        for test in suite:
            method = test._testMethodName
            was_failure = any(method in str(f[0]) for f in result.failures + result.errors)
            if not was_failure:
                print_result(method, True)

    # Summary
    total = total_passed + total_failed
    print(f"\n{CYAN}{'━'*55}{RESET}")
    print(f"  {'SUMMARY':<20}", end="")
    colour = GREEN if total_failed == 0 else RED
    print(f"{colour}{BOLD}{total_passed}/{total} tests passed{RESET}")
    if total_failed > 0:
        print(f"  {RED}✘ {total_failed} test(s) failed{RESET}")
    else:
        print(f"  {GREEN}🎉 All tests passed!{RESET}")
    print(f"{CYAN}{'━'*55}{RESET}\n")

    return total_failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
