# AI Coach / Treningsmotor — v0.1

A deterministic feedback engine for **[BUILD] AI Coach / Treningsmotor**.
It compares HQ's planned workout snapshots with actual execution and athlete
response, aggregates comparable observations, and returns explainable advice.
**HQ is the sole training-plan authority. The engine cannot write a plan.**

No ML, LLM calls, external services, real athlete records, or automatic scheduling
are included. All checked-in examples and fixtures are synthetic.

## Run

Python 3.11 or newer:

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -t . -v
ai-coach examples/synthetic_progress.json --audit history.sqlite
```

The command reads a JSON snapshot and writes a recommendation to stdout. The
optional SQLite file stores the input and output for replay. Input files are
never edited. Invalid input exits with status 2 without creating an audit event.
Audit files can contain athlete data; keep them outside this public repository.

```python
import json
from ai_coach.engine import evaluate
from ai_coach.audit import AuditLog

with open("examples/synthetic_progress.json", encoding="utf-8") as source:
    request = json.load(source)
advice = evaluate(request)
assert advice["state"] == "PROGRESS"
assert advice["requires_hq_approval"] is True
log = AuditLog("history.sqlite")
log.append(request, advice)
assert log.replay()
```

`PROGRESS` means a candidate for HQ review, not an instruction to increase any
particular workout. v0.1 deliberately does not generate a replacement dose.

## Boundaries and contracts

| Layer | Contents | Owner |
| --- | --- | --- |
| `source_facts` | Original source payload, provenance, corrections | Ingesting caller |
| `athlete_data` | Normalized planned / actual / response records with source references | Ingesting caller; planned authority HQ |
| `derived_features` | Completion, response completeness, outcome flags, sequence context | Engine |
| Recommendation | State, reasons, confidence, evidence references and review constraints | Engine advises; HQ decides |

Public JSON Schemas are in `schemas/`; runtime cross-record validation supplements
them. Planned, actual, and response records cannot contain recommendations.
Null response values mean **unknown**, never normal recovery or no pain.

Supported states: `KEEP`, `PROGRESS`, `CONSOLIDATE`, `REDUCE`, `MOVE`,
`AVOID_COMBINATION`, `INSUFFICIENT_EVIDENCE`.

## Project map

```text
schemas/                 versioned public wire contracts, packaged at installation
src/ai_coach/
  contracts.py           schema and referential/temporal validation; HQ envelope
  taxonomy.py            workout types, sports, stimuli, recommendation states
  features.py            pure feature extraction and conservative dose matching
  engine.py              versioned deterministic evidence and decision rules
  audit.py               append-only SQLite history, integrity checks and replay
  cli.py                 read input, emit advice, optionally append audit
tests/unit/              domain, evidence, validation and HQ-boundary tests
tests/integration/       CLI, fixtures, replay and audit integrity tests
tests/fixtures/          synthetic scenarios for every state
examples/                runnable synthetic request
scripts/                 reproducible schema and fixture generation
docs/                    audit, architecture, taxonomy, policy and HQ contract
```

## Scope of this baseline

Rules and cutoffs are explicit engineering defaults, **not validated training or
medical thresholds**. Confidence measures evidence strength, not a probability
of safety or improvement. Evidence is athlete-specific, limited to 84 days, and
matched on exact workout type, stimuli and planned dose. Current signals can stop
progression; a single event does not establish a permanent personal rule.

Combination advice describes an association, not causation. `AVOID_COMBINATION`
needs repeated exposures and a better comparable baseline. `MOVE` requests HQ
review when repeated spacing signals lack a conclusive baseline.

Device imports, automatic normalization, workout-library candidate ranking,
clinical interpretation, deployment, and live HQ integration are outside v0.1.
Pace/HR drift, power decay and interval consistency are not fabricated from
summary data. Corrections require an explicit new source fact and a rebuilt
normalized snapshot; previous audit events remain unchanged.

See [architecture](docs/architecture.md), [rule policy](docs/policy.md),
[HQ contract](docs/hq-contract.md), [taxonomy](docs/taxonomy.md), and
[initial repo audit](docs/repo-audit.md).

## Maintaining the contracts

After an editable installation, regenerate and verify committed artifacts:

```sh
python -m scripts.generate_schemas
python -m scripts.generate_fixtures
python -m unittest discover -s tests -t . -v
git diff --exit-code -- schemas tests/fixtures examples
```

Behavior changes require a policy version change, updated fixtures/tests and
documentation. Preserve the old engine version for exact historical replay.
