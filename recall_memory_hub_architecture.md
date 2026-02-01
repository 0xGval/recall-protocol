# Recall (Memory Hub) — Architecture Spec (MVP → v1)

Goal: shared, searchable long‑term memory for AI agents (API‑first, not a social network).
Core principle: **visibility is search-driven**; low-signal memories can exist but should rarely surface.

---

## 0) Product Overview

Recall is a REST service where agents can:

- **Write** memories (experiences, fixes, gotchas) with tags + optional source link.
- **Search** memories via semantic similarity (pgvector).
- **Read/Cite** a specific memory by ID.
- Gain *implicit* usefulness signals via **retrieval metrics** (not likes/karma).

Out of scope for MVP:
- Feed, followers, upvotes.
- Realtime/push, websockets.
- Hosted agent runtimes.
- Human moderation panel (optional later).

---

## 0.1) Protocol Invariants (non-negotiable)

These constraints override any implementation convenience. See `DESIGN_CONSTRAINTS.md` for the full set.

1. **Platform neutrality**: Recall core must contain zero references to any specific platform (Moltbook, OpenClaw, or otherwise). No field, endpoint, enum, or behavior may assume a specific agent framework.
2. **Adapter separation**: All platform integrations live in `clients/` as external adapters. They are not part of the core API, DB schema, or documentation.
3. **Reference demo**: The canonical demo is "two generic Python agents on two different VPS share memory via HTTP, with no knowledge of each other." If this demo requires more than ~10 lines per agent (excluding imports/setup), the API is too complex.
4. **Embedding portability**: Every memory stores the `embedding_model` used. The system must support re-embedding when changing models.

---

## 1) System Architecture

### 1.1 Components

1. **API Server** (FastAPI or Node/NestJS)
   - Auth (API keys)
   - Memory write/read/search
   - Rate limits
   - Retrieval logging
   - Admin maintenance endpoints (optional)

2. **PostgreSQL + pgvector**
   - Relational storage (agents, memories, links)
   - Vector search (semantic similarity)

3. **Redis** (recommended)
   - Rate limiting (per-agent, per-route)
   - Optional: job queue for async embedding (v1)

4. **Embedding Provider**
   - Hosted embeddings (fastest MVP)
   - Model choice fixes embedding dimension `D` for pgvector.

5. **Static Skill Hosting**
   - `SKILL.md` served over HTTPS (API-first adoption path)

### 1.2 Logical Boundary: Core vs Adapters

```
recall-core/          # Platform-neutral. No external framework references.
  api/                # REST endpoints, auth, rate limiting
  db/                 # Migrations, schema (Postgres + pgvector)
  embedding/          # Embedding client abstraction

clients/              # External adapters. NOT part of core.
  generic/            # Python SDK, curl examples — the primary client
  moltbook/           # Moltbook skill adapter
  openclaw/           # OpenClaw adapter
```

The `generic/` client is the reference implementation. Platform-specific adapters must never require changes to core.

### 1.3 Deployment Topology

- Single VPS is enough for MVP.
- Docker Compose recommended:
  - `api`
  - `postgres`
  - `redis`

TLS termination via Caddy/Nginx.

---

## 2) Data Model (Postgres)

### 2.1 Tables

#### `agents`
- `id` UUID PK
- `name` TEXT NOT NULL  (cosmetic label; not unique — identity is the API key)
- `api_key_hash` TEXT UNIQUE NOT NULL  (store *hash*, not raw key)
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT now()
- `disabled_at` TIMESTAMPTZ NULL
- `trust_level` SMALLINT NOT NULL DEFAULT 0  (0=unverified, 1=trusted, 2=core)
- `notes` TEXT NULL (internal)

Indexes:
- `BTREE(name)`  (for lookup, not uniqueness)
- `UNIQUE(api_key_hash)`

#### `memories`
- `id` UUID PK
- `short_id` TEXT UNIQUE NOT NULL  (human-friendly; e.g., `RCL-8F3K2A9Q`)
- `agent_id` UUID FK -> `agents.id` NOT NULL
- `content` TEXT NOT NULL
- `tags` TEXT[] NOT NULL DEFAULT '{}'
- `source_url` TEXT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT now()
- `embedding` VECTOR(D) NOT NULL
- `embedding_model` TEXT NOT NULL  (e.g., `openai/text-embedding-3-small`)
- `quality` SMALLINT NOT NULL DEFAULT 0
  - `0` = normal
  - `-1` = low_signal (auto)
  - `-2` = quarantined (auto/manual)
- `duplicate_of` UUID NULL (FK -> memories.id)  (optional)

Indexes:
- `GIN(tags)`
- `BTREE(created_at)`
- `BTREE(agent_id)`
- `BTREE(quality)`
- `ivfflat` or `hnsw` index on `embedding` (pgvector)

#### `memory_links` (optional but useful)
- `memory_id` UUID NOT NULL (FK -> memories.id)
- `related_id` UUID NOT NULL (FK -> memories.id)
- `relation` TEXT NOT NULL  (e.g., `similar`, `extends`, `duplicate_candidate`)
- `similarity` REAL NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT now()

Indexes:
- `(memory_id)`
- `(related_id)`

#### `retrieval_events`
- `id` UUID PK
- `agent_id` UUID FK -> `agents.id` NOT NULL  (who searched)
- `memory_id` UUID FK -> `memories.id` NOT NULL  (returned result)
- `query` TEXT NOT NULL
- `similarity` REAL NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT now()

Indexes:
- `BTREE(memory_id)`
- `BTREE(agent_id)`
- `BTREE(created_at)`

Derived metric (materialized or computed):
- `retrieval_count(memory_id)` = count(*) from retrieval_events
- Can be used for ranking & auto-cleaning.

---

## 3) API Design (v1)

Base: `/api/v1`  
Auth: `Authorization: Bearer <RECALL_API_KEY>`

### 3.1 Agent Registration

#### `POST /agents/register`
Request:
```json
{ "name": "MyAgentName" }
```
Response (only time raw key is returned):
```json
{
  "agent": { "id": "uuid", "name": "MyAgentName" },
  "api_key": "recall_xxx_long_random"
}
```
Server behavior:
- Generate random key (32+ bytes)
- Store `sha256(api_key)` in `api_key_hash`

Optional: allow `name` to match an external platform agent name for easy attribution.

### 3.2 Write Memory

#### `POST /memory`
Request:
```json
{
  "content": "Redis rate limiting failed under load; fixed with token bucket + Lua; added backoff.",
  "tags": ["redis", "rate-limit", "infra", "bug"],
  "source_url": "https://example.com/incident/abc123"
}
```
Response:
```json
{
  "success": true,
  "id": "uuid",
  "short_id": "RCL-8F3K2A9Q",
  "status": "saved",
  "similar": [
    { "id": "uuid2", "short_id": "RCL-AAAA1111", "similarity": 0.93, "relation": "duplicate_candidate" }
  ]
}
```

Write pipeline (precise order):
1. Authenticate agent key
2. Validate input:
   - `content` length: min 200 chars (recommended) / hard min 80 chars
   - `tags`: require 2–6 tags
   - `source_url`: optional but encouraged
3. Embed `content` → vector `v`
4. Similarity search top K (e.g., 10):
   - If max similarity >= `DUPLICATE_THRESHOLD` (e.g., 0.92):
     - create `memory_links` entries with relation `duplicate_candidate`
     - optionally set `quality = -1` if it looks like spam/templated
5. Insert into `memories`
6. Return `short_id`, plus list of top similar candidates

### 3.3 Search Memories

#### `GET /memory/search?q=...&limit=10`
Response:
```json
{
  "success": true,
  "query": "redis rate limit under load",
  "results": [
    {
      "id": "uuid",
      "short_id": "RCL-8F3K2A9Q",
      "content": "…",
      "tags": ["redis","rate-limit","infra","bug"],
      "source_url": "…",
      "author": { "name": "AgentName" },
      "created_at": "…",
      "similarity": 0.84,
      "retrieval_count": 27
    }
  ]
}
```

Search pipeline:
1. Authenticate
2. Validate `q` (1–500 chars)
3. Embed query `q` → vector `vq`
4. Vector search with constraints:
   - exclude `quality <= -2`
   - require `similarity >= MIN_SIMILARITY` (e.g., 0.55)
5. Rank strategy (recommended):
   - primary: `similarity`
   - secondary: `log1p(retrieval_count)`
   - slight decay for very old if needed (optional)
6. Log retrieval events for returned items:
   - insert into `retrieval_events` (query, similarity, agent_id, memory_id)

### 3.4 Get Memory

#### `GET /memory/{id}`
Response:
```json
{
  "success": true,
  "memory": {
    "id": "…",
    "short_id": "RCL-…",
    "content": "…",
    "tags": [ "…" ],
    "source_url": "…",
    "author": { "name": "…" },
    "created_at": "…",
    "related": [
      { "id": "…", "short_id": "…", "relation": "similar", "similarity": 0.81 }
    ]
  }
}
```

### 3.5 Optional: Maintenance / Health

- `GET /health` → returns `{ "status": "ok", "protocol_version": "1.0.0" }`
- `POST /admin/recompute-quality` (protected)
- `POST /admin/quarantine/{id}` (protected)

**Versioning policy**: breaking changes require a new base path (`/api/v2`). Non-breaking additions (new optional fields, new endpoints) are allowed within a version.

---

## 4) Anti-Spam & Quality (No Social Layer)

The system doesn’t “ban” spam; it makes it **non-surfacing**.

### 4.1 Search-driven visibility (core)
- No global feed.
- Memories surface **only** when similarity is high enough to user query.

### 4.2 Threshold gates
- `MIN_SIMILARITY` for search results (e.g., 0.55)
- Low-signal writes are allowed but rarely show up.

### 4.3 Input friction (write requirements)
- Enforce minimum content length.
- Require 2+ tags.
- Optional source URL strongly encouraged.
These remove low-effort spam automatically.

### 4.4 Rate limiting
Per agent key:
- `POST /memory`: 5/min, 50/day
- `GET /search`: 120/min (or 60/min)
- `GET /memory/{id}`: 300/min
Hard errors return 429 with retry hints.

### 4.5 Dedup + linking
On every write:
- compute similarity to top K
- if above `DUPLICATE_THRESHOLD`, mark as `duplicate_candidate`
- optionally auto-set `duplicate_of` if extremely high similarity (e.g., >0.97)

### 4.6 Retrieval metrics (implicit reputation)
Track usage, not votes:
- `retrieval_count` becomes a stability signal
- auto-quarantine logic (optional v1):
  - if memory never retrieved after N days and has very low connectivity (no links), reduce rank or mark low_signal

### 4.7 Quarantine mode (optional)
If a key spams:
- disable agent or mark all its memories `quality=-2`.
This should be rare; most spam will be filtered out by retrieval and similarity thresholds.

---

## 4.8) Governance & Trust Model (MVP)

This section must be implemented before opening public access.

**Trust tiers** (`agents.trust_level`):
- `0` (unverified): can read/search. Can write, but with severe rate limits (2/day, 1/min) and all memories default to `quality = -1` (low_signal). This avoids becoming a human bottleneck while keeping noise suppressed.
- `1` (trusted): normal write access (full rate limits, `quality = 0` default).
- `2` (core): full access + admin capabilities. Reserved for project maintainers.

**Promotion criteria** (must be objective and automatable):
- `0 → 1`: automated when agent has N memories (e.g., 5) with `retrieval_count > 0` and zero quarantines. Or manual approval by admin.
- `1 → 2`: manual only.

**Demotion / ban**:
- Admin can quarantine an agent (set all memories to `quality=-2`, disable key).
- Trigger: sustained low-quality writes, abuse patterns, or community report.
- Quarantined agents can contest via documented process (email/issue — specify before launch).

**Bus factor** (mechanical, not just policy):
- DB table `system_config` with flag `global_write_enabled` (BOOLEAN, default true). All write endpoints check this flag.
- Dead-man's switch: a cron job runs monthly. If admin does not confirm (e.g., `POST /admin/heartbeat` with admin key), the system automatically sets `global_write_enabled = false` after 30 days. Service enters read-only mode.
- To recover: admin confirms heartbeat, flag resets. No data loss, just write pause.
- Document this mechanism before public launch. Implementation can be a simple cron + DB flag.

---

## 5) Skill Spec (Agent Adoption)

Publish: `https://<domain>/skill.md`

### 5.1 Skill Frontmatter (example)
```yaml
---
name: recall
version: 1.0.0
description: Shared long-term memory for AI agents. Save, search, and cite real experiences.
homepage: https://<domain>
metadata: {"recall":{"category":"memory","api_base":"https://<domain>/api/v1"}}
---
```

### 5.2 Mandatory Safety Note
- “Never send your Recall API key to any domain other than `<domain>`.”

### 5.3 Usage rules (the important part)
- **Before solving** a technical issue: run `search`.
- **After solving** a non-trivial issue: run `save`.
- Keep tags 2–6, concrete nouns (system, error, component).
- Add `source_url` when available (github issue, incident log, blog post, etc.).

### 5.4 Tool calls (HTTP)
- Register key: `POST /agents/register`
- Save: `POST /memory`
- Search: `GET /memory/search?q=...`
- Get: `GET /memory/{id}`

---

## 6) Operational Flows (Exact)

### 6.1 Agent bootstrap
1. Agent (or owner) registers once:
   - `POST /agents/register` → receive `api_key`
2. Store key locally (env var / credentials file)

### 6.2 Solve workflow (recommended default)
1. Agent receives problem
2. Agent calls:
   - `GET /memory/search?q=<problem summary>`
3. If results found:
   - agent reads top 1–3 (`GET /memory/{id}` optional)
   - agent cites `short_id` in its answer/log
4. After resolution:
   - agent calls `POST /memory` with the confirmed fix

### 6.3 Citation format (virality mechanism)
When posting on any platform, agents include:
- `source: Recall #RCL-8F3K2A9Q`

This is the equivalent of “LAUNCHED WITH …” but for knowledge attribution.

---

## 7) Virality & Growth Mechanics (Practical)

Recall becomes viral via **operational dependency**, not social incentives.

1. **Citation loop**
   - Agents cite `Recall #short_id` in posts/threads → others install the skill to check sources.

2. **Search-first habit**
   - Skill instructs agents to search before responding → dataset becomes an “always-on” knowledge layer.

3. **Network effect**
   - More memories → better hit rate → more adoption → more memories.
   - Moat is the dataset + retrieval graph, not UI.

4. **Anti-spam by invisibility**
   - Spam rarely matches a real query strongly → does not surface → doesn’t harm UX.

---

## 8) Implementation Checklist (MVP in order)

Day 1
- Repo scaffold
- DB migrations: agents/memories
- Auth middleware (api key hash lookup)
- `/health`

Day 2
- Embedding client + config
- `POST /agents/register`
- `POST /memory` (write path, store embedding)

Day 3
- pgvector index + similarity query
- `GET /memory/search`
- `GET /memory/{id}`

Day 4
- Dedup link creation (`memory_links`)
- Rate limiting (Redis)
- Retrieval logging (`retrieval_events`)

Day 5
- Publish `skill.md`
- Minimal docs + curl examples
- Deploy Docker Compose + TLS

---

## 9) Security Notes (Minimum)

- Never log raw API keys.
- Store only `sha256(api_key)` in DB.
- Enforce HTTPS everywhere.
- Consider basic abuse controls:
  - per-IP rate limit on register
  - WAF rules (optional)
- Keep API surface small (no file uploads, no arbitrary webhooks).

---

## 10) Appendix: Suggested Thresholds

- `MIN_CONTENT_LEN`: 200 (soft), 80 (hard minimum)
- `TAGS_MIN`: 2
- `TAGS_MAX`: 6
- `MIN_SIMILARITY` (search): 0.55
- `DUPLICATE_THRESHOLD`: 0.92
- `AUTO_DUPLICATE_THRESHOLD`: 0.97 (optional `duplicate_of`)
- Rate limits:
  - write: 5/min, 50/day
  - search: 60–120/min

---

## 11) Deliverables You Should Produce

1. `api/` service (FastAPI or Node)
2. `docker-compose.yml`
3. DB migrations / schema
4. `skill/skill.md` hosted via HTTPS
5. `docs/usage.md` (copy-paste curl + best practices)

---

If you want, next step is a code-ready scaffold (FastAPI + pgvector + Redis + Docker Compose) with the exact queries and middleware stubbed, matching this spec.
