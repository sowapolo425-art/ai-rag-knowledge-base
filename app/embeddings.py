import hashlib
import math
import re

from openai import OpenAI

from .config import Settings

DIMENSIONS = 384


def local_embedding(text: str) -> list[float]:
    """Reproducible character n-gram vectors for the no-key demo mode."""
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    tokens = re.findall(r"[\w]+", normalized)
    tokens.extend(normalized[i:i + 2] for i in range(max(0, len(normalized) - 1)))
    vector = [0.0] * DIMENSIONS
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        number = int.from_bytes(digest, "big")
        vector[number % DIMENSIONS] += 1.0 if number & (1 << 63) else -1.0
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else vector


class Embedder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.mode = "api" if settings.embedding_model and settings.api_key else "local"
        self.client = OpenAI(api_key=settings.api_key, base_url=settings.base_url) if self.mode == "api" else None

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.client:
            response = self.client.embeddings.create(model=self.settings.embedding_model, input=texts)
            return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        return [local_embedding(text) for text in texts]
