"""
Gemini Embedding Provider for Curio AI.

Provides deterministic, batched embedding generation using Google's Gemini API
(e.g., gemini-embedding-001, text-embedding-004, gemini-embedding-2).
Supports configurable dimensions (default: 1536) to match the pgvector schema.
"""
from dataclasses import dataclass
import hashlib
import json
import logging
import math
import random
import time
from typing import List, Optional

import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embeddings: List[List[float]]  # One vector per input text
    model: str
    dimensions: int
    total_tokens: int


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    def __init__(self, message: str, details: str = None, retryable: bool = False):
        self.message = message
        self.details = details
        self.retryable = retryable
        super().__init__(message)


def _generate_deterministic_mock_embedding(text: str, dimensions: int = 1536) -> List[float]:
    """
    Generates a deterministic, normalized vector of specified dimensions
    derived from text content. Used when running offline, in CI, or without API keys.
    """
    if not text or not text.strip():
        return []

    # Seed random with text hash
    h = hashlib.sha256(text.strip().encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "big")
    rng = random.Random(seed)

    raw_vec = [rng.gauss(0.0, 1.0) for _ in range(dimensions)]
    # Add token-frequency signal to initial dimensions
    tokens = text.lower().split()
    for idx, token in enumerate(tokens[:min(32, dimensions)]):
        tok_hash = int.from_bytes(hashlib.md5(token.encode("utf-8")).digest()[:4], "big") % dimensions
        raw_vec[tok_hash] += 0.5

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in raw_vec))
    if norm > 0:
        return [round(x / norm, 6) for x in raw_vec]
    return [0.0] * dimensions


class GeminiEmbeddingProvider:
    """
    Google Gemini Embedding Provider.
    
    Calls Google's generativelanguage v1beta API using httpx with:
    - Bounded batch sizes
    - Output dimensionality control (e.g. 1536)
    - Rate limit retry with exponential backoff & jitter
    - Deterministic fallback for offline testing
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        batch_size: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY or settings.EMBEDDING_API_KEY
        raw_model = model or settings.GEMINI_EMBEDDING_MODEL or settings.EMBEDDING_MODEL
        # Normalize model name for Google API: strip 'models/' prefix if present
        if raw_model.startswith("models/"):
            raw_model = raw_model[len("models/"):]
        self.model = raw_model
        self.dimensions = dimensions or settings.EMBEDDING_DIMENSIONS or 1536
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE or 50
        self.timeout = timeout or settings.EMBEDDING_TIMEOUT_SECONDS or 30.0
        self.max_retries = max_retries if max_retries is not None else settings.EMBEDDING_MAX_RETRIES

        self._is_mock = (
            not self.api_key
            or "mock" in self.api_key.lower()
            or "test" in self.api_key.lower()
            or self.api_key == "curio-dev-mock-key"
        )
        if self._is_mock:
            logger.info("GeminiEmbeddingProvider: Using deterministic offline mock provider (no live key provided).")

    def generate_embeddings(self, texts: List[str]) -> EmbeddingResult:
        """
        Generate embeddings for a list of texts using Gemini API.
        Empty texts receive an empty vector list ([]).
        """
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                model=self.model,
                dimensions=self.dimensions,
                total_tokens=0,
            )

        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text.strip())
                valid_indices.append(i)

        if not valid_texts:
            return EmbeddingResult(
                embeddings=[[] for _ in texts],
                model=self.model,
                dimensions=self.dimensions,
                total_tokens=0,
            )

        if self._is_mock:
            all_embeddings = [_generate_deterministic_mock_embedding(t, self.dimensions) for t in valid_texts]
            estimated_tokens = sum(len(t.split()) for t in valid_texts)
        else:
            all_embeddings = []
            estimated_tokens = 0
            for i in range(0, len(valid_texts), self.batch_size):
                batch = valid_texts[i : i + self.batch_size]
                batch_res = self._embed_batch_remote(batch)
                all_embeddings.extend(batch_res)
                estimated_tokens += sum(len(t.split()) for t in batch)

        # Map back to original indices
        result_embeddings = []
        valid_idx = 0
        valid_indices_set = set(valid_indices)
        for i in range(len(texts)):
            if i in valid_indices_set:
                result_embeddings.append(all_embeddings[valid_idx])
                valid_idx += 1
            else:
                result_embeddings.append([])

        return EmbeddingResult(
            embeddings=result_embeddings,
            model=self.model,
            dimensions=self.dimensions,
            total_tokens=estimated_tokens,
        )

    def _embed_batch_remote(self, batch_texts: List[str]) -> List[List[float]]:
        """
        Performs a batched HTTP request to Google's batchEmbedContents endpoint.
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents?key={self.api_key}"
        
        requests_payload = []
        for text in batch_texts:
            item = {
                "model": f"models/{self.model}",
                "content": {
                    "parts": [{"text": text}]
                },
            }
            if self.dimensions:
                item["outputDimensionality"] = self.dimensions
            requests_payload.append(item)

        body = {"requests": requests_payload}
        headers = {"Content-Type": "application/json"}

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, headers=headers, json=body)

                if resp.status_code == 200:
                    data = resp.json()
                    raw_embeddings = data.get("embeddings", [])
                    result_vectors = []
                    for idx, emb_obj in enumerate(raw_embeddings):
                        values = emb_obj.get("values", [])
                        if len(values) != self.dimensions:
                            # If dimension mismatch, pad or truncate cleanly
                            if len(values) > self.dimensions:
                                values = values[:self.dimensions]
                            elif len(values) < self.dimensions:
                                values = values + [0.0] * (self.dimensions - len(values))
                        result_vectors.append(values)
                    return result_vectors

                elif resp.status_code in (429, 503):
                    # Rate limit or temporary service unavailability
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
                    if attempt < self.max_retries:
                        jitter = random.uniform(0.1, 0.5)
                        backoff = (2 ** attempt) + jitter
                        logger.warning(
                            "Gemini rate limit (%d), retrying in %.2fs (attempt %d/%d)",
                            resp.status_code, backoff, attempt + 1, self.max_retries
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        raise EmbeddingError("Gemini rate limit exceeded after retries", details=last_error, retryable=True)

                else:
                    logger.error("Gemini API error (HTTP %d): %s", resp.status_code, resp.text)
                    raise EmbeddingError(f"Gemini API returned HTTP {resp.status_code}", details=resp.text, retryable=False)

            except httpx.RequestError as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    backoff = (2 ** attempt) * 1.0
                    logger.warning("Gemini network error, retrying in %.2fs: %s", backoff, exc)
                    time.sleep(backoff)
                    continue
                else:
                    raise EmbeddingError("Gemini network request failed after retries", details=str(exc), retryable=True)

        raise EmbeddingError("Failed to generate Gemini embeddings", details=str(last_error))
