import json
from starlette.concurrency import run_in_threadpool
import os
import tempfile

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    WebSocket,
    WebSocketDisconnect
)
from fastapi.middleware.cors import CORSMiddleware

from backend.whisper_service import transcribe_audio
from backend.emotion_service import detect_emotion
from backend.llm_service import generate_response


app = FastAPI(title="Auralis API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Auralis API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/api/audio")
async def upload_audio(file: UploadFile = File(...)):
    file_path = None

    try:
        # Read uploaded audio
        audio_data = await file.read()

        # Validate empty file
        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail="Uploaded audio file is empty"
            )

        # Get safe filename and preserve extension
        filename = os.path.basename(
            (file.filename or "audio_upload").replace("\\", "/")
        )
        extension = os.path.splitext(filename)[1]

        # Create a unique temporary file
        with tempfile.NamedTemporaryFile(
            prefix="auralis_",
            suffix=extension,
            delete=False
        ) as temp_file:
            file_path = temp_file.name
            temp_file.write(audio_data)

        # Speech-to-text
        result = transcribe_audio(file_path)

        # Emotion detection
        emotion = detect_emotion(file_path)

        print("DEBUG EMOTION:", emotion)

        # LLM Context Engine
        llm_response = generate_response(
            result["text"],
            emotion["emotion"]
        )

        print("DEBUG LLM RESPONSE:", llm_response)

        return {
            "filename": filename,
            "content_type": file.content_type,
            "transcription": result["text"],
            "language": result["language"],
            "confidence": emotion["confidence"],
            "emotion": emotion["emotion"],
            "raw_emotion": emotion["raw_emotion"],
            "llm_response": llm_response
        }

    except HTTPException:
        raise

    except Exception as e:
        print("Audio processing error:", e)

        raise HTTPException(
            status_code=500,
            detail="Audio processing failed. Please upload a valid audio file."
        )

    finally:
        # Remove temporary audio file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        # Close uploaded file
        await file.close()


@app.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket):
    await websocket.accept()

    print("WebSocket connection established")

    file_path = None

    try:
        with tempfile.NamedTemporaryFile(
            prefix="auralis_stream_",
            suffix=".webm",
            delete=False
        ) as temp_file:

            file_path = temp_file.name

            while True:
                message = await websocket.receive()

                if message.get("type") == "websocket.disconnect":
                    break

                audio_chunk = message.get("bytes")

                if audio_chunk:
                    temp_file.write(audio_chunk)

                    await websocket.send_json({
                        "status": "received",
                        "chunk_size": len(audio_chunk)
                    })

                elif message.get("text"):

                    try:
                        command = json.loads(message["text"])

                    except json.JSONDecodeError:
                        continue

                    if command.get("type") == "end":
                        break

        if file_path and os.path.getsize(file_path) > 0:

            await websocket.send_json({
                "status": "processing"
            })

            # Speech-to-text
            result = await run_in_threadpool(
                transcribe_audio,
                file_path
            )

            # Emotion detection
            emotion = await run_in_threadpool(
                detect_emotion,
                file_path
            )

            # LLM Context Engine
            llm_response = await run_in_threadpool(
                generate_response,
                result["text"],
                emotion["emotion"]
            )

            print("DEBUG EMOTION:", emotion)
            print("DEBUG LLM RESPONSE:", llm_response)

            await websocket.send_json({
                "status": "analysis",
                "transcription": result["text"],
                "language": result["language"],
                "emotion": emotion["emotion"],
                "confidence": emotion["confidence"],
                "raw_emotion": emotion["raw_emotion"],
                "llm_response": llm_response
            })

        else:

            await websocket.send_json({
                "status": "error",
                "message": "No audio received"
            })

    except WebSocketDisconnect:

        print("WebSocket connection closed")

    except Exception as e:

        print(f"WebSocket audio processing failed: {e}")

        try:
            await websocket.send_json({
                "status": "error",
                "message": "Audio processing failed"
            })

        except Exception:
            pass

    finally:

        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        if websocket.client_state.name == "CONNECTED":
            await websocket.close()