from fastapi import FastAPI
from fastapi import UploadFile, File
from backend.whisper_service import transcribe_audio
from backend.emotion_service import detect_emotion

app = FastAPI(title="Auralis API")


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
    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    result = transcribe_audio(file_path)
    emotion = detect_emotion(file_path)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "transcription": result["text"],
        "language": result["language"],
        "emotion": emotion["emotion"],
        "emotion_confidence": emotion["confidence"]
    }