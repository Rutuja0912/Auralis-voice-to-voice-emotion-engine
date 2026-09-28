
import { useRef, useState } from "react";

function App() {
  const [recording, setRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startRecording = async () => {
    try {
      setError("");
      setResult(null);

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType || "audio/webm",
        });

        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);

        stream.getTracks().forEach((track) => track.stop());

        const formData = new FormData();
        formData.append("file", audioBlob, "recording.webm");

        setLoading(true);

        try {
          const response = await fetch("http://127.0.0.1:8000/api/audio", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
          }

          const data = await response.json();
          setResult(data);
        } catch (err) {
          setError(
            err.message || "Audio upload failed. Please try again."
          );
        } finally {
          setLoading(false);
        }
      };

      mediaRecorder.start();
      setRecording(true);
    } catch (err) {
      setError("Microphone access failed. Please allow microphone permission.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  };

  return (
    <div style={styles.container}>
      <h1>Auralis</h1>
      <p>Real-Time Voice-to-Voice Emotion Engine</p>

      <div style={styles.card}>
        <h2>Voice Input</h2>

        <p>
          {recording
            ? "🎙️ Recording in progress..."
            : "Click the button to start recording"}
        </p>

        {!recording ? (
          <button style={styles.button} onClick={startRecording}>
            🎙️ Start Recording
          </button>
        ) : (
          <button style={styles.stopButton} onClick={stopRecording}>
            ⏹️ Stop Recording
          </button>
        )}

        {audioUrl && (
          <div style={{ marginTop: "25px" }}>
            <p>Recorded Audio:</p>
            <audio controls src={audioUrl} />
          </div>
        )}

        {loading && <p>⏳ Processing audio, please wait...</p>}

        {error && <p style={styles.error}>{error}</p>}

        {result && (
          <div style={styles.result}>
            <h2>Analysis Result</h2>
            <p><strong>Transcription:</strong></p>
            <p>{result.transcription || "No speech detected"}</p>
            <p><strong>Language:</strong> {result.language || "Unknown"}</p>
            <p><strong>Emotion:</strong> {result.emotion || "Unknown"}</p>
            <p>
              <strong>Emotion Confidence:</strong>{" "}
              {result.emotion_confidence ?? "N/A"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    backgroundColor: "#20232a",
    color: "white",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "Arial",
  },
  card: {
    backgroundColor: "#282c34",
    padding: "40px",
    borderRadius: "15px",
    textAlign: "center",
    width: "400px",
    maxWidth: "90%",
  },
  button: {
    padding: "12px 25px",
    border: "none",
    borderRadius: "8px",
    backgroundColor: "#61dafb",
    fontSize: "16px",
    cursor: "pointer",
  },
  stopButton: {
    padding: "12px 25px",
    border: "none",
    borderRadius: "8px",
    backgroundColor: "#ff4d4d",
    color: "white",
    fontSize: "16px",
    cursor: "pointer",
  },
  result: {
    marginTop: "25px",
    padding: "15px",
    backgroundColor: "#20232a",
    borderRadius: "10px",
    textAlign: "left",
    overflowWrap: "anywhere",
  },
  error: {
    color: "#ff8080",
    marginTop: "20px",
  },
};

export default App;