# Rate limit rules: list of (requests, window_seconds)
# Keyed by (endpoint_tag, trust_level)
# Multiple limits per key are ALL checked (e.g. per-minute AND per-day)

RULES: dict[tuple[str, int], list[tuple[int, int]]] = {
    # Trust 0 (unverified) — severe limits
    ("memory:write", 0): [(1, 60), (2, 86400)],           # 1/min AND 2/day
    ("memory:search", 0): [(30, 60)],                    # 30/min
    ("memory:get", 0): [(60, 60)],                       # 60/min

    # Trust 1 (trusted)
    ("memory:write", 1): [(5, 60), (50, 86400)],         # 5/min AND 50/day
    ("memory:search", 1): [(120, 60)],                   # 120/min
    ("memory:get", 1): [(300, 60)],                      # 300/min

    # Trust 2 (core)
    ("memory:write", 2): [(10, 60), (200, 86400)],       # 10/min AND 200/day
    ("memory:search", 2): [(120, 60)],
    ("memory:get", 2): [(300, 60)],
}


def get_limits(endpoint: str, trust_level: int) -> list[tuple[int, int]]:
    return RULES.get((endpoint, trust_level), [(10, 60)])
