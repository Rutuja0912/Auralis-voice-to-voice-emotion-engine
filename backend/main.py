import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import requests
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from backend.emotion_service import detect_emotion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auralis")

app = FastAPI(title="Auralis – Real-Time Voice-to-Voice Emotion Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434/api/chat",
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

MAX_AUDIO_BYTES = int(
    os.getenv(
        "AURALIS_MAX_AUDIO_BYTES",
        str(25 * 1024 * 1024),
    )
)


def transcribe_audio(audio_path: str) -> str:
    """Transcribe one completed browser recording with Faster-Whisper."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Faster-Whisper is missing. "
            "Install it with: pip install faster-whisper"
        ) from exc

    model = WhisperModel(
        os.getenv("WHISPER_MODEL", "base"),
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
    )

    segments, info = model.transcribe(
        audio_path,
        vad_filter=True,
    )

    transcription = " ".join(
        segment.text.strip()
        for segment in segments
    ).strip()

    logger.info(
        "Whisper language: %s",
        getattr(info, "language", "unknown"),
    )

    if not transcription:
        raise ValueError(
            "No speech detected. Please record again."
        )

    return transcription


def create_ai_response(
    transcription: str,
    emotion_result: dict[str, Any],
) -> str:
    """Generate a local Ollama reply using emotion as uncertain context."""

    emotion = str(
        emotion_result.get("emotion", "Unknown")
    ).lower()

    confidence = float(
        emotion_result.get("confidence", 0.0)
    )

    if confidence < 0.60:
        emotion_context = (
            f"The audio model's tentative emotion estimate is {emotion} "
            f"({confidence:.0%} confidence). It may be wrong. "
            "Do not assume this is the user's actual feeling. "
            "Prioritize the meaning of the user's words."
        )
    else:
        emotion_context = (
            f"The audio model estimates {emotion} "
            f"({confidence:.0%} confidence), but this is only "
            "a fallible signal. Do not contradict the user's words."
        )

    prompt = (
        "You are Auralis, a calm and empathetic voice conversation partner. "
        "Reply naturally and briefly to the user's spoken message. "
        "Never tell the user what they feel as if you know for certain. "
        "If they say they are happy or excited, acknowledge that instead "
        "of assuming frustration.\n\n"
        f"Audio emotion context: {emotion_context}\n"
        f"User said: {transcription}\n"
        "Write a concise conversational reply."
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Auralis, calm and empathetic."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "stream": False,
            },
            timeout=90,
        )

        response.raise_for_status()

        answer = str(
            response.json()
            .get("message", {})
            .get("content", "")
        ).strip()

        if answer:
            return answer

        logger.warning("Ollama returned an empty answer")

    except requests.RequestException:
        logger.exception("Ollama request failed")

    return f"I heard you say: “{transcription}”"


def analyze_recording(audio_path: str) -> dict[str, Any]:
    """Transcribe speech, detect acoustic emotion, and generate a reply."""

    transcription = transcribe_audio(audio_path)
    emotion_result = detect_emotion(audio_path)

    ai_response = create_ai_response(
        transcription,
        emotion_result,
    )

    return {
        "transcription": transcription,
        "emotion_analysis": emotion_result,
        "response": ai_response,
    }


def save_audio_bytes(
    audio_bytes: bytes,
    suffix: str = ".webm",
) -> str:
    """Save received browser audio to a temporary file."""

    if not audio_bytes:
        raise ValueError(
            "No audio data received. Please record again."
        )

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError(
            "Recording is too large. Please record a shorter clip."
        )

    fd, audio_path = tempfile.mkstemp(
        prefix="auralis_recording_",
        suffix=suffix,
    )

    try:
        with os.fdopen(fd, "wb") as audio_file:
            audio_file.write(audio_bytes)

        return audio_path

    except Exception:
        try:
            os.remove(audio_path)
        except OSError:
            pass
        raise


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Auralis",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "Auralis",
    }


@app.post("/api/audio")
async def analyze_audio(
    file: UploadFile = File(...),
):
    """REST fallback for a completed recording."""

    audio_path = None
    suffix = Path(
        file.filename or "recording.webm"
    ).suffix or ".webm"

    try:
        audio_bytes = await file.read()

        audio_path = save_audio_bytes(
            audio_bytes,
            suffix,
        )

        result = await asyncio.to_thread(
            analyze_recording,
            audio_path,
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Audio analysis failed")

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    finally:
        await file.close()

        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                logger.warning(
                    "Could not remove temp audio: %s",
                    audio_path,
                )


@app.websocket("/ws/audio")
async def audio_websocket(
    websocket: WebSocket,
):
    """
    Receive binary MediaRecorder chunks.
    The frontend sends {"type": "end"} after the final chunk.
    The backend concatenates the chunks and analyses the recording once.
    """

    await websocket.accept()

    chunks: list[bytes] = []
    total_bytes = 0

    try:
        await websocket.send_json({
            "type": "status",
            "message": "Connected",
        })

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            binary_data = message.get("bytes")
            text_data = message.get("text")

            # Receive audio chunks from the browser.
            if binary_data is not None:
                total_bytes += len(binary_data)

                if total_bytes > MAX_AUDIO_BYTES:
                    chunks.clear()
                    total_bytes = 0

                    await websocket.send_json({
                        "type": "error",
                        "message": (
                            "Recording too large. "
                            "Please record a shorter clip."
                        ),
                    })
                    continue

                chunks.append(binary_data)

                await websocket.send_json({
                    "type": "progress",
                    "chunks_received": len(chunks),
                    "bytes_received": total_bytes,
                })

                continue

            if text_data is None:
                continue

            try:
                control = json.loads(text_data)

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": (
                        "Invalid control message; expected JSON."
                    ),
                })
                continue

            # Clear current recording.
            if control.get("type") == "reset":
                chunks.clear()
                total_bytes = 0

                await websocket.send_json({
                    "type": "status",
                    "message": "Recording reset",
                })
                continue

            # Wait until the frontend finishes recording.
            if control.get("type") != "end":
                continue

            if not chunks:
                await websocket.send_json({
                    "type": "error",
                    "message": (
                        "No audio chunks received. "
                        "Please record again."
                    ),
                })
                continue

            await websocket.send_json({
                "type": "status",
                "message": "Processing audio",
            })

            audio_path = None

            try:
                # Combine chunks and process the completed recording.
                combined_audio = b"".join(chunks)

                audio_path = save_audio_bytes(
                    combined_audio,
                    ".webm",
                )

                chunks.clear()
                total_bytes = 0

                result = await asyncio.to_thread(
                    analyze_recording,
                    audio_path,
                )

                await websocket.send_json({
                    "type": "transcription",
                    "transcription": result["transcription"],
                })

                await websocket.send_json({
                    "type": "emotion",
                    "emotion_analysis": result["emotion_analysis"],
                })

                await websocket.send_json({
                    "type": "response",
                    "response": result["response"],
                })

                await websocket.send_json({
                    "type": "complete",
                    "message": "Analysis complete",
                })

            except Exception as exc:
                logger.exception(
                    "WebSocket audio analysis failed"
                )

                await websocket.send_json({
                    "type": "error",
                    "message": str(exc),
                })

            finally:
                if audio_path and os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)

                    except OSError:
                        logger.warning(
                            "Could not remove temp audio: %s",
                            audio_path,
                        )

    except WebSocketDisconnect:
        logger.info("Auralis WebSocket disconnected")

    except Exception:
        logger.exception("Unexpected WebSocket error")

        try:
            await websocket.send_json({
                "type": "error",
                "message": (
                    "Unexpected server error while receiving audio."
                ),
            })
        except Exception:
            pass

    finally:
        chunks.clear()