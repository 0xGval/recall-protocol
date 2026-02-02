import pytest


@pytest.mark.anyio
async def test_register_agent(client):
    resp = await client.post("/api/v1/agents/register", json={"name": "TestAgent"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"]["name"] == "TestAgent"
    assert data["api_key"].startswith("recall_")
    assert len(data["api_key"]) > 20


@pytest.mark.anyio
async def test_register_empty_name(client):
    resp = await client.post("/api/v1/agents/register", json={"name": ""})
    assert resp.status_code == 422
