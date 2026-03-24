import { useTranscription } from "./hooks/useTranscription";
import { TranscriptionView } from "./components/TranscriptionView";
import { SessionControls } from "./components/SessionControls";
import "./App.css";

function App() {
  const {
    entries,
    status: _status,
    isSessionActive,
    error,
    elapsed,
    startSession,
    stopSession,
    toggleTranslation,
    aslState,
    toggleAsl,
    videoStream,
  } = useTranscription();

  return (
    <div className="app">
      {/* Top bar */}
      <header className="top-bar">
        <div className="brand">
          <div className="logo">I</div>
          <span className="app-name">IncluSpeech</span>
        </div>
        <div className="status-area">
          {isSessionActive && (
            <div className="status-badge">
              <div className="status-dot" />
              <span>Listening</span>
            </div>
          )}
          <div className="lang-badge">ES / EN</div>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      )}

      {/* Main content */}
      <main className="main-content">
        {isSessionActive ? (
          <TranscriptionView
            entries={entries}
            onToggleTranslation={toggleTranslation}
            aslState={aslState}
            onToggleAsl={toggleAsl}
            videoStream={videoStream}
          />
        ) : (
          <div className="welcome">
            <h1>IncluSpeech</h1>
            <p>Real-time transcription for inclusive conversations</p>
            <p className="hint">
              Place the device between both speakers and press Start.
            </p>
          </div>
        )}
      </main>

      {/* Bottom bar */}
      <footer className="bottom-bar">
        <SessionControls
          isSessionActive={isSessionActive}
          elapsed={elapsed}
          onStart={startSession}
          onStop={stopSession}
        />
      </footer>
    </div>
  );
}

export default App;
