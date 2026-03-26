// --- Client to Server (text frames) ---

export interface StartSessionMessage {
  type: "start_session";
  config: { sampleRate: number };
}

export interface StopSessionMessage {
  type: "stop_session";
}

export interface ToggleTranslationMessage {
  type: "toggle_translation";
  speaker: number;
  targetLang: string;
  enabled: boolean;
}

export interface ToggleAslMessage {
  type: "toggle_asl";
  speaker: number;
  enabled: boolean;
  direction: "sign_to_text" | "text_to_sign";
}

export type ClientMessage =
  | StartSessionMessage
  | StopSessionMessage
  | ToggleTranslationMessage
  | ToggleAslMessage;

// Audio is sent as binary frames (not JSON), so no type here.

// --- Server to Client ---

export interface SessionStartedMessage {
  type: "session_started";
}

export interface SessionStoppedMessage {
  type: "session_stopped";
}

export interface TranscriptMessage {
  type: "transcript";
  id: string;
  speaker: number;
  source: "speech" | "sign";
  text: string;
  lang: string;
  isFinal: boolean;
  timestamp?: number;
  confidence?: number;
}

export interface TranslationMessage {
  type: "translation";
  refId: string;
  speaker: number;
  text: string;
  targetLang: string;
}

export interface ErrorMessage {
  type: "error";
  message: string;
  code: string;
}

export interface SummaryMessage {
  type: "summary";
  speakers: Record<string, { en: string[]; es: string[] }>;
}

export type ServerMessage =
  | SessionStartedMessage
  | SessionStoppedMessage
  | TranscriptMessage
  | TranslationMessage
  | SummaryMessage
  | ErrorMessage;

// --- UI state ---

export interface TranscriptEntry {
  id: string;
  speaker: number;
  source: "speech" | "sign";
  text: string;
  lang: string;
  isFinal: boolean;
  timestamp?: number;
  translation?: string;
  confidence?: number;
}
