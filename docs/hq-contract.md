# HQ advisory contract 1.0

## Input

`evaluation_request.schema.json` describes a complete snapshot:

- `schema_version`, `as_of`, and `target_session_id`.
- `source_facts`: original payloads, IDs, timestamps, provenance and corrections.
- `athlete_data`: one athlete and planned/actual/response session records.

`planned_workout.schema.json` requires `authority: HQ` and `plan_version`.
Planned sessions are read-only snapshots. Actual and response can be null.
Unknown measurements are explicit nulls, not zeros or omitted evidence.
Individual schemas are public; the aggregate request additionally requires
referential and temporal validation by `validate_request`.

## Output

`recommendation.schema.json` permits only a fixed advisory envelope:

- One of the seven documented recommendation states.
- `authority: ADVISORY_ONLY` and `requires_hq_approval: true`.
- Athlete, target session and the exact HQ plan version evaluated.
- Reason codes, evidence session/source references, features and confidence.
- Input hash plus engine, policy and taxonomy versions for audit replay.
- Explicit constraints requiring HQ approval and revalidation after changes.

There is no plan, schedule patch, calendar event, automatic acceptance field,
or next-dose prescription. `MOVE` does not select a date. `PROGRESS` does not
select a dose. `AVOID_COMBINATION` describes evidence for a particular preceding
type and spacing band and is not a permanent ban.

## HQ responsibilities

1. Authenticate the source of the request and advisory response.
2. Match athlete/session IDs and the current `plan_version`.
3. Reject stale outputs if observations, plan or tolerance have changed.
4. Inspect missing evidence, confidence, reason codes and constraints.
5. Approve, reject or defer using HQ's own decision workflow.
6. If approved, HQ alone writes a new training-plan version.

An `INSUFFICIENT_EVIDENCE` response requests more observations. A precautionary
`REDUCE` may be based on a single recent adverse signal but explicitly does not
claim a learned personal rule. Confidence must never be interpreted as a
probability of safety. HQ may reject any recommendation, including `KEEP`.

v0.1 implements the engine side of this contract. No live HQ service, approval
database or training-plan integration is assumed to exist.

## Local v1 HQ adapter
The local application implements HQAuthority as the sole HQ_PLAN writer in its normal workflow. It requires a separate HQ credential, fresh journal revision, unchanged policy/code/schema manifest and explicit approval. The engine and language adapter cannot approve. Explicit HQ-authored imports are a separate authorized path. This is not a connection to an external HQ service or a security boundary against a local administrator. See [v1 architecture](v1-architecture.md).

