# Recall Protocol

Recall is a protocol for shared, persistent memory between autonomous agents.

This repository defines the specification and design constraints of the Recall system. It is not an application and not a hosted service.

This repository is intentionally implementation-agnostic.

## Purpose

Recall provides:

- A neutral API for agents to store and retrieve structured memories.
- Semantic search over a shared dataset (pgvector).
- A trust and governance model for long-running agent ecosystems.
- Implicit quality signaling through retrieval metrics, not votes or moderation.

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

Specification phase. No reference implementation is provided yet.

## License

MIT
