# Live Tredict experience-runtime deployment

The deterministic repository is intentionally separate from connector
credentials and private athlete data. The live deployment uses the connected
conversational runtime as the scheduler/connector layer and a private Google
Sheet as durable external persistence.

## Current deployment

As of 29 September 2026 the deployment is active.

- Tredict planned workouts are read as the runtime snapshot of the HQ plan.
- Executed Tredict activities are ingested without modifying them.
- Recent sleep and HRV are captured when Tredict exposes them.
- The runtime checks for new source facts every hour.
- New or revised plan rows are idempotent by plan ID + Tredict updatedAt.
- Executed activities are idempotent by Tredict activity ID.
- Explicit executedTrainingId links win over inferred matching.
- A unique same-sport activity may be reconciled inside the bounded time window.
- Multiple plausible matches stay AMBIGUOUS and require human review.
- Information-rich sessions may trigger a minimal subjective follow-up.
- Routine low-information sessions are allowed to pass silently.
- Private athlete data is stored outside the public GitHub repository.

The external ledger currently has four logical tables:

`Events`
: planned and actual exposure facts plus later response/decision events.

`RecoveryDaily`
: sparse daily sleep/HRV observations. Missing stays missing.

`PendingQuestions`
: only subjective fields that have enough expected information value to justify
  asking the athlete.

`SyncState`
: connector cursors/version markers used to make retries idempotent.

## Authority boundary

The live runtime may read Tredict and write the private experience ledger. It
must not write, move, delete or reschedule Tredict workouts as part of the
learning sync.

~~~text
Tredict planned workouts
          |
          v
     live collector
          |
Tredict activities + recovery
          |
          v
 private experience ledger
          |
          v
   learning / analysis
          |
          v
          HQ
          |
          v
 actual training plan
~~~

HQ remains the only training-plan authority.

## Why the private ledger exists

The public repository must not become the athlete database. Keeping the runtime
ledger private also allows the collection layer to change independently of the
deterministic engine. The ledger can later be migrated into the SQLite
ExperienceStore or another encrypted store because its rows use the same source
fact concepts: stable identity, event type, provenance, correction rather than
overwrite, and explicit missingness.

## Runtime behavior

Each sync should:

1. read SyncState and existing event keys;
2. fetch the bounded planned-workout and activity windows from Tredict;
3. append only new/revised source facts;
4. reconcile explicit links first and refuse ambiguous inference;
5. fetch normal detailed activity data for new key/benchmark/hard exposures;
6. capture sleep/HRV sparsely;
7. create minimal pending questions only when information value is high;
8. update SyncState only after a successful write;
9. remain silent unless athlete input, ambiguity resolution or an error needs
   attention.

This deployment is a data-acquisition foundation, not permission for autonomous
training-plan changes.
