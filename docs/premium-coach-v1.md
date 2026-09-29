# Premium AI Coach v1

v1 is a coaching layer on top of the deterministic feedback engine. It is
designed to behave more like a high-touch performance coach than a static
workout generator while preserving one hard boundary: HQ owns the training plan.

## Daily coaching loop

A coaching cycle combines the current HQ plan, recent execution and adherence,
the feedback engine, a normalized execution gate, goal priorities, benchmark
freshness, capacities, available venues and calendar context.

The result contains:

- the HQ-approved A/B/C version to execute today;
- a fully rendered workout with athlete-specific targets when capacity data is available;
- a data-grounded motivational and accountability message;
- a bounded adaptation proposal for HQ;
- at most one due benchmark or spot-check candidate;
- recovery/performance actions from normalized sleep, stress, fueling and travel context;
- the connected-data reads the runtime should refresh;
- a post-workout prompt that closes the feedback loop.

The coach does not punish missed sessions by stacking make-up work. Falling
behind changes the immediate objective to restoring rhythm and protecting key stimuli.

## Accountability

The coach measures 14-day execution and separates Plan A, modified sessions and
misses. It surfaces a next action rather than only showing adherence.

## Decision support

The execution gate is normalized before v1 sees it.

- GREEN: execute HQ Plan A.
- AMBER: use HQ's pre-approved Plan B; Plan C may be used when B is absent.
- RED: use HQ's pre-approved Plan C or request an HQ review.

The coach cannot invent an easier session and silently replace HQ's plan.

## Life-aware coaching

The conversational runtime is expected to read Google Calendar and give HQ a
compact view of work, travel and available windows. Calendar data is context,
not an instruction. Calendar or training-plan writes remain explicit actions.

## Objective progress and adaptation

The feedback engine compares planned → actual → response → downstream quality.
v1 translates the result into concise coaching language and a one-step proposal.
PROGRESS never means increase frequency, volume and intensity together.

## Whole-system performance

The context supports normalized sleep, stress, fueling and travel states. v1
can surface concrete actions without pretending that a heuristic is a diagnosis.
Medical symptoms remain outside the autonomous coaching layer.

## Spot checks

The spot-check engine maintains benchmark freshness for running, cycling,
swimming and strength. A benchmark is proposed only with a GREEN execution gate,
is suppressed when another quality session was too recent, counts as quality
itself and still requires HQ placement.

## Tools and venues

Tredict is the training database: activities, planned workouts, capacity, zones
and training effort. Google Calendar supplies life constraints. MyWhoosh is a
winter indoor-cycling execution venue. EVO is a gym and treadmill venue.

The Python package stores no connector credentials. MyWhoosh and EVO have no
live connector in this repository, so the coach renders sessions for those
venues rather than claiming it can control them.

## Personalization

The learning ledger has four stages:

1. one exposure is an observation;
2. repeated consistent evidence can become a candidate rule;
3. stronger repeated evidence can become an established rule;
4. an explicit athlete or HQ correction overrides an inferred rule.

Personal rules can advise HQ but can never write the plan.

## v1-complete definition

For this repository, v1-complete means the core can cover the coaching loop with
normalized inputs:

calendar/life + HQ plan + training data + recovery gate
→ today's approved execution
→ workout prescription and venue
→ accountability and motivation
→ actual workout
→ deterministic feedback
→ personal pattern learning
→ bounded adaptation proposal
→ periodic benchmark
→ HQ decision

Autonomous plan writing, medical decision-making, raw-device ingestion,
background connector credentials and ML are intentionally outside v1.
