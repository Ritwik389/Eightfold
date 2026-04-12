import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import useWebSocket from 'react-use-websocket';
import VideoMonitor from './VideoMonitor';
import AudioRecorder from './AudioRecorder';
import MonitoringDashboard from './MonitoringDashboard';
import './InterviewSession.css';

function InterviewSession({ sessionId, config, onEndSession }) {
  const [question, setQuestion] = useState(config?.initialQuestion || '');
  const [audioUrl, setAudioUrl] = useState(config?.initialAudioUrl || null);
  const [currentTurn, setCurrentTurn] = useState(config?.currentTurn || 0);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [report, setReport] = useState(null);
  const [integrityScore, setIntegrityScore] = useState(0);
  const [classification, setClassification] = useState('CLEAN');
  const audioRef = useRef(new Audio());

  const { sendMessage, lastMessage, readyState } = useWebSocket(
    `ws://localhost:8000/ws/interview/${sessionId}`,
    { shouldReconnect: () => true }
  );

  // Handle WebSocket monitoring events
  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data);
        if (data.type === 'turn_complete') {
          setIntegrityScore(data.data.integrity_score);
          setClassification(data.data.classification);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    }
  }, [lastMessage]);

  // Initialize question and audio when config is available
  useEffect(() => {
    if (config?.initialQuestion) {
      setQuestion(config.initialQuestion);
    }
    if (config?.initialAudioUrl) {
      setAudioUrl(config.initialAudioUrl);
    }
  }, [config]);

  const handlePlayAudio = async () => {
    if (!audioUrl) {
      setError('Audio URL not available');
      return;
    }
    try {
      setIsPlayingAudio(true);
      // Construct full URL if audioUrl is relative
      const fullUrl = audioUrl.startsWith('http') ? audioUrl : `http://localhost:8000${audioUrl}`;
      const response = await axios.get(fullUrl, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      audioRef.current.src = url;
      audioRef.current.onended = () => setIsPlayingAudio(false);
      await audioRef.current.play();
    } catch (err) {
      setError(`Failed to play audio: ${err.message}`);
      setIsPlayingAudio(false);
    }
  };

  const handleSubmitResponse = async (audioBlob) => {
    setIsSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('audio_file', audioBlob, 'response.webm');

      const response = await axios.post(
        `http://localhost:8000/api/interview/${sessionId}/submit-response`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      if (response.data.status === 'completed') {
        setInterviewComplete(true);
        setReport(response.data.report);
      } else {
        setQuestion(response.data.question);
        setAudioUrl(response.data.audio_url);
        setCurrentTurn(response.data.current_turn);
      }
    } catch (err) {
      setError(`Failed to submit response: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEndInterview = async () => {
    try {
      await axios.post(`http://localhost:8000/api/interview/${sessionId}/end`);
      onEndSession();
    } catch (err) {
      setError(`Failed to end interview: ${err.message}`);
    }
  };

  if (interviewComplete) {
    return (
      <div className="interview-complete">
        <h2>Interview Complete</h2>
        <div className="report-section">
          <h3>Overall Assessment</h3>
          <p>{report.overall_signal}</p>

          <h3>Hire Signal</h3>
          <p className="hire-signal">{report.hire_signal}</p>

          <h3>Competency Scores</h3>
          <div className="competencies">
            {report.competencies &&
              report.competencies.map((comp, idx) => (
                <div key={idx} className="competency">
                  <h4>{comp.name}</h4>
                  <p>Score: {comp.score}/5</p>
                  <p>Evidence: {comp.evidence}</p>
                  <p>Gap: {comp.gap}</p>
                </div>
              ))}
          </div>

          <h3>Feedback</h3>
          <ul>
            {report.feedback &&
              report.feedback.map((tip, idx) => (
                <li key={idx}>{tip}</li>
              ))}
          </ul>
        </div>

        <button onClick={onEndSession} className="end-btn">
          Exit & Return to Setup
        </button>
      </div>
    );
  }

  return (
    <div className="interview-session">
      <div className="interview-layout">
        {/* Main Content */}
        <div className="interview-main">
          {/* Video Monitor */}
          <VideoMonitor sessionId={sessionId} />

          {/* Question & Audio */}
          <div className="question-section">
            <h2>Current Question</h2>
            <div className="question-text">{question}</div>
            <button
              className="play-audio-btn"
              onClick={handlePlayAudio}
              disabled={isPlayingAudio || !audioUrl}
            >
              {isPlayingAudio ? 'Playing...' : 'Play Question Audio'}
            </button>
          </div>

          {/* Audio Recording */}
          <div className="recording-section">
            <h3>Record Your Response</h3>
            <AudioRecorder
              onSubmit={handleSubmitResponse}
              disabled={isSubmitting || isPlayingAudio}
            />
          </div>

          {error && <div className="error-message">{error}</div>}
        </div>

        {/* Monitoring Dashboard */}
        <aside className="interview-sidebar">
          <MonitoringDashboard
            integrityScore={integrityScore}
            classification={classification}
            currentTurn={currentTurn}
          />
        </aside>
      </div>

      <div className="interview-controls">
        <p>Session ID: {sessionId}</p>
        <button onClick={handleEndInterview} className="end-interview-btn">
          End Interview
        </button>
      </div>
    </div>
  );
}

export default InterviewSession;
