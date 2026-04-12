"""
SENTINEL — Semantic Drift Agent (SDA)

Monitors semantic coherence across turns using sentence embeddings.
Detects mid-session shifts in content source (e.g. switching from
genuine answers to pasted content).
"""

from dataclasses import dataclass

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
except ImportError:
    SentenceTransformer = None
    sk_cosine = None

from sentinel.agents.eca import ECAResult
from sentinel.config import SDA_COSINE_THRESHOLDS


@dataclass
class SDAResult:
    """Output of the Semantic Drift Agent."""
    signal: str
    cosine_to_session_mean: float
    q_to_a_cosine: float
    trajectory_delta: float
    note: str


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    a = a.flatten()
    b = b.flatten()
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-9:
        return 0.0
    return float(np.dot(a, b) / denom)


class SemanticDriftAgent:
    """
    Tracks embedding trajectory across interview turns.
    Flags semantic divergence and suspiciously high question-answer similarity.
    """

    def __init__(self):
        self.embeddings: list[np.ndarray] = []
        self._model = None
        self._model_loaded = False

    def _load_model(self):
        """Lazy-load the sentence transformer model."""
        if self._model_loaded:
            return
        try:
            if SentenceTransformer is not None:
                self._model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
            self._model_loaded = True
        except Exception:
            self._model = None
            self._model_loaded = True

    def _embed(self, text: str) -> np.ndarray:
        """Embed text using the sentence transformer model."""
        self._load_model()
        if self._model is None:
            return np.zeros(384)
        try:
            return self._model.encode(text, convert_to_numpy=True)
        except Exception:
            return np.zeros(384)

    def analyse(self, question: str, response: str, eca_result: ECAResult) -> SDAResult:
        """
        Analyse semantic drift for a single turn.

        Args:
            question: The interview question.
            response: The candidate's response.
            eca_result: Calibration from ECA.

        Returns:
            SDAResult with signal and analysis.
        """
        try:
            if not response or len(response.split()) < 5:
                return SDAResult(
                    signal="GREEN",
                    cosine_to_session_mean=0.0,
                    q_to_a_cosine=0.0,
                    trajectory_delta=0.0,
                    note="Response too short for semantic analysis.",
                )

            response_emb = self._embed(response)
            question_emb = self._embed(question)

            multiplier = eca_result.threshold_multiplier
            signals = []

            # 1. Cosine to session mean
            cosine_to_session_mean = 0.0
            if len(self.embeddings) >= 2:
                session_mean = np.mean(self.embeddings, axis=0)
                cosine_to_session_mean = _cosine_sim(response_emb, session_mean)

                # Apply adjusted thresholds
                red_thresh = SDA_COSINE_THRESHOLDS["RED"] * multiplier
                amber_thresh = SDA_COSINE_THRESHOLDS["AMBER"] * multiplier

                if cosine_to_session_mean < red_thresh:
                    signals.append("RED")
                elif cosine_to_session_mean < amber_thresh:
                    signals.append("AMBER")
                else:
                    signals.append("GREEN")
            else:
                signals.append("GREEN")

            # 2. Question-to-answer cosine (pasted definition detection)
            q_to_a_cosine = _cosine_sim(question_emb, response_emb)
            if q_to_a_cosine > 0.92:
                signals.append("AMBER")

            # 3. Trajectory delta (first third vs last third coherence)
            trajectory_delta = 0.0
            all_embs = self.embeddings + [response_emb]
            if len(all_embs) >= 6:
                n = len(all_embs)
                third = n // 3
                first_third = all_embs[:third]
                last_third = all_embs[-third:]

                # Mean pairwise coherence within each third
                first_mean_sim = self._mean_pairwise_sim(first_third)
                last_mean_sim = self._mean_pairwise_sim(last_third)
                trajectory_delta = last_mean_sim - first_mean_sim

                if trajectory_delta > 0.30:
                    signals.append("RED")
                elif trajectory_delta > 0.15:
                    signals.append("AMBER")

            # Final signal = worst
            signal_priority = {"RED": 2, "AMBER": 1, "GREEN": 0}
            signal = max(signals, key=lambda s: signal_priority.get(s, 0))

            # Build note
            if len(self.embeddings) < 2:
                note = "Insufficient history for drift analysis."
            elif signal == "GREEN":
                note = f"Semantic coherence normal. Session cosine: {cosine_to_session_mean:.3f}."
            else:
                parts = []
                if cosine_to_session_mean < SDA_COSINE_THRESHOLDS["AMBER"] * multiplier:
                    parts.append(f"session cosine low ({cosine_to_session_mean:.3f})")
                if q_to_a_cosine > 0.92:
                    parts.append(f"Q-A cosine high ({q_to_a_cosine:.3f})")
                if trajectory_delta > 0.15:
                    parts.append(f"trajectory shift ({trajectory_delta:.3f})")
                note = "Semantic anomaly: " + ", ".join(parts) + "."

            # Append embedding to history
            self.embeddings.append(response_emb)

            return SDAResult(
                signal=signal,
                cosine_to_session_mean=round(cosine_to_session_mean, 4),
                q_to_a_cosine=round(q_to_a_cosine, 4),
                trajectory_delta=round(trajectory_delta, 4),
                note=note,
            )

        except Exception as e:
            self.embeddings.append(np.zeros(384))
            return SDAResult(
                signal="GREEN",
                cosine_to_session_mean=0.0,
                q_to_a_cosine=0.0,
                trajectory_delta=0.0,
                note=f"parse error — insufficient signal. ({str(e)})",
            )

    @staticmethod
    def _mean_pairwise_sim(embeddings: list[np.ndarray]) -> float:
        """Compute mean pairwise cosine similarity within a list of embeddings."""
        if len(embeddings) < 2:
            return 0.0
        sims = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sims.append(_cosine_sim(embeddings[i], embeddings[j]))
        return float(np.mean(sims)) if sims else 0.0
