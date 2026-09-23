from transformers import pipeline

emotion_classifier = pipeline(
    "audio-classification",
    model="superb/wav2vec2-base-superb-er"
)


def detect_emotion(file_path):
    results = emotion_classifier(file_path)

    best_result = max(results, key=lambda x: x["score"])

    return {
        "emotion": best_result["label"],
        "confidence": round(best_result["score"], 4)
    }