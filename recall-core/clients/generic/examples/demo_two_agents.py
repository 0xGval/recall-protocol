"""Two agents share memory via Recall in ~10 lines each.

Prerequisites:
  pip install httpx
  export RECALL_URL=http://localhost:8000/api/v1
  export AGENT_A_KEY=recall_...
  export AGENT_B_KEY=recall_...
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from recall_client import RecallClient

URL = os.environ["RECALL_URL"]

# --- Agent A: saves a memory ---
a = RecallClient(URL, os.environ["AGENT_A_KEY"])
a.save(
    "Redis BRPOPLPUSH was removed in Redis 7. Use LMPOP or BLMOVE instead. Caught this during CI upgrade.",
    tags=["redis", "migration", "ci", "breaking-change"],
)
print("Agent A saved a memory.")

# --- Agent B: searches and finds it ---
b = RecallClient(URL, os.environ["AGENT_B_KEY"])
results = b.search("redis command removed in version 7")
for r in results:
    print(f"  Found: {r['short_id']} (sim={r['similarity']}) — {r['content'][:80]}...")
