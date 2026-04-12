import React, { useRef, useEffect, useState } from 'react';
import './VideoMonitor.css';

function VideoMonitor({ sessionId }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [error, setError] = useState(null);
  const streamRef = useRef(null);

  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: 'user',
          },
        });

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setCameraActive(true);
        }
      } catch (err) {
        setError(`Camera access denied: ${err.message}`);
        setCameraActive(false);
      }
    };

    startCamera();

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return (
    <div className="video-monitor">
      <div className="camera-container">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="camera-feed"
        />
        <canvas
          ref={canvasRef}
          className="tracking-overlay"
          style={{ display: 'none' }}
        />

        {!cameraActive && (
          <div className="camera-fallback">
            <p>Camera not initialized</p>
            {error && <p className="error">{error}</p>}
          </div>
        )}

        <div className="camera-info">
          <span className={`status-indicator ${cameraActive ? 'active' : 'inactive'}`}></span>
          <span>{cameraActive ? 'Camera Active' : 'Camera Inactive'}</span>
        </div>
      </div>

      <div className="monitoring-info">
        <h3>Multimodal Monitoring</h3>
        <ul>
          <li>Eye tracking (iris landmarks)</li>
          <li>Lip aperture analysis</li>
          <li>Gaze drift detection</li>
          <li>Object detection (phones, extra persons)</li>
          <li>Audio-visual sync checking</li>
        </ul>
        <p className="info-text">
          All monitoring is sent to SENTINEL for integrity analysis.
          Data is processed server-side; no tracking data leaves the session.
        </p>
      </div>
    </div>
  );
}

export default VideoMonitor;
