import { useEffect, useRef } from "react";
import type { TranscriptEntry } from "../types/messages";

interface SpeakerColumnProps {
  speaker: number;
  label: string;
  color: string;
  accentBg: string;
  entries: TranscriptEntry[];
  translationEnabled: boolean;
  onToggleTranslation: (enabled: boolean) => void;
}

export function SpeakerColumn({
  speaker,
  label,
  color,
  accentBg,
  entries,
  translationEnabled,
  onToggleTranslation,
}: SpeakerColumnProps) {
  const speakerEntries = entries.filter((e) => e.speaker === speaker);
  const entriesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (entriesRef.current) {
      entriesRef.current.scrollTop = entriesRef.current.scrollHeight;
    }
  }, [speakerEntries.length]);

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
      </div>

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
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
