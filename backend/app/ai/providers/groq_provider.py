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

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("GROQ_API_KEY")
            or getattr(settings, "GROQ_API_KEY", "")
        )
        self.model = (
            model
            or os.getenv("GROQ_MODEL")
            or getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        )
        self.timeout = (
            timeout
            if timeout is not None
            else float(os.getenv("GROQ_TIMEOUT_SECONDS") or getattr(settings, "GROQ_TIMEOUT_SECONDS", 30.0))
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else int(os.getenv("GROQ_MAX_RETRIES") or getattr(settings, "GROQ_MAX_RETRIES", 2))
        )
        self.max_tokens = int(
            os.getenv("GROQ_MAX_TOKENS")
            or getattr(settings, "GROQ_MAX_TOKENS", 900)
        )
        self.mock_fallback = MockLLMProvider()
        self.client = None

        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
                logger.info("GroqLLMProvider successfully initialized with client (model=%s, max_tokens=%d).", self.model, self.max_tokens)
            except ImportError:
                logger.warning("Groq package not installed; falling back to MockLLMProvider.")
            except Exception as e:
                logger.warning("Failed to initialize Groq client (%s); falling back to MockLLMProvider.", type(e).__name__)
        else:
            logger.info("No GROQ_API_KEY found; operating in mock fallback mode.")

    def _sanitize_error(self, e: Exception) -> str:
        """Sanitize error message to avoid leaking any credentials or tokens in logs."""
        msg = str(e)
        if self.api_key and self.api_key in msg:
            msg = msg.replace(self.api_key, "[REDACTED]")
        return msg

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
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                )
            except Exception as e_rf:
                # If json_object response_format failed (e.g. 400 Bad Request / json_validate_failed), retry without it
                if "json_validate_failed" in str(e_rf) or "BadRequestError" in type(e_rf).__name__:
                    logger.info("Retrying structured generation without response_format constraint...")
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.0,
                        max_tokens=self.max_tokens,
                        timeout=self.timeout,
                    )
                else:
                    raise e_rf

            raw_content = response.choices[0].message.content or "{}"
            cleaned_content = self._clean_json_text(raw_content)
            return response_model.model_validate_json(cleaned_content)
        except Exception as e:
            logger.warning(
                "Groq structured generation failed (%s: %s); falling back to mock.",
                type(e).__name__,
                self._sanitize_error(e),
            )
            return self.mock_fallback.generate_structured(prompt, response_model)

    def generate_text(self, prompt: str) -> str:
        if not self.client:
            return self.mock_fallback.generate_text(prompt)

        prompt_lower = prompt.lower()
        if "mode: teacher" in prompt_lower or "expert, empathetic, and concise teacher" in prompt_lower:
            system_prompt = (
                "You are Curio acting as an expert, empathetic, and concise Teacher. "
                "Teach ONLY the identified knowledge gap, keep it concise, and end with exactly ONE verification question testing the gap."
            )
        else:
            system_prompt = (
                "You are Curio, an inquisitive student learning from the user. "
                "Output exactly ONE primary learning question. Do not lecture."
            )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=min(self.max_tokens, 600),
                timeout=self.timeout,
            )
            content = response.choices[0].message.content or ""
            return content.strip()
        except Exception as e:
            logger.warning(
                "Groq text generation failed (%s: %s); falling back to mock.",
                type(e).__name__,
                self._sanitize_error(e),
            )
            return self.mock_fallback.generate_text(prompt)

    @staticmethod
    def _clean_json_text(raw: str) -> str:
        """Strip markdown fences if model outputs ```json ... ``` or wraps JSON in text."""
        text = raw.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # If text contains extra conversational wrapper, extract the outermost JSON object
        if not (text.startswith("{") and text.endswith("}")):
            match = re.search(r"(\{.*\})", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        return text
