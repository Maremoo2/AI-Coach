# Runtime orchestration

The repository is the deterministic core. The conversational runtime supplies
fresh external context.

## Daily cycle

1. Read recent Tredict activities, normally the last 14 days.
2. Read Tredict planned workouts for today and the near future.
3. Read Google Calendar for relevant life constraints.
4. Reconcile the fresh data with HQ's current plan version.
5. Produce or refresh the normalized execution gate.
6. Build a coach context and call build_daily_brief.
7. Present the selected HQ-approved variant and workout.
8. After execution, fetch the activity and collect missing subjective response.
9. Run the deterministic feedback engine.
10. Store the observation, update personal pattern evidence and send only a
    bounded proposal back to HQ.

## Weekly cycle

The runtime additionally reads current capacity and zones and the next 14 days
of planned work. HQ remains the single writer of the actual training plan.

## Tool safety

Read operations can be automated by the runtime. Writes to Tredict workout dates,
activity notes or Google Calendar must respect connector confirmation rules.
MyWhoosh and EVO are execution venues in v1; there is no credentialed live API
adapter in this repository.
