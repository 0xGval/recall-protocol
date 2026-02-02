# Rate limit rules: (requests, window_seconds)
# Keyed by (endpoint_tag, trust_level)

RULES: dict[tuple[str, int], tuple[int, int]] = {
    # Trust 0 (unverified) — severe limits
    ("memory:write", 0): (2, 86400),       # 2/day
    ("memory:search", 0): (30, 60),         # 30/min
    ("memory:get", 0): (60, 60),            # 60/min

    # Trust 1 (trusted)
    ("memory:write", 1): (5, 60),           # 5/min
    ("memory:search", 1): (120, 60),        # 120/min
    ("memory:get", 1): (300, 60),           # 300/min

    # Trust 2 (core) — same as trust 1 but could be raised
    ("memory:write", 2): (10, 60),
    ("memory:search", 2): (120, 60),
    ("memory:get", 2): (300, 60),
}


def get_limit(endpoint: str, trust_level: int) -> tuple[int, int]:
    return RULES.get((endpoint, trust_level), (10, 60))
