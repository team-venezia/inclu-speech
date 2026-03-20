import { useState } from "react";
import type { TranscriptEntry } from "../types/messages";
import { SpeakerColumn } from "./SpeakerColumn";

interface TranscriptionViewProps {
  entries: TranscriptEntry[];
  onToggleTranslation: (speaker: number, targetLang: string, enabled: boolean) => void;
}

export function TranscriptionView({
  entries,
  onToggleTranslation,
}: TranscriptionViewProps) {
  const [translationState, setTranslationState] = useState<Record<number, string | null>>({
    1: null,
    2: null,
  });

  const handleToggle = (speaker: number, enabled: boolean) => {
    // Infer target language from what this speaker mostly speaks.
    // Look at the latest entries for this speaker to find their detected language,
    // then translate to the "other" language.
    const speakerEntries = entries.filter((e) => e.speaker === speaker && e.isFinal && e.lang);
    const lastLang = speakerEntries.length > 0
      ? speakerEntries[speakerEntries.length - 1].lang
      : "";
    const targetLang = lastLang.startsWith("es") ? "en" : "es";
    setTranslationState((prev) => ({ ...prev, [speaker]: enabled ? targetLang : null }));
    onToggleTranslation(speaker, targetLang, enabled);
  };

  return (
    <div className="transcription-view">
      <SpeakerColumn
        speaker={1}
        label="Speaker 1"
        color="#4fc3f7"
        accentBg="#0d2137"
        entries={entries}
        translationEnabled={translationState[1] !== null}
        onToggleTranslation={(enabled) => handleToggle(1, enabled)}
      />
      <div className="column-divider" />
      <SpeakerColumn
        speaker={2}
        label="Speaker 2"
        color="#81c784"
        accentBg="#0d2613"
        entries={entries}
        translationEnabled={translationState[2] !== null}
        onToggleTranslation={(enabled) => handleToggle(2, enabled)}
      />
    </div>
  );
}
