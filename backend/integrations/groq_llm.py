"""
Groq LLM Integration

Uses Groq's API for fast inference with LLaMA models.
Generates interview questions and final reports.
"""

import os
import json
import logging
from typing import Optional

from groq import Groq

logger = logging.getLogger("groq_llm")


class GroqLLM:
    """Interview question generation and evaluation using Groq."""
    
    def __init__(self):
        api_key = os.getenv("GROQ_API")
        if not api_key:
            raise ValueError("GROQ_API not set in environment")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
    
    async def generate_question(
        self,
        phase: str,
        competencies: str,
        system_prompt: str,
        previous_response: Optional[str] = None
    ) -> str:
        """
        Generate the next interview question.
        
        Args:
            phase: "greeting" or "follow-up"
            competencies: Comma-separated list of competencies
            system_prompt: System context for the interviewer
            previous_response: Previous candidate response (for follow-ups)
        
        Returns:
            Question text
        """
        try:
            if phase == "greeting":
                user_prompt = "Generate a professional opening question for the first competency. Only output the question, nothing else."
            else:
                user_prompt = f"""The candidate said: "{previous_response}"

Generate a follow-up question or advance to the next competency. 
Only output the question, nothing else."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=200,
            )
            
            question = response.choices[0].message.content.strip()
            logger.info(f"Generated question: {question[:80]}...")
            
            return question
        
        except Exception as e:
            logger.error(f"Groq question generation error: {e}")
            raise
    
    async def evaluate_response(
        self,
        question: str,
        response: str,
        system_prompt: str
    ) -> dict:
        """
        Internally evaluate response depth.
        
        Returns:
            {
                "depth": "SURFACE|PARTIAL|DEEP",
                "score": 1-5,
                "reasoning": "...",
                "action": "advance|follow-up|probe"
            }
        """
        try:
            eval_prompt = f"""Question: {question}
Candidate Response: {response}

Classify the response as SURFACE (vocabulary only), PARTIAL (foundational but missing nuance), or DEEP (mechanism/tradeoffs/examples).
Score 1-5.
Then decide: ADVANCE to next competency, ask a FOLLOW-UP on the gap, or use SOCRATIC probe.

Respond in JSON format:
{{"depth": "SURFACE|PARTIAL|DEEP", "score": 1-5, "reasoning": "brief reason", "action": "advance|follow-up|probe"}}"""
            
            response_text = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": eval_prompt}
                ],
                temperature=0.3,
                max_tokens=300,
            ).choices[0].message.content
            
            # Parse JSON response
            try:
                result = json.loads(response_text)
            except:
                # Fallback if not valid JSON
                result = {
                    "depth": "PARTIAL",
                    "score": 3,
                    "reasoning": response_text[:100],
                    "action": "follow-up"
                }
            
            return result
        
        except Exception as e:
            logger.error(f"Groq evaluation error: {e}")
            return {"depth": "PARTIAL", "score": 3, "reasoning": "Error", "action": "follow-up"}
    
    async def generate_report(
        self,
        transcript: list,
        candidate_name: str,
        experience_tier: str
    ) -> dict:
        """
        Generate comprehensive interview report.
        
        Returns:
            {
                "candidate": "...",
                "role": "...",
                "date": "...",
                "overall_signal": "...",
                "competencies": [...],
                "hire_signal": "...",
                "feedback": [...]
            }
        """
        try:
            # Format transcript for context
            transcript_text = "\n".join([
                f"{turn['role'].upper()}: {turn['text']}" 
                for turn in transcript
            ])
            
            report_prompt = f"""Interview Transcript:
{transcript_text}

Generate a comprehensive technical interview report for {candidate_name} ({experience_tier}):
1. Overall Signal (2-3 sentences)
2. Competency Scores (for each: score 1-5, evidence, gaps)
3. Hire Signal (Strong Yes/Yes/Lean Yes/Lean No/No)
4. Feedback (3 actionable tips)

Respond in JSON format:
{{
"overall_signal": "...",
"competencies": [{{"name": "...", "score": 1-5, "evidence": "...", "gap": "..."}}],
"hire_signal": "...",
"feedback": [...]
}}"""
            
            response_text = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert technical interviewer creating comprehensive reports."},
                    {"role": "user", "content": report_prompt}
                ],
                temperature=0.4,
                max_tokens=1500,
            ).choices[0].message.content
            
            try:
                report = json.loads(response_text)
            except:
                report = {
                    "overall_signal": response_text[:200],
                    "competencies": [],
                    "hire_signal": "Neutral",
                    "feedback": ["See detailed notes above"]
                }
            
            report["candidate"] = candidate_name
            report["experience_tier"] = experience_tier
            
            return report
        
        except Exception as e:
            logger.error(f"Groq report generation error: {e}")
            return {
                "candidate": candidate_name,
                "error": str(e),
                "overall_signal": "Report generation failed"
            }
