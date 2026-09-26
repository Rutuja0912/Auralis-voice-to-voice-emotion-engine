# Continuous Speech Testing

## Test Objective
Verify Auralis speech-to-text processing with continuous speech input.

## Test File
- File: WhatsApp Video 2026-09-26 at 8.07.26 PM.mp4
- Content Type: video/mp4

## Test Result
- API Status: 200 OK
- Language Detected: English
- Speech-to-Text: Successful
- Emotion Detection: Successful
- Detected Emotion: sad
- Emotion Confidence: 0.9978

## Observation
The system successfully processed continuous speech and generated a complete transcription.

Some technical terms were not recognized accurately by the speech-to-text model, such as LLM, APIs and other technical words.

## Conclusion
Continuous speech processing is working successfully through the FastAPI backend using Faster-Whisper.

The test also confirms that speech transcription and emotion detection can be performed from the uploaded audio/video file.