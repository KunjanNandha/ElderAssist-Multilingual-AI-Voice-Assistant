"""
intent_classifier.py
Classifies user intent using a TF-IDF + Logistic Regression pipeline.
Trained on multilingual intent patterns from intents.json.
Supports: greeting, farewell, appointment, medicine_reminder,
          emergency, banking, weather, government_services, news, help
"""

import json
import os
import re
import logging
import pickle
from typing import Tuple, List

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

# Emergency keywords that always trigger emergency intent regardless of classifier
EMERGENCY_KEYWORDS = {
    # English
    "emergency", "help me", "ambulance", "chest pain", "dying", "unconscious",
    "accident", "breathless", "heart attack", "stroke", "bleeding",
    # Hindi
    "आपातकाल", "मदद करो", "एम्बुलेंस", "सीने में दर्द", "बेहोश",
    # Marathi
    "आणीबाणी", "मदत करा", "रुग्णवाहिका",
    # Gujarati
    "ઇમર્જન્સી", "ઍમ્બ્યુલન્સ",
    # Tamil
    "அவசரம்", "ஆம்புலன்ஸ்",
    # Telugu
    "అత్యవసరం", "యాంబులెన్స్",
    # Bengali
    "জরুরি", "অ্যাম্বুলেন্স"
}


class IntentClassifier:
    """
    Multilingual intent classifier trained on labeled patterns.
    """

    def __init__(self, intents_file: str):
        self.intents_file = intents_file
        self.intents_data = None
        self.pipeline = None
        self.label_encoder = LabelEncoder()
        self.responses = {}   # tag -> {lang -> response}
        self._load_and_train()

    def _load_and_train(self):
        """Load intent data and train the classifier."""
        try:
            with open(self.intents_file, "r", encoding="utf-8") as f:
                self.intents_data = json.load(f)

            # Build training corpus
            X, y = [], []
            for intent in self.intents_data["intents"]:
                tag = intent["tag"]
                self.responses[tag] = intent.get("responses", {})
                for pattern in intent["patterns"]:
                    X.append(self._preprocess(pattern))
                    y.append(tag)

            # Encode labels
            y_encoded = self.label_encoder.fit_transform(y)

            # Build sklearn pipeline
            self.pipeline = Pipeline([
                ("tfidf", TfidfVectorizer(
                    analyzer="char_wb",       # Character n-grams — works across scripts
                    ngram_range=(2, 4),       # 2-4 character n-grams
                    max_features=10000,
                    sublinear_tf=True
                )),
                ("clf", LogisticRegression(
                    C=5.0,
                    max_iter=500,
                    class_weight="balanced",
                    random_state=42
                ))
            ])

            self.pipeline.fit(X, y_encoded)
            logger.info(f"Intent classifier trained on {len(X)} patterns, {len(set(y))} intents")

        except Exception as e:
            logger.error(f"Failed to train intent classifier: {e}")
            raise

    def _preprocess(self, text: str) -> str:
        """Normalize text for classification."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s\u0900-\u097F\u0A80-\u0AFF\u0B80-\u0BFF"
                      r"\u0C00-\u0C7F\u0980-\u09FF\u0A00-\u0A7F]", " ", text)
        return text

    def _check_emergency(self, text: str) -> bool:
        """Fast check for emergency keywords."""
        text_lower = text.lower()
        for keyword in EMERGENCY_KEYWORDS:
            if keyword in text_lower:
                return True
        return False

    def classify(self, text: str) -> Tuple[str, float]:
        """
        Classify intent of input text.

        Args:
            text: Input text (any supported language)

        Returns:
            Tuple of (intent_tag, confidence_score)
        """
        if not text or not text.strip():
            return "help", 0.5

        # Emergency override — always prioritize safety
        if self._check_emergency(text):
            return "emergency", 1.0

        try:
            processed = self._preprocess(text)
            probs = self.pipeline.predict_proba([processed])[0]
            pred_idx = np.argmax(probs)
            confidence = float(probs[pred_idx])
            intent_tag = self.label_encoder.inverse_transform([pred_idx])[0]
            return intent_tag, confidence

        except Exception as e:
            logger.error(f"Classification error: {e}")
            return "help", 0.5

    def get_response(self, intent_tag: str, language: str = "en") -> str:
        """
        Get the response for a given intent in the specified language.

        Args:
            intent_tag: Intent tag (e.g., 'greeting', 'emergency')
            language:   Target language code (e.g., 'hi', 'mr', 'en')

        Returns:
            Response string in the requested language
        """
        responses = self.responses.get(intent_tag, {})

        # Try requested language first, then English as fallback
        if language in responses:
            return responses[language]
        if "en" in responses:
            return responses["en"]

        return "I'm here to help. Please tell me more about what you need."

    def get_all_intents(self) -> List[str]:
        """Return all known intent tags."""
        return list(self.responses.keys())

    def get_top_intents(self, text: str, n: int = 3) -> List[Tuple[str, float]]:
        """
        Return top N intent predictions with confidence scores.

        Args:
            text: Input text
            n:    Number of top intents to return

        Returns:
            List of (intent_tag, confidence) tuples, sorted by confidence
        """
        if not text or not text.strip():
            return [("help", 0.5)]

        try:
            processed = self._preprocess(text)
            probs = self.pipeline.predict_proba([processed])[0]
            top_indices = np.argsort(probs)[::-1][:n]
            results = []
            for idx in top_indices:
                tag = self.label_encoder.inverse_transform([idx])[0]
                results.append((tag, float(probs[idx])))
            return results
        except Exception as e:
            logger.error(f"Top intent error: {e}")
            return [("help", 0.5)]
