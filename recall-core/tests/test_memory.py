import pytest


async def _register_and_get_key(client):
    resp = await client.post("/api/v1/agents/register", json={"name": "MemAgent"})
    return resp.json()["api_key"]


def _auth(key):
    return {"Authorization": f"Bearer {key}"}


SAMPLE_CONTENT = "x" * 100  # min 80 chars


@pytest.mark.anyio
async def test_write_memory(client):
    key = await _register_and_get_key(client)
    resp = await client.post(
        "/api/v1/memory",
        json={
            "content": SAMPLE_CONTENT,
            "tags": ["test", "unit"],
        },
        headers=_auth(key),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["short_id"].startswith("RCL-")


@pytest.mark.anyio
async def test_write_too_short(client):
    key = await _register_and_get_key(client)
    resp = await client.post(
        "/api/v1/memory",
        json={"content": "short", "tags": ["a", "b"]},
        headers=_auth(key),
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_write_too_few_tags(client):
    key = await _register_and_get_key(client)
    resp = await client.post(
        "/api/v1/memory",
        json={"content": SAMPLE_CONTENT, "tags": ["only_one"]},
        headers=_auth(key),
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_search_memories(client):
    key = await _register_and_get_key(client)
    # Write one
    await client.post(
        "/api/v1/memory",
        json={"content": SAMPLE_CONTENT, "tags": ["search", "test"]},
        headers=_auth(key),
    )
    # Search
    resp = await client.get(
        "/api/v1/memory/search",
        params={"q": "test query"},
        headers=_auth(key),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "results" in data


@pytest.mark.anyio
async def test_get_memory_by_short_id(client):
    key = await _register_and_get_key(client)
    write_resp = await client.post(
        "/api/v1/memory",
        json={"content": SAMPLE_CONTENT, "tags": ["get", "test"]},
        headers=_auth(key),
    )
    short_id = write_resp.json()["short_id"]

    resp = await client.get(f"/api/v1/memory/{short_id}", headers=_auth(key))
    assert resp.status_code == 200
    data = resp.json()
    assert data["memory"]["short_id"] == short_id


@pytest.mark.anyio
async def test_get_memory_not_found(client):
    key = await _register_and_get_key(client)
    resp = await client.get("/api/v1/memory/RCL-ZZZZZZZZ", headers=_auth(key))
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_unauthorized(client):
    resp = await client.post(
        "/api/v1/memory",
        json={"content": SAMPLE_CONTENT, "tags": ["a", "b"]},
    )
    assert resp.status_code == 401
