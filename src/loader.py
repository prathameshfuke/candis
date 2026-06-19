"""Load candidates efficiently."""
import gzip
from pathlib import Path
from typing import Iterator

try:
    import ujson as json
except ImportError:  # pragma: no cover
    import json


def iter_candidates(path: str) -> Iterator[dict]:
    """Stream candidates one at a time to keep memory usage low."""
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_all_candidates(path: str) -> list[dict]:
    """Load all candidates when callers explicitly want an in-memory list."""
    return list(iter_candidates(path))
