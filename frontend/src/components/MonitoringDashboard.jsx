import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './MonitoringDashboard.css';

function MonitoringDashboard({ integrityScore, classification, currentTurn }) {
  const getClassificationColor = (classification) => {
    switch (classification) {
      case 'CLEAN':
        return '#22c55e';
      case 'WATCH':
        return '#eab308';
      case 'FLAG':
        return '#f97316';
      case 'ESCALATE':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  // Sample data for score timeline
  const scoreHistory = Array.from({ length: currentTurn + 1 }, (_, i) => ({
    turn: i,
    score: Math.round(integrityScore * (1 - Math.random() * 0.2)),
  }));

  return (
    <div className="monitoring-dashboard">
      <h2>Integrity Monitoring</h2>

      {/* Integrity Score Gauge */}
      <div className="score-section">
        <div className="score-gauge">
          <div
            className="score-fill"
            style={{
              width: `${integrityScore}%`,
              backgroundColor: getClassificationColor(classification),
            }}
          ></div>
          <span className="score-text">{Math.round(integrityScore)}</span>
        </div>
        <p className="score-label">Integrity Score</p>
      </div>

      {/* Classification */}
      <div className="classification-section">
        <h3>Classification</h3>
        <div
          className={`classification-badge classification-${classification.toLowerCase()}`}
          style={{ backgroundColor: getClassificationColor(classification) }}
        >
          {classification}
        </div>
        <p className="classification-description">
          {classification === 'CLEAN' && 'No integrity concerns detected'}
          {classification === 'WATCH' && 'Minor anomalies detected - monitoring closely'}
          {classification === 'FLAG' && 'Significant concerns detected'}
          {classification === 'ESCALATE' && 'Critical integrity issues detected'}
        </p>
      </div>

      {/* Score Timeline */}
      <div className="timeline-section">
        <h3>Score Timeline</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={scoreHistory}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="turn" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="score"
              stroke={getClassificationColor(classification)}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Monitoring Indicators */}
      <div className="indicators-section">
        <h3>Active Monitoring</h3>
        <div className="indicator-item">
          <span className="indicator-name">Video Feed</span>
          <span className="status-badge active">Active</span>
        </div>
        <div className="indicator-item">
          <span className="indicator-name">Audio Stream</span>
          <span className="status-badge active">Active</span>
        </div>
        <div className="indicator-item">
          <span className="indicator-name">Eye Tracking</span>
          <span className="status-badge active">Active</span>
        </div>
        <div className="indicator-item">
          <span className="indicator-name">Lip Sync Check</span>
          <span className="status-badge active">Active</span>
        </div>
        <div className="indicator-item">
          <span className="indicator-name">Object Detection</span>
          <span className="status-badge active">Active</span>
        </div>
      </div>

      <div className="info-box">
        <p>
          <strong>Note:</strong> Integrity scores are calculated in real-time based on
          multimodal signals from SENTINEL, including audio/visual analysis, voice
          verification, and behavioral anomalies.
        </p>
      </div>
    </div>
  );
}

export default MonitoringDashboard;
