from pathlib import Path


def shared_volume() -> Path:
    return Path(__file__).parent.parent.parent.joinpath('volume')