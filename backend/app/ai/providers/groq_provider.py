"""
Groq LLM Provider implementation for Curio AI.
Provides real LLM inference using the official Groq SDK with graceful mock fallback.
"""
import json
import logging
import os
import re
from typing import Optional, Type
from pydantic import BaseModel

from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.providers.mock_provider import MockLLMProvider
from backend.app.core.config import settings

logger = logging.getLogger("curio.ai.providers.groq")


class GroqLLMProvider(BaseLLMProvider):
    """
    Production LLM provider using Groq's high-speed inference API.
    Supports structured Pydantic outputs and open-ended text generation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", "")
        self.mock_fallback = MockLLMProvider()
        self.client = None

        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
                logger.info("GroqLLMProvider successfully initialized with client.")
            except ImportError:
                logger.warning("Groq package not installed; falling back to MockLLMProvider.")
            except Exception as e:
                logger.warning("Failed to initialize Groq client (%s); falling back to MockLLMProvider.", type(e).__name__)
        else:
            logger.info("No GROQ_API_KEY found; operating in mock fallback mode.")

    def generate_structured(self, prompt: str, response_model: Type[BaseModel]) -> BaseModel:
        if not self.client:
            return self.mock_fallback.generate_structured(prompt, response_model)

        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        system_prompt = (
            "You are a pedagogical AI system that strictly outputs valid JSON.\n"
            f"You MUST conform to the following JSON schema:\n{schema_json}\n"
            "Output ONLY the JSON object. Do not include markdown code block formatting or explanations."
        )

        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw_content = response.choices[0].message.content or "{}"
            cleaned_content = self._clean_json_text(raw_content)
            return response_model.model_validate_json(cleaned_content)
        except Exception as e:
            logger.warning("Groq structured generation failed (%s: %s); falling back to mock.", type(e).__name__, str(e))
            return self.mock_fallback.generate_structured(prompt, response_model)

    def generate_text(self, prompt: str) -> str:
        if not self.client:
            return self.mock_fallback.generate_text(prompt)

        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are Curio, an inquisitive student learning from the user. Output exactly ONE primary learning question. Do not lecture."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content or ""
            return content.strip()
        except Exception as e:
            logger.warning("Groq text generation failed (%s: %s); falling back to mock.", type(e).__name__, str(e))
            return self.mock_fallback.generate_text(prompt)

    @staticmethod
    def _clean_json_text(raw: str) -> str:
        """Strip markdown fences if model outputs ```json ... ```."""
        text = raw.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
