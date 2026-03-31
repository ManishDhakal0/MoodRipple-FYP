import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


DATASET_PATH = Path("tweet_emotions.csv")
MODEL_PATH = Path("text_emotion_model.joblib")
REPORT_PATH = Path("text_emotion_report.json")

TARGET_LABELS = ("happy", "sad", "neutral")
LABEL_MAP = {
    "happiness": "happy",
    "love": "happy",
    "fun": "happy",
    "enthusiasm": "happy",
    "relief": "happy",
    "sadness": "sad",
    "worry": "sad",
    "hate": "sad",
    "anger": "sad",
    "empty": "sad",
    "neutral": "neutral",
    "boredom": "neutral",
    "surprise": "neutral",
}


def load_dataset(path: Path):
    df = pd.read_csv(path)
    df = df[["content", "sentiment"]].dropna()
    df["content"] = df["content"].astype(str).str.strip()
    df["mapped_label"] = df["sentiment"].map(LABEL_MAP)
    df = df[df["mapped_label"].isin(TARGET_LABELS)]
    df = df[df["content"] != ""]
    return df


def build_pipeline():
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    stop_words="english",
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.95,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    multi_class="auto",
                ),
            ),
        ]
    )


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    df = load_dataset(DATASET_PATH)
    if df.empty:
        raise ValueError("No usable rows found after label mapping.")

    x_train, x_test, y_train, y_test = train_test_split(
        df["content"],
        df["mapped_label"],
        test_size=0.2,
        random_state=42,
        stratify=df["mapped_label"],
    )

    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)

    y_pred = pipeline.predict(x_test)
    report = classification_report(y_test, y_pred, output_dict=True)

    artifact = {
        "model": pipeline,
        "labels": list(TARGET_LABELS),
        "label_map": LABEL_MAP,
        "dataset": str(DATASET_PATH),
    }
    joblib.dump(artifact, MODEL_PATH)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved report to {REPORT_PATH}")
    print("Rows used:", len(df))
    print("Class counts:")
    print(df["mapped_label"].value_counts().to_string())


if __name__ == "__main__":
    main()
