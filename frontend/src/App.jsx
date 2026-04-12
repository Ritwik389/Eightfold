import React, { useState } from 'react';
import ConfigPanel from './components/ConfigPanel';
import InterviewSession from './components/InterviewSession';
import './App.css';

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [config, setConfig] = useState(null);

  const handleStartInterview = (configData) => {
    setConfig(configData);
    // sessionId will be set after API call in ConfigPanel
  };

  const handleSessionStarted = (id) => {
    setSessionId(id);
  };

  const handleEndSession = () => {
    setSessionId(null);
    setConfig(null);
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>HireMind: AI Technical Interviewer</h1>
        <p>Real-time multimodal integrity assessment with voice interaction</p>
      </header>

      <main className="app-main">
        {!sessionId ? (
          <ConfigPanel onStartInterview={handleStartInterview} onSessionStarted={handleSessionStarted} />
        ) : (
          <InterviewSession
            sessionId={sessionId}
            config={config}
            onEndSession={handleEndSession}
          />
        )}
      </main>

      <footer className="app-footer">
        <p>SENTINEL Multimodal Integrity Monitoring System</p>
      </footer>
    </div>
  );
}

export default App;
