from transformers import pipeline

emotion_classifier = pipeline(
    "audio-classification",
    model="superb/wav2vec2-base-superb-er"
)

EMOTION_LABELS = {
    "ang": "Angry",
    "hap": "Happy",
    "sad": "Sad",
    "neu": "Neutral"
}


def detect_emotion(file_path):
    results = emotion_classifier(file_path)

    best_result = max(results, key=lambda x: x["score"])

    raw_emotion = str(best_result["label"]).strip().lower()
    emotion = EMOTION_LABELS.get(raw_emotion, raw_emotion)

    return {
        "emotion": emotion,
        "raw_emotion": raw_emotion,
        "confidence": round(best_result["score"], 4)
    }