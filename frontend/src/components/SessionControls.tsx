interface SessionControlsProps {
  isSessionActive: boolean;
  elapsed: number;
  onStart: () => void;
  onStop: () => void;
}

export function SessionControls({
  isSessionActive,
  elapsed,
  onStart,
  onStop,
}: SessionControlsProps) {
  const minutes = Math.floor(elapsed / 60);
  const seconds = String(elapsed % 60).padStart(2, "0");

  return (
    <div className="session-controls">
      {isSessionActive ? (
        <>
          <button className="stop-btn" onClick={onStop} aria-label="Stop session">
            <div className="stop-icon" />
          </button>
          <span className="elapsed">
            {minutes}:{seconds} elapsed
          </span>
        </>
      ) : (
        <button className="start-btn" onClick={onStart} aria-label="Start session">
          <div className="start-icon" />
          <span>Start Conversation</span>
        </button>
      )}
    </div>
  );
}
