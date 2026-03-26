import { useState } from "react";

interface SummaryPanelProps {
  speakers: Record<string, { en: string[]; es: string[] }>;
  onClose: () => void;
}

export function SummaryPanel({ speakers, onClose }: SummaryPanelProps) {
  const [lang, setLang] = useState<"en" | "es">("en");

  const speakerEntries = Object.entries(speakers).sort(
    ([a], [b]) => Number(a) - Number(b)
  );

  const speakerColors: Record<string, string> = {
    "1": "var(--speaker-1)",
    "2": "var(--speaker-2)",
  };

  const speakerColorValues: Record<string, string> = {
    "1": "#4fc3f7",
    "2": "#81c784",
  };

  function esc(text: string): string {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function exportPdf() {
    const date = new Date().toLocaleString();

    const speakerSections = speakerEntries
      .map(([spk, data]) => {
        const color = speakerColorValues[spk] ?? "#888";
        const enBullets = data.en.map((b) => `<li>${esc(b)}</li>`).join("");
        const esBullets = data.es.map((b) => `<li>${esc(b)}</li>`).join("");
        return `
          <div class="speaker">
            <h3 style="color:${color}">Speaker ${esc(spk)}</h3>
            <div class="cols">
              <div class="col"><h4>English</h4><ul>${enBullets}</ul></div>
              <div class="col"><h4>Español</h4><ul>${esBullets}</ul></div>
            </div>
          </div>`;
      })
      .join("");

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>IncluSpeech — Session Summary</title>
  <style>
    body { font-family: system-ui, sans-serif; color: #1a1a1a; padding: 32px; max-width: 820px; margin: 0 auto; }
    h1 { font-size: 20px; margin-bottom: 4px; }
    .date { font-size: 12px; color: #666; margin-bottom: 24px; }
    .speaker { margin-bottom: 28px; border-top: 1px solid #e0e0e0; padding-top: 16px; }
    h3 { font-size: 15px; margin: 0 0 12px; }
    .cols { display: flex; gap: 32px; }
    .col { flex: 1; }
    h4 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin: 0 0 8px; }
    ul { margin: 0; padding-left: 16px; }
    li { font-size: 13px; line-height: 1.6; margin-bottom: 4px; }
    @media print { body { padding: 16px; } }
  </style>
</head>
<body>
  <h1>IncluSpeech — Session Summary</h1>
  <div class="date">${esc(date)}</div>
  ${speakerSections}
</body>
</html>`;

    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const win = window.open(url, "_blank");
    if (win) {
      win.addEventListener("load", () => {
        win.print();
        URL.revokeObjectURL(url);
      });
    }
  }

  return (
    <div className="summary-panel">
      <div className="summary-header">
        <h2 className="summary-title">Session Summary</h2>
        <div className="summary-actions">
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
          <button className="summary-export-btn" onClick={exportPdf}>
            Export PDF
          </button>
          <button className="summary-close-btn" onClick={onClose} aria-label="Close summary">
            ✕
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
