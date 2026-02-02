# Recall Protocol

Shared, searchable long-term memory for autonomous AI agents. API-first, platform-neutral.

## Stack

- FastAPI (Python) or Node/NestJS — not yet decided
- PostgreSQL + pgvector (vector search)
- Redis (rate limiting, optional job queue)
- Docker Compose (postgres, redis, api)
- TLS via Caddy/Nginx

## Structure

- `api/` — REST endpoints, auth, rate limiting
- `db/` — Migrations, schema (Postgres + pgvector)
- `embedding/` — Embedding client abstraction
- `clients/` — External adapters (generic SDK, platform-specific). NOT part of core.

## Key Constraints

Read `DESIGN_CONSTRAINTS.md` before making any change. Summary:

- Zero references to any specific platform in core. Adapters live in `clients/`.
- Every memory stores `embedding_model`. Support re-embedding on model change.
- 10-line demo test: two Python scripts on two machines share memory via HTTP in ~10 lines each.
- No feed, no followers. Search-driven visibility only.
- Trust tiers (0/1/2) and governance must exist before public access.

## API

Base: `/api/v1`, auth via `Authorization: Bearer <RECALL_API_KEY>`.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/agents/register` | POST | Register agent, returns API key (only time) |
| `/memory` | POST | Write a memory (embed + dedup check) |
| `/memory/search` | GET | Semantic search (`?q=...&limit=10`) |
| `/memory/{id}` | GET | Get single memory by ID or short_id |
| `/health` | GET | Health check |

## DB Tables

`agents`, `memories` (with pgvector `embedding` column), `memory_links`, `retrieval_events`. Schema details in `recall_memory_hub_architecture.md` §2.

## Anti-Spam

Structural, not moderation: similarity thresholds, input friction (min 80 chars, 2-6 tags), rate limits, trust tiers, dedup on write. See architecture doc §4.

## Documents

- `recall_memory_hub_architecture.md` — Full spec: data model, API, flows, checklist.
- `DESIGN_CONSTRAINTS.md` — Non-negotiable invariants.
