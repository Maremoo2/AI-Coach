# Runtime orchestration

The repository is the deterministic core. The conversational runtime supplies
fresh external context.

## Daily cycle

1. Read recent Tredict activities, normally the last 14 days.
2. Read Tredict planned workouts for today and the near future.
3. Read Google Calendar for relevant life constraints.
4. Reconcile the fresh data with HQ's current plan version.
5. Persist new plan/activity facts into the append-only Athlete Experience Store.
6. Produce or refresh the normalized execution gate.
7. Build a coach context and call `build_daily_brief`.
8. Present the selected HQ-approved variant and workout.
9. Store the coach decision beside the evidence available at decision time.
10. After execution, fetch the activity and collect only the subjective fields
    selected by adaptive sampling.
11. Run the deterministic feedback engine.
12. At 24/48 h, request recovery only when the session has enough information
    value to justify another question.
13. Link the next relevant session outcome when available.
14. Update personal pattern evidence and send only a bounded proposal back to HQ.

## Experience capture cadence

The runtime should capture information when it becomes available rather than
waiting for a weekly review:

- **HQ plan write/version:** append PLANNED_EXPOSURE.
- **Tredict activity appears:** reconcile and append ACTUAL_EXPOSURE.
- **Immediately post-workout:** run adaptive sampling; often zero questions for
  routine easy sessions.
- **~24 h / ~48 h:** recovery sampling only for key, hard, novel, benchmark or
  otherwise informative sessions.
- **Next relevant workout:** append DOWNSTREAM_OUTCOME.
- **Benchmark performed:** append BENCHMARK_STATE.
- **Coach/HQ decision:** append COACH_DECISION.
- **User correction:** append CORRECTION; never edit the original event.

## Reconciliation rule

Prefer an explicit planned-session link. If unavailable, a unique same-sport
activity within the configured time window may be matched. Multiple plausible
activities are AMBIGUOUS and require review. The runtime must never guess merely
to make the database look complete.

## Calendar/context reduction

Do not copy raw calendar titles, attendees, customer names or meeting notes into
the training store. Reduce them before persistence to training-relevant
constraints such as busy minutes, available training window, workday load,
travel and late-evening commitments.

## Weekly cycle

The runtime additionally reads current capacity and zones and the next 14 days
of planned work. It should export sparse learning rows and sequence observations
to the personal-pattern layer. GOOD combinations are retained as negative
evidence alongside POOR combinations.

HQ remains the single writer of the actual training plan.

## Tool safety

Read operations can be automated by the runtime. Writes to Tredict workout dates,
activity notes or Google Calendar must respect connector confirmation rules.
MyWhoosh and EVO are execution venues in v1; there is no credentialed live API
adapter in this repository.
