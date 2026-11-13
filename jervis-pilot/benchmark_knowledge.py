"""Synthetic retrieval benchmark; does not measure model or Matt's hardware."""
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
import json
from jarvis_knowledge import retrieve

with TemporaryDirectory() as folder:
    root = Path(folder)
    (root / "Data").mkdir()
    for number in range(100):
        (root / "Data" / f"record-{number:03}.txt").write_text(
            "\n".join(f"Business record {number}, item {line}, cobalt delivery scheduled Friday."
                      for line in range(50)), encoding="utf-8")
    start = perf_counter()
    cold, _ = retrieve("cobalt delivery", root)
    cold_seconds = perf_counter() - start
    durations = []
    for _ in range(5):
        start = perf_counter()
        warm, _ = retrieve("cobalt delivery", root)
        durations.append(perf_counter() - start)
        assert warm == cold and len(warm) == 6
    print(json.dumps({"files": 100, "lines": 5000, "cold_index_and_query_seconds": cold_seconds,
                      "warm_query_seconds": durations,
                      "scope": "Synthetic Windows CI retrieval only; excludes LLM generation and PDF parsing"}, indent=2))
