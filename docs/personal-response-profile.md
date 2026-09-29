# Personal Response Profile

The Personal Response Profile is the automatic materialization layer above the Athlete Experience Ledger.
It is descriptive before it is prescriptive.

It answers questions such as:

- how many comparable threshold, sweet-spot, long-endurance or strength exposures have actually been observed;
- how often recovery was known and how often it was normal;
- how often the next relevant session stayed good;
- which workout combinations repeatedly have good or poor outcomes;
- how much of an apparent signal is still UNKNOWN because follow-up data is missing;
- how past coach decisions performed when their later outcomes are known.

## Absorption is stricter than execution quality

A workout can be executed well without enough evidence to say it was absorbed well.
GOOD absorption therefore requires at least one known recovery or downstream response.
A high-quality activity alone is not enough. Missing follow-up remains UNKNOWN.

## Evidence states

- INSUFFICIENT_EVIDENCE: no known absorption outcome.
- OBSERVATION: one known outcome.
- EARLY_PATTERN: two or three known outcomes.
- CANDIDATE_PATTERN: at least four known outcomes with at least 70% consistency.
- ESTABLISHED_PERSONAL_RULE: at least six known outcomes, at least 80% consistency, and at least two known recent outcomes.
- MIXED_PATTERN: enough observations exist but the response is not consistent.

These thresholds are engineering policy defaults, not physiological laws. The profile remains advisory and cannot write the plan.

## Recency

Lifetime counts remain visible, but current coaching evidence is weighted by age: 0-28 days = 1.0, 29-56 = 0.75, 57-84 = 0.50, 85-180 = 0.25, and older evidence = 0 for the current response score.

## Four profile views

Dose response is produced both at workout-type level and exact dose-signature level. Workout-type aggregation is useful early; dose signatures prevent later silent pooling of materially different doses.

Spacing/sequence response keeps both good and poor adjacent-session outcomes. A possible negative spacing signal requires repeated exposed outcomes and a better baseline rather than a few isolated bad cases.

Weekly tolerance summarizes the last eight weeks by frequency, known duration, sport distribution and known absorption. It does not claim an optimal weekly volume.

Coach-decision evaluation groups KEEP, PROGRESS, CONSOLIDATE and other decisions with later known outcomes so the coaching policy itself can be audited.

## Runtime cadence

The live Experience Ledger is synchronized daily. The Personal Response Profile is normally materialized weekly before HQ weekly planning, and can be rebuilt on demand after an important benchmark or correction.

Each materialization is a snapshot. Old profile snapshots remain available so the system can inspect how its beliefs changed over time.

## No premature ML

This layer is deterministic. It creates the baseline that any future statistical or ML model must beat on a defined evaluation set.
