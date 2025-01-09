import json
from pathlib import Path
from typing import List, Dict, Any


def shared_volume() -> Path:
    return Path(__file__).parent.parent.parent.joinpath("volume")


def compact(a_string: str) -> str:
    return "\n".join([line.strip() for line in a_string.splitlines() if line.strip()])


def make_jsonl(content: List[Dict[str, Any]]) -> str:
    return "\n".join([json.dumps(line, separators=(",", ":")) for line in content])
