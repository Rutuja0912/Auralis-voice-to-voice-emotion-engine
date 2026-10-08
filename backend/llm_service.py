import requests


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "llava:7b"


def generate_response(transcription, emotion):
    prompt = f"""
You are the conversational AI engine of Auralis.

User speech:
{transcription}

Detected emotion:
{emotion}

Respond naturally and appropriately to the user's emotional state.
Keep the response short and conversational.
Do not mention the emotion label directly.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return data.get("response", "").strip()