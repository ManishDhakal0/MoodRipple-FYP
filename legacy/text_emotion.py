from pathlib import Path

import joblib


MODEL_PATH = Path("text_emotion_model.joblib")


class TextEmotionDetector:
    def __init__(self, model_path: Path = MODEL_PATH):
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {model_path}. Run text_emotion_train.py first."
            )

        artifact = joblib.load(model_path)
        self.model = artifact["model"]
        self.labels = artifact.get("labels", ["happy", "sad", "neutral"])

    def predict(self, text: str):
        cleaned = (text or "").strip()
        if not cleaned:
            return {"emotion": "neutral", "confidence": 0.0, "scores": {}}

        probabilities = self.model.predict_proba([cleaned])[0]
        label_scores = {
            label: float(score)
            for label, score in zip(self.model.classes_, probabilities)
        }
        best_label = max(label_scores, key=label_scores.get)

        return {
            "emotion": best_label,
            "confidence": label_scores[best_label],
            "scores": label_scores,
        }


def main():
    detector = TextEmotionDetector()

    print("Text Emotion Detector")
    print("Type text and press Enter. Type 'exit' to quit.")

    while True:
        text = input("\nText: ").strip()
        if text.lower() in {"exit", "quit"}:
            break

        result = detector.predict(text)
        print(f"Emotion: {result['emotion']}")
        print(f"Confidence: {result['confidence'] * 100:.1f}%")
        print("Scores:")
        for label, score in sorted(result["scores"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {label}: {score * 100:.1f}%")


if __name__ == "__main__":
    main()
