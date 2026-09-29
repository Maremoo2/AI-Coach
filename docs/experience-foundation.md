# Athlete Experience Foundation

The experience foundation exists so later versions of AI Coach can learn from
clean longitudinal evidence rather than trying to reconstruct context months
after the fact.

It is intentionally a data foundation, not machine learning.

## What is stored

Each relevant training exposure gets a stable experience ID. Facts are appended
as immutable events:

- planned exposure from HQ;
- actual exposure from Tredict/device data;
- selectively sampled subjective response;
- 24 h / 48 h recovery response when it is information-rich;
- privacy-reduced life context;
- downstream next-session outcome;
- benchmark state;
- the coach/HQ-facing decision that was made;
- explicit corrections.

The original event is never overwritten. A correction points to the original
event and overlays corrected fields only when a materialized view is requested.

## Facts vs interpretation

Raw observations are kept separate from derived features and labels. A future
algorithm can therefore recompute dose signatures, outcome labels, sequence
features or personal rules without rewriting history.

Missing remains missing. No response is never treated as normal recovery.

## Adaptive sampling

Routine easy sessions should create very little friction. Subjective questions
are prioritized for key sessions, benchmarks, novel doses, hard sessions,
modified/failed execution, low quality and pain signals.

The first small number of routine sessions may be sampled to establish a
baseline. After that, low-information sessions can remain silent.

## Life-context privacy

The store does not need raw calendar event titles, attendees, customer names or
meeting notes. Calendar/runtime context should first be reduced to fields such as:

- workday load;
- busy minutes;
- available training window;
- travel;
- late-evening commitment;
- sleep/stress/fueling status when known.

This gives the coach useful constraints without turning the training database
into a general personal diary.

## Reconciliation

HQ plan sessions are the preferred anchor. Actual activities can be linked by an
explicit planned-session reference. If that reference is unavailable, a unique
same-sport activity inside the configured time window may be linked. Ambiguous
matches are surfaced for review rather than guessed.

## Negative evidence

Sequence analysis stores successful as well as adverse combinations. If
CrossFit → bike threshold works well, that is evidence too. This prevents the
system from learning a false avoidance rule merely because only bad cases were
recorded.

UNKNOWN remains a separate outcome whenever response data is insufficient.

## Decision ledger

Coach decisions are stored beside the evidence available at the time. This makes
it possible to evaluate the coach later:

- What did the coach/HQ recommend?
- What evidence supported it?
- What happened afterward?
- Did repeated decisions of that type improve or degrade outcomes?

This is a prerequisite for improving the coaching policy itself.

## Storage

`ExperienceStore` is an append-only, hash-linked SQLite event store. UPDATE and
DELETE operations are rejected by database triggers. Idempotency keys prevent a
connector retry from creating duplicate observations.

The store is athlete data and must remain outside the public repository.

## Future use

The exported learning rows are deliberately sparse and recomputable. They can
later support:

- tolerated frequency and volume models;
- dose-response analysis;
- spacing/combination learning;
- recovery-cost estimates;
- benchmark-response analysis;
- decision-policy evaluation;
- eventually, ML only if it can outperform the deterministic baseline on a
  defined evaluation set.
