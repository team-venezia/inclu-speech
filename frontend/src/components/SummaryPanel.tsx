import { useState } from "react";

interface SummaryPanelProps {
  speakers: Record<string, { en: string[]; es: string[] }>;
}

export function SummaryPanel({ speakers }: SummaryPanelProps) {
  const [lang, setLang] = useState<"en" | "es">("en");

  const speakerEntries = Object.entries(speakers).sort(
    ([a], [b]) => Number(a) - Number(b)
  );

  const speakerColors: Record<string, string> = {
    "1": "var(--speaker-1)",
    "2": "var(--speaker-2)",
  };

  return (
    <div className="summary-panel">
      <div className="summary-header">
        <h2 className="summary-title">Session Summary</h2>
        <div className="summary-lang-tabs">
          <button
            className={`summary-lang-tab ${lang === "en" ? "active" : ""}`}
            onClick={() => setLang("en")}
          >
            EN
          </button>
          <button
            className={`summary-lang-tab ${lang === "es" ? "active" : ""}`}
            onClick={() => setLang("es")}
          >
            ES
          </button>
        </div>
      </div>
      <div className="summary-columns">
        {speakerEntries.map(([spk, data]) => (
          <div key={spk} className="summary-speaker">
            <div className="summary-speaker-label">
              <span
                className="summary-speaker-dot"
                style={{ background: speakerColors[spk] ?? "var(--text-muted)" }}
              />
              <span style={{ color: speakerColors[spk] ?? "var(--text-muted)" }}>
                Speaker {spk}
              </span>
            </div>
            <ul className="summary-bullets">
              {data[lang].map((bullet, i) => (
                <li key={i}>{bullet}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
