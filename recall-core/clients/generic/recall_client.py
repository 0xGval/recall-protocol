"""Minimal Recall client — the reference SDK."""

import httpx


class RecallClient:
    def __init__(self, base_url: str, api_key: str):
        self._url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._http = httpx.Client(timeout=30)

    def save(self, content: str, tags: list[str], source_url: str | None = None) -> dict:
        body = {"content": content, "tags": tags}
        if source_url:
            body["source_url"] = source_url
        r = self._http.post(f"{self._url}/memory", json=body, headers=self._headers)
        r.raise_for_status()
        return r.json()

    def search(self, query: str, limit: int = 5) -> list[dict]:
        r = self._http.get(
            f"{self._url}/memory/search",
            params={"q": query, "limit": limit},
            headers=self._headers,
        )
        r.raise_for_status()
        return r.json()["results"]

    def get(self, memory_id: str) -> dict:
        r = self._http.get(f"{self._url}/memory/{memory_id}", headers=self._headers)
        r.raise_for_status()
        return r.json()["memory"]
