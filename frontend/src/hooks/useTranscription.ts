import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ClientMessage,
  ServerMessage,
  TranscriptEntry,
  TranscriptMessage,
  TranslationMessage,
} from "../types/messages";

const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/transcribe`;
const SAMPLE_RATE = 16000;

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export function useTranscription() {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const intentionalCloseRef = useRef(false);

  const sendControl = useCallback((msg: ClientMessage) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }, []);

  const handleServerMessage = useCallback((event: MessageEvent) => {
    if (typeof event.data !== "string") return;
    const msg: ServerMessage = JSON.parse(event.data);

    switch (msg.type) {
      case "session_started":
        break;

      case "transcript":
        setEntries((prev) => {
          const tm = msg as TranscriptMessage;
          const existing = prev.findIndex((e) => e.id === tm.id);
          const entry: TranscriptEntry = {
            id: tm.id,
            speaker: tm.speaker,
            source: tm.source,
            text: tm.text,
            lang: tm.lang,
            isFinal: tm.isFinal,
            timestamp: tm.timestamp,
          };
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = { ...updated[existing], ...entry };
            return updated;
          }
          return [...prev, entry];
        });
        break;

      case "translation":
        setEntries((prev) => {
          const tl = msg as TranslationMessage;
          return prev.map((e) =>
            e.id === tl.refId ? { ...e, translation: tl.text } : e
          );
        });
        break;

      case "error":
        setError(msg.message);
        break;

      case "session_stopped":
        setIsSessionActive(false);
        break;
    }
  }, []);

  const connect = useCallback(() => {
    setStatus("connecting");
    setError(null);
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setStatus("connected");
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = handleServerMessage;

    ws.onclose = () => {
      setStatus("disconnected");
      if (intentionalCloseRef.current) {
        intentionalCloseRef.current = false;
        return;
      }
      if (reconnectAttemptsRef.current < 3) {
        const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000;
        reconnectAttemptsRef.current++;
        setTimeout(connect, delay);
        setStatus("connecting");
      } else {
        setError("Connection lost. Please retry.");
      }
    };

    ws.onerror = () => {
      setStatus("error");
    };

    wsRef.current = ws;
  }, [handleServerMessage]);

  const startSession = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioContextRef.current = audioContext;

      // Load audio worklet for PCM capture
      const workletCode = `
        class PCMProcessor extends AudioWorkletProcessor {
          process(inputs) {
            const input = inputs[0];
            if (input.length > 0) {
              const float32 = input[0];
              const int16 = new Int16Array(float32.length);
              for (let i = 0; i < float32.length; i++) {
                const s = Math.max(-1, Math.min(1, float32[i]));
                int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
              }
              this.port.postMessage(int16.buffer, [int16.buffer]);
            }
            return true;
          }
        }
        registerProcessor('pcm-processor', PCMProcessor);
      `;
      const blob = new Blob([workletCode], { type: "application/javascript" });
      const url = URL.createObjectURL(blob);
      await audioContext.audioWorklet.addModule(url);
      URL.revokeObjectURL(url);

      const workletNode = new AudioWorkletNode(audioContext, "pcm-processor");
      workletNodeRef.current = workletNode;

      workletNode.port.onmessage = (event: MessageEvent) => {
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(event.data as ArrayBuffer);
        }
      };

      const source = audioContext.createMediaStreamSource(stream);
      source.connect(workletNode);
      // Do NOT connect to audioContext.destination — that would play audio back through speakers

      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connect();
        // Wait for connection with timeout
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => {
            clearInterval(check);
            reject(new Error("Connection timeout"));
          }, 5000);
          const check = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              clearInterval(check);
              clearTimeout(timeout);
              resolve();
            }
          }, 50);
        });
      }

      sendControl({ type: "start_session", config: { sampleRate: SAMPLE_RATE } });
      setIsSessionActive(true);
      setEntries([]);
      setElapsed(0);

      timerRef.current = window.setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      setError(
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone access denied. Please allow microphone access in your browser settings."
          : `Failed to start session: ${err}`
      );
    }
  }, [connect, sendControl]);

  const stopSession = useCallback(() => {
    sendControl({ type: "stop_session" });
    setIsSessionActive(false);

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, [sendControl]);

  const toggleTranslation = useCallback(
    (speaker: number, targetLang: string, enabled: boolean) => {
      sendControl({ type: "toggle_translation", speaker, targetLang, enabled });
    },
    [sendControl]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      intentionalCloseRef.current = true;
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  return {
    entries,
    status,
    isSessionActive,
    error,
    elapsed,
    startSession,
    stopSession,
    toggleTranslation,
    connect,
  };
}
