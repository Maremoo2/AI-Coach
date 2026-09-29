# AI Coach / Treningsmotor — v1.0

A deterministic, inspectable coaching system for a conversational premium coach.
It combines an HQ-owned training plan with actual training response, adherence,
life constraints, recovery context, available training venues and periodic
benchmarks.

HQ remains the sole training-plan authority. AI Coach can select only
pre-approved A/B/C variants for today's session and can send bounded proposals
back to HQ. It cannot silently rewrite the plan.

## What v1 adds

- Daily coaching brief with accountability and goal-oriented motivation.
- HQ-approved A/B/C execution gate.
- Versioned workout library for run, bike, swim, strength and recovery.
- Capacity-aware targets from FTP, running threshold and CSS when supplied.
- Winter bike execution through MyWhoosh as a venue.
- EVO gym/treadmill-aware strength and run execution.
- Post-workout feedback from plan → actual → response evidence.
- One-step adaptation proposals.
- Periodic goal-aligned benchmark / spot-check candidates.
- Conservative personal rule learning from repeated observations.
- Runtime tool policy for Tredict and Google Calendar.
- Existing append-only feedback audit and deterministic replay.
- CI tests on Windows/Linux and Python 3.11/3.12.

No ML is used in v1. No connector credentials or private athlete records are
checked into this public repository.

## Architecture

~~~text
Tredict + Calendar + athlete input
              |
              v
       normalized context
              |
              v
     execution/recovery gate
              |
        +-----+------+
        |            |
        v            v
   HQ plan A/B/C   feedback history
        |            |
        +-----+------+
              v
        AI Coach v1
   workout + accountability
   motivation + spot checks
   adaptation proposal
              |
              v
             HQ
              |
              v
     actual training plan
~~~

There is no direct AI-Coach → training-plan write edge.

## Run

~~~sh
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests -t . -v
ai-coach examples/synthetic_progress.json --audit history.sqlite
ai-coach-v1 examples/coach_context.json
~~~

## Core modules

- engine.py: deterministic plan → actual → response feedback.
- coach.py: daily premium-coach orchestration.
- workout_library.py: finite versioned workout/session library.
- progression.py: one-step HQ adaptation proposals.
- spot_checks.py: benchmark freshness and placement candidates.
- personalization.py: repeated-pattern learning without ML.
- tool_policy.py: Tredict / Calendar / venue capability boundary.
- audit.py: append-only SQLite history and replay.

See docs/premium-coach-v1.md and docs/runtime-orchestration.md for the v1
operating model.

## Safety and scope

Confidence is evidence strength, not a probability of safety or improvement.
A single bad session can create a precautionary signal but not a permanent
personal rule. User corrections override inferred preferences. Benchmarks count
as quality sessions and are not stacked onto another quality day.

v1 does not diagnose illness/injury, autonomously edit Tredict/Calendar, or
write HQ's plan. It also does not pretend MyWhoosh or EVO have a live connector
when they do not.
