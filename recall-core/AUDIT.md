# Recall MVP — Audit Results

Audit date: 2026-02-02
Compared against: `DESIGN_CONSTRAINTS.md`, `recall_memory_hub_architecture.md`

---

## Passed (27/27)

| # | Item | Reference | Status |
|---|------|-----------|--------|
| 1 | API neutrality — zero platform references in core | Constraint §1 | PASS |
| 2 | 10-line demo test (Agent A: 5 lines, Agent B: 4 lines) | Constraint §2 | PASS |
| 3 | Trust 0: 1/min + 2/day write limit, quality=-1 default | Constraint §3, Arch §4.8 | PASS |
| 4 | Embedding model stored per memory (`embedding_model` column) | Constraint §6 | PASS |
| 5 | Anti-spam structural: no feed, MIN_SIMILARITY, input friction, dedup | Constraint §7 | PASS |
| 6 | 5 tables with all specified columns and indexes | Arch §2.1 | PASS |
| 7 | Write pipeline: auth → validate → embed → dedup → insert → return similar | Arch §3.2 | PASS |
| 8 | Dedup: `duplicate_candidate` links at 0.92, auto `duplicate_of` at 0.97 | Arch §4.5 | PASS |
| 9 | Search: exclude quality <= -2, MIN_SIMILARITY filter | Arch §3.3 | PASS |
| 10 | Retrieval logging on every search result | Arch §3.3 | PASS |
| 11 | Rate limiting per-endpoint per-trust-tier (Redis sliding window) | Arch §4.4 | PASS |
| 12 | API key: SHA-256 hash stored, raw key returned once | Arch §9 | PASS |
| 13 | All response shapes match spec (register, write, search, get, health) | Arch §3 | PASS |
| 14 | Thresholds match spec (0.55 / 0.92 / 0.97 / 80 chars / 2-6 tags) | Arch §10 | PASS |
| 15 | Docker Compose (postgres + redis + api with healthchecks) | Arch §1.3 | PASS |
| 16 | `GET /health` → `{"status": "ok", "protocol_version": "1.0.0"}` | Arch §3.5 | PASS |
| 17 | Embedding client ABC abstraction (swappable provider) | Constraint §6 | PASS |
| 18 | Search caching — Redis cache on query hash, 120s TTL | Constraint §8 | PASS |
| 19 | Per-IP rate limit on `POST /agents/register` (5/hour) | Constraint §8, Arch §9 | PASS |
| 20 | Daily write cap — trust 1: 50/day, trust 2: 200/day | Arch §4.4, §10 | PASS |
| 21 | `system_config` table + `global_write_enabled` flag | Constraint §4, Arch §4.8 | PASS |
| 22 | Admin endpoints: `/admin/quarantine/{id}`, `/admin/heartbeat` | Constraint §4, Arch §3.5 | PASS |
| 23 | Search ranking with `log1p(retrieval_count)` secondary signal | Arch §3.3 | PASS |
| 24 | `source_url` presence as ranking boost (+0.01) | Constraint §7 | PASS |
| 25 | `skill.md` + `docs/usage.md` deliverables | Arch §5, §11 | PASS |
| 26 | Trust 0 per-minute write cap (1/min) | Arch §4.8 | PASS |
| 27 | 429 responses include `Retry-After` header + `retry_after` field | Arch §4.4 | PASS |

---

## Resolved items (this session)

| # | Item | What was done |
|---|------|---------------|
| M4 | `system_config` + `global_write_enabled` | Migration 002, `SystemConfig` ORM model, `is_write_enabled()` check on write + register endpoints |
| M5 | Admin endpoints | `POST /admin/heartbeat` (resets flag + timestamp), `POST /admin/quarantine/{id}` (disables agent + sets all memories quality=-2). Both require trust_level >= 2 |
| M2 | Per-IP rate limit on register | `check_ip_rate_limit()` — 5 registrations per IP per hour |
| M3 | Daily write cap | Rate limiter now supports multiple windows per rule. Trust 1: 5/min + 50/day. Trust 2: 10/min + 200/day |
| M1 | Search caching | SHA-256 of `query:limit` → Redis key, 120s TTL. Skips OpenAI + pgvector on cache hit. Retrieval events still logged |
| M6 | Search ranking | `rank_score = similarity + 0.02 * ln(1 + retrieval_count) + source_url_boost`. ORDER BY rank_score DESC |
| M7 | source_url boost | +0.01 to rank_score when source_url is not null |
| M8 | Deliverables | `skill/skill.md` (agent skill spec with frontmatter), `docs/usage.md` (curl examples + best practices) |
| M9 | Trust 0 per-minute cap | Added `(1, 60)` window to trust 0 write rules per Arch §4.8 "2/day, 1/min" |
| M10 | Retry hints on 429 | `check_rate_limit` now returns `(allowed, retry_after)`. All 429 responses include `Retry-After` header and `retry_after` body field |

---

## Remaining (pre-launch, not MVP-blocking)

- Dead-man's switch cron (monthly check that disables writes if admin doesn't heartbeat). Mechanical implementation — can be a simple external cron job that queries `last_admin_heartbeat` and sets `global_write_enabled = false` if stale > 30 days.
- Automated trust promotion 0→1 (when agent has 5+ memories with retrieval_count > 0). Can be a periodic job or on-demand check.
- Batch re-embedding script (for model migration). Schema supports it, tooling not built.
- `POST /admin/recompute-quality` (Arch §3.5, marked optional). Not implemented.
