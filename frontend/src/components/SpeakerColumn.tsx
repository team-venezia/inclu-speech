import { useCallback, useEffect, useRef, useState } from "react";
import type { TranscriptEntry } from "../types/messages";
import { matchSigns, type SignEntry } from "../data/signVocabulary";
import { CameraCapture } from "./CameraCapture";
import { SignVideoPlayer } from "./SignVideoPlayer";

interface SpeakerColumnProps {
  speaker: number;
  label: string;
  color: string;
  accentBg: string;
  entries: TranscriptEntry[];
  translationEnabled: boolean;
  onToggleTranslation: (enabled: boolean) => void;
  aslDirection: string | null;
  onToggleAsl: (enabled: boolean, direction: "sign_to_text" | "text_to_sign") => void;
  videoStream: MediaStream | null;
}

export function SpeakerColumn({
  speaker,
  label,
  color,
  accentBg,
  entries,
  translationEnabled,
  onToggleTranslation,
  aslDirection,
  onToggleAsl,
  videoStream,
}: SpeakerColumnProps) {
  const speakerEntries = entries.filter((e) => e.speaker === speaker);
  const entriesRef = useRef<HTMLDivElement>(null);
  const [signQueue, setSignQueue] = useState<SignEntry[]>([]);
  const lastProcessedIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (entriesRef.current) {
      entriesRef.current.scrollTop = entriesRef.current.scrollHeight;
    }
  }, [speakerEntries.length]);

  // Text-to-sign: scan new final speech entries for vocabulary matches
  useEffect(() => {
    if (aslDirection !== "text_to_sign") return;
    const finalEntries = speakerEntries.filter((e) => e.isFinal && e.source === "speech");
    if (finalEntries.length === 0) return;
    const latest = finalEntries[finalEntries.length - 1];
    if (latest.id === lastProcessedIdRef.current) return;
    lastProcessedIdRef.current = latest.id;
    const matches = matchSigns(latest.text);
    if (matches.length > 0) {
      setSignQueue((prev) => [...prev, ...matches]);
    }
  }, [speakerEntries, aslDirection]);

  const advanceQueue = useCallback(() => {
    setSignQueue((prev) => prev.slice(1));
  }, []);

  return (
    <div className="speaker-column">
      <div className="speaker-header">
        <div className="speaker-info">
          <div className="speaker-avatar" style={{ background: color }}>
            {String.fromCharCode(64 + speaker)}
          </div>
          <span className="speaker-label" style={{ color }}>
            {label}
          </span>
        </div>
        <div className="header-buttons">
          <button
            className={`translate-btn ${translationEnabled ? "active" : ""}`}
            style={{
              background: translationEnabled ? accentBg : "transparent",
              color,
              borderColor: color,
            }}
            onClick={() => onToggleTranslation(!translationEnabled)}
          >
            🌐 Translate
          </button>
          <button
            className={`asl-btn ${aslDirection ? "active" : ""}`}
            onClick={() => {
              if (aslDirection) {
                onToggleAsl(false, aslDirection as "sign_to_text" | "text_to_sign");
              } else {
                onToggleAsl(true, "sign_to_text");
              }
            }}
          >
            {aslDirection ? "🤟 ASL ON" : "🤟 ASL"}
          </button>
        </div>
      </div>

      {aslDirection && (
        <div className="asl-media-area">
          <div className="asl-direction-tabs">
            <button
              className={`asl-direction-tab ${aslDirection === "sign_to_text" ? "active" : ""}`}
              onClick={() => onToggleAsl(true, "sign_to_text")}
            >
              📷 Sign → Text
            </button>
            <button
              className={`asl-direction-tab ${aslDirection === "text_to_sign" ? "active" : ""}`}
              onClick={() => onToggleAsl(true, "text_to_sign")}
            >
              🎬 Text → Sign
            </button>
          </div>
          {aslDirection === "sign_to_text" ? (
            <CameraCapture stream={videoStream} />
          ) : (
            <SignVideoPlayer queue={signQueue} onQueueAdvance={advanceQueue} />
          )}
        </div>
      )}

      <div className="entries" ref={entriesRef}>
        {speakerEntries.map((entry) => (
          <div
            key={entry.id}
            className={`entry ${entry.isFinal ? "" : "partial"}`}
            style={{ borderLeftColor: color }}
          >
            <div className="entry-text">{entry.text}</div>
            {entry.translation && (
              <div className="entry-translation">{entry.translation}</div>
            )}
            <div className="entry-meta">
              {entry.timestamp != null
                ? `${Math.floor(entry.timestamp / 60)}:${String(Math.floor(entry.timestamp % 60)).padStart(2, "0")}`
                : ""}
              {entry.lang ? ` · ${entry.lang.split("-")[0].toUpperCase()}` : ""}
              {!entry.isFinal && " · speaking..."}
              {entry.source === "sign" && (
                <span className="asl-badge">
                  via ASL{entry.confidence != null ? ` · ${Math.round(entry.confidence * 100)}%` : ""}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
