
import os
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.whisper_service import transcribe_audio
from backend.emotion_service import detect_emotion


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

        return {
            "filename": filename,
            "content_type": file.content_type,
            "transcription": result["text"],
            "language": result["language"],
            "emotion": emotion["emotion"],
            "emotion_confidence": emotion["confidence"]
        }

    except HTTPException:
        raise

    except Exception:
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

    try:
        while True:
            audio_chunk = await websocket.receive_bytes()

            print(f"Received audio chunk: {len(audio_chunk)} bytes")

            await websocket.send_json({
                "status": "received",
                "chunk_size": len(audio_chunk)
            })

    except WebSocketDisconnect:
        print("WebSocket connection closed")