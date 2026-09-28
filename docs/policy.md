# Deterministic policy rules-0.1.0

All thresholds below are explicit engineering defaults for testing and future
evaluation, not empirically calibrated athlete or clinical guidance.

## Comparable evidence

Pool only the same athlete, workout type, sorted stimulus set, and exact planned
dose (including interval structure, intensity and volume unit). Use actual
start times in the inclusive preceding 84-day window. No fuzzy dose matching
or unit conversion is performed. Different doses/types and unperformed planned
sessions are excluded from the cohort and listed in the result.

A complete response needs actual RPE/quality, pain, 24h and 48h recovery and
linked downstream quality. Sleep is retained as context but not currently used
in decisions. Unknown required values cannot count as complete success.

- Adverse: execution C, duration completion <0.8, quality <0.6, reported pain >0,
  poor recovery at either observation, or poor linked next-session quality.
- Successful: complete, no adverse flag, execution A, completion [0.95,1.1],
  quality >=0.8 and RPE <=8.
- Trend: last two minus first two complete-session quality averages, when at
  least four exist. This is a descriptive comparison, not a fitted model.

## Decision precedence

1. Any reported pain in the same workout type in the last 21 days: `REDUCE`,
   flagged as a precautionary signal, not a learned rule (even at another dose).
2. Recent adverse response at another dose of that type: `CONSOLIDATE`; HQ
   reviews the changed tolerance before accepting progression.
3. For the latest comparable exposure's combination, >=3 complete exposures
   with >=2/3 adverse outcomes: `AVOID_COMBINATION` if >=3 complete baseline
   observations have <=1/3 adverse outcomes and the rate difference is >=0.4.
   Otherwise `MOVE` to request a spacing review. Latest exposure must be recent.
4. Latest comparable exposure adverse and recent: precautionary `REDUCE`.
5. Fewer than three complete comparable sessions: `INSUFFICIENT_EVIDENCE`.
6. Latest comparable session older than 21 days: `INSUFFICIENT_EVIDENCE`.
7. At least half complete comparable sessions adverse: `REDUCE`.
8. Latest comparable response incomplete: `CONSOLIDATE`.
9. >=5 complete sessions, all comparable sessions complete and successful,
   trend no worse than -0.05: `PROGRESS`.
10. Any adverse history, trend below -0.05, or success rate <0.8: `CONSOLIDATE`.
11. Otherwise: `KEEP`.

Recent negative signals at other doses contribute source evidence but are not
pooled into comparable dose statistics. No single successful exposure yields
progression, spacing policy, or a permanent tolerance rule.

## Combinations

Derive the nearest preceding actual session whose end is within 36 hours of the
current actual start. Keys combine prior/current workout types and a 0–24h or
24–36h spacing band. Ties use session ID for deterministic ordering. The
baseline is comparable sessions without that exact preceding combination.
Reports are associations; context, selection bias and confounding are unresolved.
Coverage depends on complete activity history supplied by the caller. An absent
prior session is not proof of no preceding exercise.

## Confidence

`n` = complete comparable sessions; coverage = n / comparable sessions.
Consistency = largest of successful, adverse, and neutral fractions.

```text
score = min(0.95, n / 8) × coverage × (0.5 + 0.5 × consistency)
        × (1 if recent else 0.5)
```

Round to three decimals. Cap precautionary advice, MOVE and insufficient
evidence at 0.35. For AVOID_COMBINATION also cap by the smaller exposure/baseline
count divided by eight. Labels: HIGH >=0.8, MODERATE >=0.5, otherwise LOW.
This score is an explainable evidence-strength heuristic, not a calibrated
probability. Missing, old and inconsistent evidence lowers confidence.
