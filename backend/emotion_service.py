import os
import subprocess
import tempfile

import librosa
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


def convert_to_wav(input_file):
    wav_file = tempfile.NamedTemporaryFile(
        prefix="auralis_emotion_",
        suffix=".wav",
        delete=False
    ).name

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            wav_file
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )

    return wav_file


def detect_emotion(file_path):
    wav_file = None

    try:
        # Browser WebM -> WAV
        wav_file = convert_to_wav(file_path)

        # Load normalized WAV
        audio, sample_rate = librosa.load(
            wav_file,
            sr=16000,
            mono=True
        )

        # Normalize volume
        max_value = max(abs(audio))

        if max_value > 0:
            audio = audio / max_value

        results = emotion_classifier({
            "array": audio,
            "sampling_rate": sample_rate
        })

        print("DEBUG EMOTION RESULTS:", results)

        best_result = max(results, key=lambda x: x["score"])

        raw_emotion = str(
            best_result["label"]
        ).strip().lower()

        emotion = EMOTION_LABELS.get(
            raw_emotion,
            raw_emotion
        )

        return {
            "emotion": emotion,
            "raw_emotion": raw_emotion,
            "confidence": round(
                best_result["score"],
                4
            )
        }

    finally:
        if wav_file and os.path.exists(wav_file):
            os.remove(wav_file)