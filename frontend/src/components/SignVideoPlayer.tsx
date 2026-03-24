import { useEffect, useRef, useState, useCallback } from "react";
import type { SignEntry } from "../data/signVocabulary";

interface SignVideoPlayerProps {
  queue: SignEntry[];
  onQueueAdvance: () => void;
}

export function SignVideoPlayer({ queue, onQueueAdvance }: SignVideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentLabel, setCurrentLabel] = useState<string | null>(null);

  const current = queue.length > 0 ? queue[0] : null;

  const handleEnded = useCallback(() => {
    onQueueAdvance();
  }, [onQueueAdvance]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !current) {
      setCurrentLabel(null);
      return;
    }

    setCurrentLabel(current.label);
    video.src = `/signs/${current.videoFile}`;
    video.play().catch(() => {
      // Video not available — advance queue
      onQueueAdvance();
    });
  }, [current, onQueueAdvance]);

  if (!current) {
    return (
      <div className="sign-video-idle">
        <span>ASL signs will appear here</span>
      </div>
    );
  }

  return (
    <div className="sign-video-container">
      <video
        ref={videoRef}
        className="sign-video"
        onEnded={handleEnded}
        playsInline
        muted
      />
      {currentLabel && <div className="sign-label">{currentLabel}</div>}
    </div>
  );
}
