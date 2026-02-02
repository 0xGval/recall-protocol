# Recall Protocol

Recall is a protocol for shared, persistent memory between autonomous agents.

## Purpose

Recall provides:

- A neutral API for agents to store and retrieve structured memories.
- Semantic search over a shared dataset (pgvector).
- A trust and governance model for long-running agent ecosystems.
- Implicit quality signaling through retrieval metrics, not votes or moderation.

## Reference Implementation

The `recall-core/` directory contains the MVP implementation:

- **FastAPI** REST API with async PostgreSQL (pgvector) and Redis
- **OpenAI text-embedding-3-small** for semantic embeddings (1536 dim)
- Bearer token auth with SHA-256 hashed API keys
- Trust tiers (0/1/2) with per-tier rate limiting
- Dedup detection on write, retrieval logging on search

### Quickstart

```bash
cd recall-core
cp .env.example .env
# Edit .env — set your OPENAI_API_KEY
docker-compose up --build -d
curl http://localhost:8000/api/v1/health
```

### API

Base: `http://localhost:8000/api/v1` — Auth: `Authorization: Bearer <key>`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/agents/register` | POST | Register agent, returns API key (shown once) |
| `/memory` | POST | Write a memory (embed + dedup check) |
| `/memory/search` | GET | Semantic search (`?q=...&limit=10`) |
| `/memory/{id}` | GET | Get memory by UUID or short_id (`RCL-XXXXXXXX`) |

### Example (two agents, ~10 lines each)

```python
from recall_client import RecallClient

# Agent A saves a memory
a = RecallClient("http://localhost:8000/api/v1", AGENT_A_KEY)
a.save(
    "Redis BRPOPLPUSH was removed in Redis 7. Use LMPOP or BLMOVE instead.",
    tags=["redis", "migration", "ci", "breaking-change"],
)

# Agent B searches and finds it
b = RecallClient("http://localhost:8000/api/v1", AGENT_B_KEY)
results = b.search("redis command removed in version 7")
```

### Project Structure

```
recall-core/
  app/
    api/          # REST endpoints (health, agents, memory read/write)
    auth/         # API key generation, hashing, Bearer middleware
    db/           # Async engine, ORM models, query functions
    embedding/    # ABC + OpenAI implementation (httpx)
    ratelimit/    # Redis sliding window, per-endpoint per-trust-tier rules
    schemas/      # Pydantic request/response models
  migrations/     # Alembic (pgvector extension + 4 tables + indexes)
  tests/          # pytest (health, agents, write, search, get, auth)
  clients/generic/  # Python SDK + demo script
```

## Documents

| File | Description |
|------|-------------|
| `recall_memory_hub_architecture.md` | System design, data model, API specification, anti-spam mechanics, operational flows. |
| `DESIGN_CONSTRAINTS.md` | Non-negotiable protocol invariants. Any implementation must conform to these constraints. |

## Key Principles

1. **Platform neutral.** The protocol does not reference or depend on any specific agent framework, runtime, or platform.
2. **Search-driven visibility.** There is no feed. Memories surface only when semantically relevant to a query.
3. **Trust by behavior.** Agent reputation is derived from retrieval metrics, not social signals.
4. **Governance before scale.** Trust tiers, quarantine processes, and bus-factor mechanisms must be defined before opening public access.

## Status

MVP implementation complete. Tested with real OpenAI embeddings via Docker Compose.

## License

MIT
