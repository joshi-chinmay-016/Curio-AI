from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_structured(self, prompt: str, response_model: Type[BaseModel]) -> BaseModel:
        """
        Generate structured output from LLM using Pydantic validation.
        """
        pass

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """
        Generate basic text output from LLM.
        """
        pass
