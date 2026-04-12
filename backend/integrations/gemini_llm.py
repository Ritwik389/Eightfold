"""
Google Gemini LLM Integration
Handles question generation, response evaluation, and report generation
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class GeminiLLM:
    """LLM wrapper using Google Gemini API"""

    def __init__(self):
        """Initialize Gemini LLM client"""
        if not genai:
            self.enabled = False
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.enabled = False
            return

        genai.configure(api_key=api_key)
        self.client = genai
        self.enabled = True
        self.model = os.getenv("GEMINI_LLM_MODEL", "gemini-2.0-flash")

    async def generate_question(
        self,
        competencies: str,
        current_turn: int = 0,
        previous_responses: Optional[list] = None,
    ) -> str:
        """
        Generate an interview question

        Args:
            competencies: Comma-separated competencies to assess
            current_turn: Question number (0 = greeting)
            previous_responses: List of previous candidate responses

        Returns:
            Generated question string
        """
        if not self.enabled:
            return "Tell me about your experience with system design."

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._generate_question_sync,
            competencies,
            current_turn,
            previous_responses,
        )

    def _generate_question_sync(
        self, competencies: str, current_turn: int, previous_responses: Optional[list]
    ) -> str:
        """Generate question synchronously"""
        try:
            if current_turn == 0:
                prompt = f"""Generate a warm, welcoming opening question for a technical interview.
The candidate will be assessed on: {competencies}

Requirements:
- Make it open-ended and engaging
- Encourage the candidate to share real experiences
- Not too long (1-2 sentences)
- Professional but friendly tone

Return ONLY the question, no additional text."""
            else:
                prev_context = ""
                if previous_responses:
                    prev_context = f"\n\nPrevious responses:\n"
                    for i, resp in enumerate(previous_responses[-2:], 1):
                        prev_context += f"Q{current_turn - len(previous_responses) + i}: {resp[:200]}...\n"

                prompt = f"""Generate the next interview question to assess: {competencies}

Current turn: {current_turn}{prev_context}

Requirements:
- Build on previous responses or explore a new competency
- Go deeper than the previous question
- Encourage specific examples and technical details
- Open-ended format
- 1-2 sentences

Return ONLY the question, no additional text."""

            model = self.client.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            print(f"Gemini LLM error: {e}")
            return (
                "Tell me about a challenging technical problem you"
                " recently solved and how you approached it."
            )

    async def evaluate_response(
        self,
        question: str,
        response: str,
        competency: str,
    ) -> Dict[str, Any]:
        """
        Evaluate candidate response depth and quality

        Args:
            question: The question asked
            response: Candidate's response
            competency: Competency being assessed

        Returns:
            Dict with depth, score, and routing
        """
        if not self.enabled:
            return {
                "depth": "PARTIAL",
                "score": 3.0,
                "routing": "advance",
                "feedback": "Response noted.",
            }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._evaluate_response_sync, question, response, competency
        )

    def _evaluate_response_sync(
        self, question: str, response: str, competency: str
    ) -> Dict[str, Any]:
        """Evaluate response synchronously"""
        try:
            prompt = f"""Evaluate this technical interview response:

Question: {question}
Competency: {competency}
Response: {response}

Score the response on:
1. Depth (SURFACE/PARTIAL/DEEP) - how thorough and detailed
2. Score (1.0-5.0) - overall technical quality
3. Routing (advance/follow_up/probe) - next action
4. Feedback (1 sentence) - key observation

Return ONLY valid JSON:
{{
  "depth": "PARTIAL",
  "score": 3.5,
  "routing": "advance",
  "feedback": "Good understanding shown..."
}}"""

            model = self.client.GenerativeModel(self.model)
            response = model.generate_content(prompt)

            try:
                # Extract JSON from response
                result = json.loads(response.text)
                # Validate structure
                result["depth"] = result.get("depth", "PARTIAL")
                result["score"] = float(result.get("score", 3.0))
                result["routing"] = result.get("routing", "advance")
                result["feedback"] = result.get("feedback", "Response noted.")
                return result
            except (json.JSONDecodeError, KeyError):
                return {
                    "depth": "PARTIAL",
                    "score": 3.0,
                    "routing": "advance",
                    "feedback": "Response evaluated.",
                }

        except Exception as e:
            print(f"Gemini evaluation error: {e}")
            return {
                "depth": "PARTIAL",
                "score": 3.0,
                "routing": "advance",
                "feedback": "Response noted.",
            }

    async def generate_report(
        self,
        candidate_name: str,
        competencies: str,
        responses: list,
        evaluations: list,
        integrity_analysis: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Generate final interview report

        Args:
            candidate_name: Candidate's name
            competencies: Assessed competencies
            responses: List of candidate responses
            evaluations: List of evaluation results
            integrity_analysis: SENTINEL monitoring results

        Returns:
            Report dict with scores, hire decision, feedback
        """
        if not self.enabled:
            return {
                "overall_signal": "MAYBE",
                "hire_score": 3.0,
                "feedback": "Interview completed. Additional review recommended.",
                "competency_scores": {},
            }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._generate_report_sync,
            candidate_name,
            competencies,
            responses,
            evaluations,
            integrity_analysis,
        )

    def _generate_report_sync(
        self,
        candidate_name: str,
        competencies: str,
        responses: list,
        evaluations: list,
        integrity_analysis: Optional[Dict],
    ) -> Dict[str, Any]:
        """Generate report synchronously"""
        try:
            responses_summary = "\n".join([f"Q{i+1}: {r[:200]}" for i, r in enumerate(responses)])
            eval_summary = json.dumps(
                [e for e in evaluations], indent=2, default=str
            )

            prompt = f"""Generate a hiring recommendation for: {candidate_name}

Competencies Assessed: {competencies}

Responses Summary:
{responses_summary}

Evaluations:
{eval_summary}

Integrity Signals:
{json.dumps(integrity_analysis or {}, indent=2)}

Provide:
1. overall_signal: STRONG_YES / YES / MAYBE / NO / STRONG_NO
2. hire_score: 1.0-5.0 (5.0 = hire immediately)
3. feedback: 2-3 sentences about competency fit
4. competency_scores: JSON dict with score per competency

Return ONLY valid JSON:
{{
  "overall_signal": "YES",
  "hire_score": 4.0,
  "feedback": "Strong technical fundamentals...",
  "competency_scores": {{"System Design": 4.0, "APIs": 3.5}}
}}"""

            model = self.client.GenerativeModel(self.model)
            response = model.generate_content(prompt)

            try:
                result = json.loads(response.text)
                return {
                    "overall_signal": result.get("overall_signal", "MAYBE"),
                    "hire_score": float(result.get("hire_score", 3.0)),
                    "feedback": result.get("feedback", "Interview completed."),
                    "competency_scores": result.get("competency_scores", {}),
                }
            except (json.JSONDecodeError, KeyError):
                return {
                    "overall_signal": "MAYBE",
                    "hire_score": 3.0,
                    "feedback": "Interview completed. Manual review recommended.",
                    "competency_scores": {},
                }

        except Exception as e:
            print(f"Gemini report error: {e}")
            return {
                "overall_signal": "MAYBE",
                "hire_score": 3.0,
                "feedback": "Report generation completed.",
                "competency_scores": {},
            }

    def set_model(self, model: str):
        """Set LLM model"""
        self.model = model

    async def stream_response(self, prompt: str):
        """
        Stream LLM response in real-time (yields text chunks)

        Args:
            prompt: The prompt to send

        Yields:
            Response text chunks
        """
        try:
            model = self.client.GenerativeModel(self.model)
            response = model.generate_content(prompt, stream=True)

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            print(f"Gemini stream error: {e}")
            yield "Response generation failed."
