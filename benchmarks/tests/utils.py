from pathlib import Path


def shared_volume() -> Path:
    return Path(__file__).parent.parent.parent.joinpath('volume')

def compact(a_string: str) -> str:
    return '\n'.join([line.strip() for line in a_string.splitlines() if line.strip()])