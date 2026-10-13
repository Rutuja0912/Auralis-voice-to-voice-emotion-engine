
import os
import math
import subprocess
import tempfile

import librosa
import numpy as np
from transformers import pipeline


# --------------------------------------------------
# Emotion Classification Model
# --------------------------------------------------

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


# --------------------------------------------------
# Convert Browser Audio to WAV
# --------------------------------------------------

def convert_to_wav(input_file):
    if not os.path.isfile(input_file):
        raise FileNotFoundError(
            f"Input audio file not found: {input_file}"
        )

    temp_file = tempfile.NamedTemporaryFile(
        prefix="auralis_emotion_",
        suffix=".wav",
        delete=False
    )

    wav_file = temp_file.name
    temp_file.close()

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_file,
                "-vn",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                wav_file
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )

        if not os.path.isfile(wav_file):
            raise RuntimeError(
                "FFmpeg did not create the WAV file."
            )

        if os.path.getsize(wav_file) == 0:
            raise ValueError(
                "Converted WAV file is empty."
            )

        return wav_file

    except Exception:
        if os.path.exists(wav_file):
            os.remove(wav_file)
        raise


# --------------------------------------------------
# Detect Emotion from Audio
# --------------------------------------------------

def detect_emotion(file_path):
    wav_file = None

    try:
        # Step 1: Convert browser audio to WAV
        wav_file = convert_to_wav(file_path)

        # Step 2: Load audio as mono, 16 kHz
        audio, sample_rate = librosa.load(
            wav_file,
            sr=16000,
            mono=True
        )

        # Step 3: Validate audio
        if len(audio) == 0:
            raise ValueError(
                "Audio is empty. Please record again."
            )

        if not np.all(np.isfinite(audio)):
            raise ValueError(
                "Audio contains invalid numeric values."
            )

        audio_peak = float(np.max(np.abs(audio)))
        audio_duration = len(audio) / sample_rate

        print("DEBUG SAMPLE RATE:", sample_rate)
        print("DEBUG AUDIO LENGTH:", len(audio))
        print("DEBUG AUDIO DURATION:", round(audio_duration, 2))
        print("DEBUG AUDIO PEAK:", audio_peak)

        if audio_peak < 1e-6:
            raise ValueError(
                "Audio is silent or too quiet. Please record again."
            )

        # Step 4: Normalize audio safely
        audio = audio.astype(np.float32)

        audio = audio / audio_peak

        # Step 5: Run emotion classification
        results = emotion_classifier(
            {
                "array": audio,
                "sampling_rate": sample_rate
            }
        )

        print("DEBUG EMOTION RESULTS:", results)
        print("DEBUG TOP 4 EMOTIONS:", results[:4])

        if not results:
            raise RuntimeError(
                "Emotion classifier returned no results."
            )

        # Step 6: Select highest-scoring prediction
        best_result = max(
            results,
            key=lambda item: float(item["score"])
        )

        raw_emotion = str(
            best_result["label"]
        ).strip().lower()

        emotion = EMOTION_LABELS.get(
            raw_emotion,
            raw_emotion
        )

        confidence = float(
            best_result["score"]
        )

        # Step 7: Return API result
        return {
            "emotion": emotion,
            "raw_emotion": raw_emotion,
            "confidence": round(confidence, 4),
            "audio_duration": round(audio_duration, 2),
            "sample_rate": sample_rate
        }

    except Exception as error:
        print(
            "ERROR IN EMOTION DETECTION:",
            repr(error)
        )
        raise

    finally:
        # Step 8: Always clean up temporary WAV
        if wav_file and os.path.exists(wav_file):
            try:
                os.remove(wav_file)
            except OSError as cleanup_error:
                print(
                    "WARNING: Could not remove temporary WAV:",
                    repr(cleanup_error)
                )
