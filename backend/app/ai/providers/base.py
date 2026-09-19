from abc import ABC, abstractmethod
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseAIProvider(ABC):
    """
    Minimal AI provider abstraction.
    Decouples Curio AI logic from specific LLM providers (Groq, Gemini, OpenAI, Mock).
    """

    @abstractmethod
    def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
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


# Backward compatibility alias for existing code
BaseLLMProvider = BaseAIProvider
