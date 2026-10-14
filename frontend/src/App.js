import { useRef, useState } from "react";

function App() {
  const [recording, setRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const [wsStatus, setWsStatus] = useState("Disconnected");
  const [chunksSent, setChunksSent] = useState(0);
  const [wsTranscription, setWsTranscription] = useState("");

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const websocketRef = useRef(null);

  const startRecording = async () => {
    let stream;
    let websocket;

    try {
      setError("");
      setResult(null);
      setWsTranscription("");
      setChunksSent(0);
      setLoading(false);
      setRecording(false);
      setWsStatus("Connecting");

      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);
      }

      // Request microphone access
      stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      // Create WebSocket connection
      websocket = new WebSocket("ws://127.0.0.1:8000/ws/audio");
      websocketRef.current = websocket;

      // Handle WebSocket messages
      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message.status === "received") {
            setChunksSent((prev) => prev + 1);
          } else if (message.status === "processing") {
            setLoading(true);
            setWsStatus("Processing");
          } else if (
            message.status === "analysis" ||
            message.status === "transcription"
          ) {
            const analysisResult = {
              transcription: message.transcription || "",
              language: message.language || "Unknown",
              emotion: message.emotion || "Unknown",
              confidence: message.confidence ?? null,
              raw_emotion: message.raw_emotion || "N/A",
              llm_response: message.llm_response || "",
            };

            setWsTranscription(analysisResult.transcription);
            setResult(analysisResult);
            setWsStatus("Transcription received");
            setError("");
            setLoading(false);

            console.log("WEBSOCKET ANALYSIS RESULT:", message);
          } else if (message.status === "error") {
            setError(
              message.message || "WebSocket processing failed."
            );
            setWsStatus("Error");
            setLoading(false);
          }
        } catch (err) {
          console.error("Invalid WebSocket message:", err);
          setError("Received an invalid WebSocket message.");
          setWsStatus("Error");
          setLoading(false);
        }
      };

      websocket.onerror = () => {
        setError("WebSocket connection or streaming failed.");
        setWsStatus("Error");
        setLoading(false);
      };

      websocket.onclose = () => {
        if (websocketRef.current === websocket) {
          websocketRef.current = null;
        }

        setWsStatus((prev) =>
          prev === "Transcription received" || prev === "Error"
            ? prev
            : "Disconnected"
        );

        setLoading(false);
      };

      // Wait until WebSocket connects
      await new Promise((resolve, reject) => {
        const handleOpen = () => {
          setWsStatus("Connected");
          resolve();
        };

        const handleClose = () => {
          reject(
            new Error("WebSocket disconnected before connecting.")
          );
        };

        const handleError = () => {
          reject(new Error("WebSocket connection failed."));
        };

        websocket.addEventListener("open", handleOpen, {
          once: true,
        });

        websocket.addEventListener("close", handleClose, {
          once: true,
        });

        websocket.addEventListener("error", handleError, {
          once: true,
        });
      });

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      // Receive and send audio chunks
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          // Keep chunks for recorded audio playback
          audioChunksRef.current.push(event.data);

          // Send audio chunks through WebSocket only
          if (websocket.readyState === WebSocket.OPEN) {
            websocket.send(event.data);
          }
        }
      };

      // Process audio when recording stops
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType || "audio/webm",
        });

        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);

        // Stop microphone tracks
        stream.getTracks().forEach((track) => track.stop());

        // WebSocket is the single audio analysis flow
        if (websocket.readyState === WebSocket.OPEN) {
          setLoading(true);
          setError("");
          setWsStatus("Processing");

          // Send only one end signal
          websocket.send(JSON.stringify({ type: "end" }));
        } else {
          setLoading(false);
          setError(
            "WebSocket disconnected. Please try recording again."
          );
          setWsStatus("Disconnected");
        }

        // No REST upload here.
        // The final result is received through WebSocket.
      };

      // Emit audio chunks approximately every second
      mediaRecorder.start(1000);
      setRecording(true);
    } catch (err) {
      console.error("Recording error:", err);

      setError(
        err.message ||
          "Unable to start recording. Check microphone permission and backend."
      );

      setWsStatus("Disconnected");
      setLoading(false);
      setRecording(false);

      // Stop microphone if setup failed
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }

      // Close WebSocket if setup failed
      if (
        websocket &&
        websocket.readyState < WebSocket.CLOSING
      ) {
        websocket.close();
      }

      websocketRef.current = null;
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
      <h1 style={styles.title}>Auralis</h1>

      <p style={styles.subtitle}>
        Real-Time Voice-to-Voice Emotion Engine
      </p>

      <div style={styles.card}>
        <h2>Voice Input</h2>

        <p>
          {recording
            ? "🎙️ Recording in progress..."
            : "Click the button to start recording"}
        </p>

        {/* WebSocket Status */}
        <p>
          <strong>WebSocket Status:</strong>{" "}
          <span
            style={{
              color:
                wsStatus === "Connected" ||
                wsStatus === "Transcription received"
                  ? "#61dafb"
                  : wsStatus === "Error"
                  ? "#ff6b6b"
                  : "#ffb86c",
            }}
          >
            {wsStatus}
          </span>
        </p>

        {/* Audio Chunks */}
        <p>
          <strong>Audio Chunks Received:</strong> {chunksSent}
        </p>

        {/* Recording Buttons */}
        {!recording ? (
          <button
            style={styles.button}
            onClick={startRecording}
            disabled={loading}
          >
            🎙️ Start Recording
          </button>
        ) : (
          <button
            style={styles.stopButton}
            onClick={stopRecording}
          >
            ⏹️ Stop Recording
          </button>
        )}

        {/* Recorded Audio */}
        {audioUrl && (
          <div style={styles.audioSection}>
            <p>
              <strong>Recorded Audio</strong>
            </p>

            <audio controls src={audioUrl} />
          </div>
        )}

        {/* Loading */}
        {loading && (
          <p style={styles.loading}>
            ⏳ Processing audio, please wait...
          </p>
        )}

        {/* Error */}
        {error && <p style={styles.error}>{error}</p>}

        {/* WebSocket Transcription */}
        {wsTranscription && (
          <div style={styles.result}>
            <h2>📝 WebSocket Transcription</h2>
            <p>{wsTranscription}</p>
          </div>
        )}

        {/* Auralis AI Response */}
        {result?.llm_response && (
          <div style={styles.result}>
            <h2>🧠 Auralis Response</h2>
            <p>{result.llm_response}</p>
          </div>
        )}

        {/* Emotion Analysis */}
        {result && (
          <div style={styles.analysisCard}>
            <h2>🎯 Emotion Analysis</h2>

            {/* Transcription */}
            <div style={styles.resultItem}>
              <strong>Transcription</strong>
              <p>{result.transcription || "No speech detected"}</p>
            </div>

            {/* Language */}
            <div style={styles.resultItem}>
              <strong>Language</strong>
              <p>{result.language || "Unknown"}</p>
            </div>

            {/* Emotion */}
            <div style={styles.emotionBox}>
              <span style={styles.emotionIcon}>🎭</span>

              <div>
                <strong>Detected Emotion</strong>
                <p style={styles.emotionText}>
                  {result.emotion || "Unknown"}
                </p>
              </div>
            </div>

            {/* Confidence */}
            <div style={styles.confidenceBox}>
              <strong>Emotion Confidence</strong>

              <p style={styles.confidenceText}>
                {result.confidence != null
                  ? `${(result.confidence * 100).toFixed(2)}%`
                  : "N/A"}
              </p>
            </div>

            {/* Raw Model Label */}
            <div style={styles.resultItem}>
              <strong>Raw Emotion Label</strong>
              <p>{result.raw_emotion || "N/A"}</p>
            </div>
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
    fontFamily: "Arial, sans-serif",
    padding: "20px",
  },

  title: {
    marginBottom: "5px",
  },

  subtitle: {
    color: "#b8c1cc",
    marginTop: "0",
    marginBottom: "25px",
    textAlign: "center",
  },

  card: {
    backgroundColor: "#282c34",
    padding: "40px",
    borderRadius: "15px",
    textAlign: "center",
    width: "450px",
    maxWidth: "95%",
    boxSizing: "border-box",
    boxShadow: "0 8px 25px rgba(0, 0, 0, 0.3)",
  },

  button: {
    padding: "12px 25px",
    border: "none",
    borderRadius: "8px",
    backgroundColor: "#61dafb",
    color: "#20232a",
    fontWeight: "bold",
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
    fontWeight: "bold",
    cursor: "pointer",
  },

  audioSection: {
    marginTop: "25px",
  },

  loading: {
    color: "#61dafb",
    marginTop: "20px",
  },

  result: {
    marginTop: "25px",
    padding: "18px",
    backgroundColor: "#20232a",
    borderRadius: "10px",
    textAlign: "left",
    overflowWrap: "anywhere",
  },

  analysisCard: {
    marginTop: "25px",
    padding: "20px",
    backgroundColor: "#20232a",
    borderRadius: "12px",
    textAlign: "left",
    border: "1px solid #3d4350",
  },

  resultItem: {
    marginTop: "15px",
    padding: "12px",
    backgroundColor: "#282c34",
    borderRadius: "8px",
    overflowWrap: "anywhere",
  },

  emotionBox: {
    marginTop: "15px",
    padding: "15px",
    backgroundColor: "#282c34",
    borderRadius: "10px",
    display: "flex",
    alignItems: "center",
    gap: "15px",
  },

  emotionIcon: {
    fontSize: "32px",
  },

  emotionText: {
    fontSize: "22px",
    fontWeight: "bold",
    margin: "5px 0 0 0",
  },

  confidenceBox: {
    marginTop: "15px",
    padding: "15px",
    backgroundColor: "#282c34",
    borderRadius: "10px",
  },

  confidenceText: {
    fontSize: "22px",
    fontWeight: "bold",
    color: "#61dafb",
    margin: "8px 0 0 0",
  },

  error: {
    color: "#ff8080",
    marginTop: "20px",
    overflowWrap: "anywhere",
  },
};

export default App;