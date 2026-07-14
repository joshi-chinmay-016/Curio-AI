import os
from typing import Type
from pydantic import BaseModel
from backend.app.ai.providers.base import BaseLLMProvider
from backend.app.ai.providers.mock_provider import MockLLMProvider

class GroqLLMProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.mock_fallback = MockLLMProvider()
        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except ImportError:
                self.client = None
        else:
            self.client = None

    def generate_structured(self, prompt: str, response_model: Type[BaseModel]) -> BaseModel:
        if not self.client:
            return self.mock_fallback.generate_structured(prompt, response_model)

        try:
            # Pydantic v2 structured outputs are supported via groq tool calls or JSON mode.
            # In this scaffold stub, we will run the standard completion with json schema guidance.
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": f"You are a structured parser. Output only valid JSON matching this schema: {response_model.model_json_schema()}"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            raw_content = response.choices[0].message.content
            return response_model.model_validate_json(raw_content)
        except Exception as e:
            # Fall back to mock response in case of any provider errors
            return self.mock_fallback.generate_structured(prompt, response_model)

    def generate_text(self, prompt: str) -> str:
        if not self.client:
            return self.mock_fallback.generate_text(prompt)

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception:
            return self.mock_fallback.generate_text(prompt)
