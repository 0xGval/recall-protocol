from abc import ABC, abstractmethod

import httpx

from app.config import settings


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...


class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self):
        self.model = settings.embedding_model
        self.api_key = settings.openai_api_key
        self._client = httpx.AsyncClient(timeout=30)

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": text},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


embedding_client: EmbeddingClient = OpenAIEmbeddingClient()
