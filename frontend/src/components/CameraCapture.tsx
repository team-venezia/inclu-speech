import { useEffect, useRef } from "react";

interface CameraCaptureProps {
  stream: MediaStream | null;
}

export function CameraCapture({ stream }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (stream) {
      video.srcObject = stream;
      video.play().catch(() => {});
    } else {
      video.srcObject = null;
    }
  }, [stream]);

  if (!stream) {
    return (
      <div className="camera-placeholder">
        <span>Camera not available</span>
      </div>
    );
  }

  return (
    <video
      ref={videoRef}
      className="camera-preview"
      autoPlay
      playsInline
      muted
    />
  );
}
