"""Regenerate synthetic integration fixtures and the runnable example."""
import json
from pathlib import Path

from tests.support import request_for

ROOT = Path(__file__).resolve().parents[1]
cases = {
    "INSUFFICIENT_EVIDENCE": request_for(1),
    "KEEP": request_for(3),
    "PROGRESS": request_for(5),
    "CONSOLIDATE": request_for(5, poor=(0,)),
    "REDUCE": request_for(5, poor=(4,)),
    "MOVE": request_for(3, poor=(0, 1, 2), combinations=(0, 1, 2)),
    "AVOID_COMBINATION": request_for(6, poor=(3, 4, 5), combinations=(3, 4, 5)),
}
for state, request in cases.items():
    path = ROOT / "tests" / "fixtures" / f"{state.lower()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"expected_state": state, "request": request}, indent=2) + "\n", encoding="utf-8")
example = ROOT / "examples" / "synthetic_progress.json"
example.parent.mkdir(exist_ok=True)
example.write_text(json.dumps(cases["PROGRESS"], indent=2) + "\n", encoding="utf-8")
