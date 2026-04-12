import React, { useState, useRef, useEffect } from 'react';
import './AudioRecorder.css';

function AudioRecorder({ onSubmit, disabled }) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordedAudio, setRecordedAudio] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
        },
      });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setRecordedAudio(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording:', err);
      alert('Unable to access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      // Stop all tracks
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    }
  };

  const handleSubmit = async () => {
    if (!recordedAudio) {
      alert('Please record a response first');
      return;
    }

    setIsProcessing(true);
    try {
      await onSubmit(recordedAudio);
      setRecordedAudio(null);
      audioChunksRef.current = [];
    } catch (err) {
      console.error('Failed to submit response:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handlePlayback = async () => {
    if (!recordedAudio) return;

    const url = URL.createObjectURL(recordedAudio);
    const audio = new Audio(url);
    audio.play();
  };

  const handleRetake = () => {
    setRecordedAudio(null);
    audioChunksRef.current = [];
  };

  return (
    <div className="audio-recorder">
      {!recordedAudio ? (
        <div className="recording-controls">
          {!isRecording ? (
            <button
              className="record-btn start"
              onClick={startRecording}
              disabled={disabled || isProcessing}
            >
              Start Recording
            </button>
          ) : (
            <div className="recording-indicator">
              <div className="recording-pulse"></div>
              <span>Recording...</span>
              <button
                className="record-btn stop"
                onClick={stopRecording}
              >
                Stop Recording
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="playback-controls">
          <p className="recorded-text">Response recorded</p>
          <button
            className="playback-btn"
            onClick={handlePlayback}
          >
            Play Response
          </button>
          <div className="action-buttons">
            <button
              className="submit-btn"
              onClick={handleSubmit}
              disabled={isProcessing}
            >
              {isProcessing ? 'Processing...' : 'Submit Response'}
            </button>
            <button
              className="retake-btn"
              onClick={handleRetake}
              disabled={isProcessing}
            >
              Retake Recording
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default AudioRecorder;
