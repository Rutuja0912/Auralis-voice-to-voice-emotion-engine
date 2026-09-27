import { useRef, useState } from "react";

function App() {
  const [recording, setRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
    });

    const mediaRecorder = new MediaRecorder(stream);

    mediaRecorderRef.current = mediaRecorder;
    audioChunksRef.current = [];

    mediaRecorder.ondataavailable = (event) => {
      audioChunksRef.current.push(event.data);
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunksRef.current, {
        type: "audio/webm",
      });

      const url = URL.createObjectURL(audioBlob);
      setAudioUrl(url);

      stream.getTracks().forEach((track) => track.stop());
    };

    mediaRecorder.start();
    setRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current.stop();
    setRecording(false);
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
};

export default App;