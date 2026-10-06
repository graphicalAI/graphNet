from pathlib import Path


def resource_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[1] / "Assets" / filename
