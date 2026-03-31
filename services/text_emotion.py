# services/text_emotion.py
# Text emotion detector — TF-IDF + LogisticRegression (joblib model).
# Train the model first:  python scripts/text_emotion_train.py

from pathlib import Path
import joblib

MODEL_PATH = Path("text_emotion_model.joblib")


class TextEmotionDetector:
    def __init__(self, model_path: Path = MODEL_PATH):
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {model_path}. "
                "Run  python scripts/text_emotion_train.py  first."
            )
        artifact   = joblib.load(model_path)
        self.model  = artifact["model"]
        self.labels = artifact.get("labels", ["happy", "sad", "neutral"])

    def predict(self, text: str) -> dict:
        cleaned = (text or "").strip()
        if not cleaned:
            return {"emotion": "neutral", "confidence": 0.0, "scores": {}}

        probs       = self.model.predict_proba([cleaned])[0]
        label_scores = {
            label: float(score)
            for label, score in zip(self.model.classes_, probs)
        }
        best = max(label_scores, key=label_scores.get)
        return {
            "emotion":    best,
            "confidence": label_scores[best],
            "scores":     label_scores,
        }
