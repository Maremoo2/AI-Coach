# AI Coach / Treningsmotor — v1.5

A deterministic, inspectable coaching system for a conversational premium coach.
It combines an HQ-owned training plan with actual training response, adherence,
life constraints, recovery context, available training venues and periodic
benchmarks.

HQ remains the sole training-plan authority. AI Coach can select only
pre-approved A/B/C variants for today's session and can send bounded proposals
back to HQ. It cannot silently rewrite the plan.


## Garmin connection (v1.5)

Optional direct, unofficial Garmin activity sync now replaces Tredict activity
history in the local view. Local terminal login, manual sync, private tokens,
source preservation and account/duplicate checks are implemented. HQ remains the
sole plan authority. See [Garmin setup](docs/garmin.md).

**Current local app status:** no scheduled sync, Garmin file import, sleep/HRV
sync or automatic feedback-engine ingestion yet. Live account validation awaits
local user login. Older external-runtime checkboxes below describe separate
modules/deployments, not an automatically connected local app. Roadmap dates are
targets, not delivery guarantees. Race choice remains conditional on athlete/HQ
confirmation; older Copenhagen milestones below are historical planning context.

Next: verify real Garmin import, connect plan/actual/subjective response to the
engine, then verify the full user flow. TrainingPeaks is deferred.

## Personal onboarding (v1.4)

The local app can now display private, dated Tredict history and the existing
HQ plan alongside sourced goals, flexible availability and progression context.
Monthly/weekly time uses the provider's recorded active and elapsed durations.
Unknown response, baseline and race date remain unknown. No plan is created by
this import. See [personal onboarding](docs/personal-onboarding.md).

## Local coaching app (v1.3)

The local v1 interface is now included alongside the existing v1.2 orchestration
and response-profile foundation. Run `.\Start-Coach.ps1 -Demo` on Windows, or
install the package and run `ai-coach-app --demo --open`.

It adds goals and measurements, check-ins, weekly summaries, optional language
assistance, and separately authorized local HQ plan approval. The local app does
not automatically consume the experience/profile store or connect to a deployed
Tredict runtime. Those existing modules and commands remain available unchanged.

See [local app setup and limitations](docs/local-app.md),
[application architecture](docs/v1-architecture.md), and
[source and transfer analysis](docs/v1-analysis.md).

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
- Append-only Athlete Experience Store for longitudinal learning.
- Privacy-reduced life-context capture, corrections and decision history.
- Adaptive post-workout/recovery sampling to reduce questionnaire noise.
- Plan↔actual reconciliation that refuses ambiguous matches.
- Sequence evidence that stores successful as well as adverse combinations.
- Weekly Personal Response Profile materialization with recency-weighted evidence.
- Dose, spacing, weekly-tolerance and coach-decision profile views.
- CI tests on Windows/Linux and Python 3.11/3.12.

No ML is used in v1. No connector credentials or private athlete records are
checked into this public repository.

## Architecture

~~~text
Garmin / optional imports + Calendar + athlete input
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


## Roadmap to the premium coach

This roadmap tracks the path from the current deterministic training engine to a
high-touch personal performance coach. The guiding product principle is simple:
workout generation is not the premium feature. The premium value comes from
accountability, decision support, life-aware planning, objective progress checks
and increasingly accurate athlete-specific adaptation.

**Status legend**

- `[x]` implemented and covered by the current core.
- `[~]` partially implemented; foundation exists but the full operational loop is not yet live.
- `[ ]` planned.

### Target operating model

~~~text
HQ plan + activity sources + Calendar + recovery + athlete input
                         |
                         v
                AI Coach decision layer
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
 today's action    accountability     spot checks
 concrete workout motivation          progress evidence
        |                |                |
        +----------------+----------------+
                         v
                 actual execution
                         |
                         v
          plan -> actual -> response
                         |
                         v
              personal pattern learning
                         |
                         v
             bounded proposal back to HQ
                         |
                         v
                 HQ decides the plan
~~~

The coach should eventually make the daily training decision feel simple to the
athlete while keeping the underlying reasoning inspectable. HQ remains the only
authority that can change the actual training plan.

### Phase 1 — Stable coaching core
**Target: now through October 2026**  
**Status: [x] core implemented; [~] still accumulating real athlete evidence**

Goal: make the foundation boring, deterministic and trustworthy before adding
more autonomy.

- [x] HQ-only plan authority.
- [x] Planned -> actual -> response -> downstream-quality feedback model.
- [x] A/B/C execution model.
- [x] Workout taxonomy separated from physiological stimulus.
- [x] KEEP / PROGRESS / CONSOLIDATE / REDUCE / MOVE / AVOID_COMBINATION /
  INSUFFICIENT_EVIDENCE states.
- [x] Explainable confidence and evidence references.
- [x] Append-only audit history and deterministic replay.
- [x] Cross-platform automated tests.
- [x] Append-only Athlete Experience Store with stable experience IDs.
- [x] Immutable source events plus explicit correction events.
- [x] Idempotent ingestion so connector retries do not duplicate evidence.
- [x] Privacy-reduced calendar/life context rather than raw diary content.
- [x] Adaptive subjective sampling for high-information sessions.
- [x] Coach-decision and benchmark event types for later policy evaluation.
- [x] Deterministic plan↔actual reconciliation with ambiguous-match protection.
- [x] GOOD/POOR/UNKNOWN sequence capture so successful combinations count too.
- [~] Feed the store enough real athlete sessions to replace synthetic evidence
  with meaningful personal history.
- [~] Separate external runtime supports Tredict collection; local app now supports manual Garmin activity sync.
- [x] Runtime reconciliation is automated with explicit-link priority and ambiguity protection.
- [~] Accumulate enough real athlete sessions for high-confidence personal rules.
- [x] Deterministic Personal Response Profile materializer with UNKNOWN-preserving absorption logic.
- [x] Weekly profile snapshots for dose response, spacing, tolerance and coach-decision evaluation.

**Exit criteria:** the system can explain why a dose should be kept, progressed,
consolidated, reduced or moved, and the explanation points back to actual
comparable evidence rather than generic coaching rules.

### Phase 2 — Daily coach
**Target: October–November 2026**  
**Status: [~] deterministic daily-coach core exists; live runtime orchestration remains**

Goal: answer "what should I do today?" with one clear, context-aware execution
decision and a complete session prescription.

- [x] Daily coaching brief.
- [x] GREEN / AMBER / RED execution gate.
- [x] Selection of HQ-approved A/B/C variants only.
- [x] Versioned workout library.
- [x] Capacity-aware cycling targets from FTP.
- [x] Hooks for running-threshold and swim-CSS targets.
- [x] MyWhoosh-aware indoor cycling venue selection.
- [x] EVO gym / treadmill venue support.
- [x] Post-workout feedback language.
- [~] Local Garmin activity sync is manual; scheduled collection is not active in the app.
- [~] Reconciliation modules exist; Garmin-to-HQ matching is not yet connected in the local app.
- [~] Feed the collected ledger back into the full daily coaching brief automatically.
- [ ] Use fresh calendar constraints in the same daily decision cycle without
  requiring manual context assembly.
- [ ] Produce one concise athlete-facing daily brief from the live runtime.

**Exit criteria:** the athlete can ask "what do I do today?" and receive a
complete answer based on fresh plan, training and life context without manually
copying activity data.

### Phase 3 — Accountability and life-aware coaching
**Target: November–December 2026**  
**Status: [~] adherence logic exists; [ ] full life-context loop**

Goal: behave more like a coach/project manager than a static training plan.

- [x] 14-day adherence summary.
- [x] Separate Plan A, modified sessions and misses.
- [x] No catch-up stacking after missed training.
- [x] Restore-rhythm logic when adherence falls.
- [~] Google Calendar capability and runtime policy defined.
- [ ] Read work meetings, travel and available time windows as planning
  constraints.
- [ ] Detect when a planned session no longer fits the real day.
- [ ] Suggest the smallest HQ-compatible change that preserves the week's key
  stimulus.
- [ ] Add proactive follow-up when an important session is repeatedly missed or
  modified.
- [ ] Distinguish time limitation, motivation, fatigue, illness/injury signals and
  scheduling conflict instead of treating every miss equally.

**Exit criteria:** training flows around real life without silently deleting key
stimuli or trying to compensate by overloading later days.

### Phase 4 — Adaptive personal coach
**Target: December 2026–February 2027**  
**Status: [~] conservative learning ledger exists; [ ] richer personal system identification**

Goal: learn how this athlete actually responds rather than merely applying
population-level rules.

- [x] Single exposure stays an observation.
- [x] Repeated evidence can become a candidate rule.
- [x] Stronger repeated evidence can become an established rule.
- [x] Athlete/HQ correction overrides inferred rules.
- [x] Personal rules cannot write the plan.
- [x] One-step progression proposals.
- [~] Materialize recent training frequency by discipline; reliable personal tolerance thresholds still need more data.
- [~] Materialize eight-week frequency/known-duration tolerance history; personal range inference waits for enough observations.
- [~] Automatically materialize dose-response profiles for workout type and exact dose signature; confidence grows only with real observations.
- [~] Automatically materialize spacing/sequence profiles with good, poor and UNKNOWN outcomes plus baseline comparison.
- [x] Data model can capture next-session quality and 24–48 h recovery without imputing missing values.
- [ ] Learn a reliable personal recovery-cost model from accumulated exposures.
- [ ] Detect recurring A -> B/C/MOVE patterns as plan-design feedback.
- [x] Recency weighting makes fresh 28/56/84/180-day evidence progressively more important than old history.
- [ ] Add explicit pattern invalidation when life context explains a bad response.

**Exit criteria:** the coach can state not only what usually works in training,
but what repeatedly works or fails for this athlete, with evidence count,
recency and confidence.

### Phase 5 — Objective testing and spot checks
**Target: January–March 2027**  
**Status: [~] benchmark scheduling exists; [ ] complete protocols and trend interpretation**

Goal: periodically test whether the training system is producing the adaptations
it is supposed to produce.

- [x] Benchmark freshness engine.
- [x] Benchmarks count as quality sessions.
- [x] Avoid stacking a benchmark on another quality day.
- [x] HQ approval required for placement.
- [ ] Dedicated MyWhoosh FTP/ramp-test protocol instead of using a normal
  threshold session as a proxy.
- [ ] Formal CSS test protocol and trend storage.
- [ ] Running 5 km / threshold benchmark protocol.
- [ ] Submaximal strength benchmark appropriate for endurance training.
- [ ] Durability checks for long run / long bike / mountain work.
- [ ] Compare benchmark change with training dose and recovery history.
- [ ] Trigger a course-review proposal when objective markers stagnate or regress
  despite adequate adherence.

**Exit criteria:** the coach periodically asks "are we actually improving?" and
can correct course from objective evidence rather than only subjective feel.

### Phase 6 — Triathlon performance coach
**Target: March–May 2027**  
**Status: [ ] planned**

Goal: move from separate sport coaching toward race-specific system performance.

- [ ] Brick-session taxonomy and progression families.
- [ ] Race-intensity bike-to-run durability analysis.
- [ ] Long-session fueling rehearsal tracking.
- [ ] Aero/TT-specific execution context.
- [ ] Open-water / swim-to-bike transition work.
- [ ] Race-specific power and pace sustainability.
- [ ] Transition and equipment rehearsal checklist.
- [ ] Use the planned 70.3 race around late May 2027 as an acceptance test of the
  whole coaching system.

**Exit criteria:** the 70.3 test produces a full evidence package for swim,
bike, run, pacing, fueling, transitions, recovery and plan accuracy.

### Phase 7 — Race execution system
**Target: June–August 2027**  
**Status: [ ] planned**

Goal: stop adding large experimental features and use a stable coach to execute
the Ironman build.

- [ ] Full Ironman race rehearsals.
- [ ] Race-power and race-pace validation.
- [ ] Fueling, fluid and sodium rehearsal history.
- [ ] Long-session durability and cardiac-drift monitoring where data supports it.
- [ ] Open-water and transition readiness.
- [ ] Equipment and contingency planning.
- [ ] Heat/weather adaptation inputs when relevant.
- [ ] Taper response monitoring.
- [ ] Race-week decision tree for normal, fatigued, travel-disrupted and
  illness/injury scenarios.
- [ ] Final Copenhagen race plan remains an HQ decision.

**Exit criteria:** by the final build, development effort shifts from "build the
coach" to "use the coach to execute the race".

### Phase 8 — Full performance coach
**Target: after August 2027**  
**Status: [ ] future**

Goal: generalize the proven coaching system beyond the Ironman build.

Potential scope:

- body-composition goals without compromising training quality;
- sleep and recovery behavior;
- strength and injury-resilience development;
- Backyard Ultra preparation;
- mountain / 2000 m summit durability;
- Norway end-to-end cycling preparation;
- changing work/travel stress;
- long-term multi-goal prioritization.

### Product progression

The intended product maturity can be summarized as:

~~~text
1. "I can analyse your training."
                    |
                    v
2. "I know what today's approved session is."
                    |
                    v
3. "I know why that is the right decision today."
                    |
                    v
4. "I know how you usually respond."
                    |
                    v
5. "I detect when we are drifting off course."
                    |
                    v
6. "I help HQ correct early and keep training aligned with real life."
~~~

### Development priorities

Build order should favor coaching value over impressive-looking features.

**Prioritize:** reliable data ingestion, plan reconciliation, accountability,
calendar constraints, personal response learning, objective benchmarks,
race-specific execution and explainability.

**Defer until the core earns them:** machine learning, large dashboards, a
standalone mobile app, hundreds of workout templates, opaque readiness scores,
automatic MyWhoosh control, or other features that look sophisticated without
improving the decision loop.

### Key validation milestones

- **Winter 2026/27:** personal learning period. Accumulate enough clean
  plan/actual/response history to identify real tolerance patterns.
- **Spring 2027:** validation period. Use benchmarks and race-specific sessions to
  challenge the coach's assumptions.
- **70.3 around late May 2027:** whole-system acceptance test.
- **June–August 2027:** stabilization and Ironman-specific execution rather than
  major architecture changes.
- **IRONMAN Copenhagen, 22 August 2027:** primary race-execution milestone.

Progress in this section should be updated whenever functionality moves from
planned to partial or complete. A feature is not complete merely because a
module exists; it is complete only when the intended end-to-end behavior is
tested and usable in the real coaching loop.

## Athlete learning foundation

v1.1 starts collecting the kind of longitudinal evidence later coaching versions
will need. It does **not** add ML. Instead it creates a clean, append-only record
of plan, execution, response, recovery, context, downstream outcome, benchmark
state, coach decision and explicit corrections.

The store deliberately keeps facts separate from interpretation so future
algorithms can recompute features without rewriting history. Missing data remains
missing, and calendar context is reduced before storage so meeting titles,
attendees and unrelated personal details are not copied into the training
database.

Routine easy sessions can remain silent after an initial baseline. Extra
questions are prioritized for key sessions, benchmarks, novel doses, hard work,
modified execution, low quality and pain signals.

See `docs/experience-foundation.md`, `docs/live-runtime-deployment.md` and `docs/personal-response-profile.md`.

## Run

~~~sh
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests -t . -v
ai-coach examples/synthetic_progress.json --audit history.sqlite
ai-coach-v1 examples/coach_context.json
ai-coach-experience --db athlete.sqlite export
ai-coach-profile --db athlete.sqlite --as-of 2026-10-01T12:00:00Z
~~~

## Core modules

- engine.py: deterministic plan → actual → response feedback.
- coach.py: daily premium-coach orchestration.
- workout_library.py: finite versioned workout/session library.
- progression.py: one-step HQ adaptation proposals.
- spot_checks.py: benchmark freshness and placement candidates.
- personalization.py: repeated-pattern learning without ML.
- tool_policy.py: Tredict / Calendar / venue capability boundary.
- audit.py: append-only feedback-evaluation history and replay.
- experience_store.py: append-only athlete experience/event history.
- experience_collector.py: normalized capture from HQ/Tredict/athlete/context sources.
- reconciliation.py: conservative HQ-plan ↔ actual-activity matching.
- sampling.py: adaptive low-noise subjective capture.
- sequences.py: positive/negative spacing evidence for later personalization.
- runtime_sync.py: stable live-ledger keys and connector-neutral reconciliation helpers.
- profile.py: deterministic Personal Response Profile materialization and evidence gates.
- profile_runtime.py: stable private-ledger profile-table contract.

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
