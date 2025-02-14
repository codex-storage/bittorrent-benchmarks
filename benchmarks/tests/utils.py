import json
from typing import List, Dict, Any


def compact(a_string: str) -> str:
    return "\n".join([line.strip() for line in a_string.splitlines() if line.strip()])


def make_jsonl(content: List[Dict[str, Any]]) -> str:
    return "\n".join([json.dumps(line, separators=(",", ":")) for line in content])
