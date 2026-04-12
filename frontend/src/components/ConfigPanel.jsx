import React, { useState } from 'react';
import axios from 'axios';

const PRESET_ROLES = {
  'Software Engineer': {
    jd: 'Backend systems engineer responsible for REST APIs, database optimization, and microservices architecture.',
    competencies: 'System Design, API Design, Database Modeling, Debugging, Problem Solving'
  },
  'ML Engineer': {
    jd: 'Machine Learning engineer focused on model training, deployment pipelines, and production ML systems.',
    competencies: 'Model Architecture, MLOps, Model Deployment, Debugging, Communication'
  },
  'Product Manager': {
    jd: 'Product Manager responsible for roadmap definition, stakeholder alignment, and product strategy.',
    competencies: 'Product Strategy, Technical Acumen, Data Analysis, Communication, Leadership'
  }
};

function ConfigPanel({ onStartInterview, onSessionStarted }) {
  const [candidateName, setCandidateName] = useState('');
  const [experienceTier, setExperienceTier] = useState('Mid-level');
  const [selectedPreset, setSelectedPreset] = useState('Software Engineer');
  const [jd, setJd] = useState(PRESET_ROLES['Software Engineer'].jd);
  const [competencies, setCompetencies] = useState(PRESET_ROLES['Software Engineer'].competencies);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePresetChange = (preset) => {
    setSelectedPreset(preset);
    setJd(PRESET_ROLES[preset].jd);
    setCompetencies(PRESET_ROLES[preset].competencies);
  };

  const handleStartInterview = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (!candidateName.trim()) {
      setError('Please enter candidate name');
      setLoading(false);
      return;
    }

    try {
      const response = await axios.post('http://localhost:8000/api/interview/start', {
        candidate_name: candidateName,
        experience_tier: experienceTier,
        jd: jd,
        competencies: competencies
      });

      const { session_id, question, audio_url, current_turn } = response.data;
      onSessionStarted(session_id);
      onStartInterview({
        sessionId: session_id,
        candidateName,
        experienceTier,
        jd,
        competencies,
        initialQuestion: question,
        initialAudioUrl: audio_url,
        currentTurn: current_turn
      });
    } catch (err) {
      setError(`Failed to start interview: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="config-panel">
      <div className="config-container">
        <section className="config-section">
          <h2>Interview Configuration</h2>

          <div className="form-group">
            <label>Candidate Name</label>
            <input
              type="text"
              value={candidateName}
              onChange={(e) => setCandidateName(e.target.value)}
              placeholder="e.g., Alice Smith"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label>Experience Level</label>
            <select value={experienceTier} onChange={(e) => setExperienceTier(e.target.value)} disabled={loading}>
              <option>Fresher</option>
              <option>Junior</option>
              <option>Mid-level</option>
              <option>Senior</option>
              <option>Principal/Staff</option>
            </select>
          </div>

          <div className="form-group">
            <label>Role Preset</label>
            <div className="preset-buttons">
              {Object.keys(PRESET_ROLES).map((role) => (
                <button
                  key={role}
                  className={`preset-btn ${selectedPreset === role ? 'active' : ''}`}
                  onClick={() => handlePresetChange(role)}
                  disabled={loading}
                >
                  {role}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Job Description</label>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              rows="4"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label>Competencies (comma-separated)</label>
            <input
              type="text"
              value={competencies}
              onChange={(e) => setCompetencies(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button
            className="start-btn"
            onClick={handleStartInterview}
            disabled={loading}
          >
            {loading ? 'Starting Interview...' : 'Start Interview'}
          </button>
        </section>

        <section className="info-section">
          <h3>Interview Process</h3>
          <ol>
            <li>Click "Start Interview" to begin</li>
            <li>Allow camera and microphone access</li>
            <li>Listen to the question being asked</li>
            <li>Record or stream your audio response</li>
            <li>System transcribes and analyzes your response</li>
            <li>Next question appears with audio playback</li>
            <li>Interview concludes with comprehensive report</li>
          </ol>

          <h3>What We Monitor</h3>
          <ul>
            <li>Eye gaze tracking (sustained off-screen staring)</li>
            <li>Lip aperture correlation with audio (lip-sync mismatch)</li>
            <li>Secondary objects/persons detected</li>
            <li>Voice signature consistency</li>
            <li>Audio quality and VAD anomalies</li>
          </ul>
        </section>
      </div>
    </div>
  );
}

export default ConfigPanel;
