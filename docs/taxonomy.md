# Workout taxonomy 1.0

Workout identity, sport, stimulus and dose are separate fields. The table lists
suggested stimuli; a caller may supply multiple allowed stimuli to represent
the actual intent. Matching requires the same stimulus set, regardless of order.

| Workout type | Sport | Suggested stimuli |
| --- | --- | --- |
| RUN_EASY | RUN | AEROBIC |
| RUN_THRESHOLD | RUN | THRESHOLD |
| BIKE_AEROBIC | BIKE | AEROBIC |
| BIKE_SWEETSPOT | BIKE | SWEETSPOT |
| BIKE_THRESHOLD | BIKE | THRESHOLD |
| SWIM_TECHNIQUE | SWIM | TECHNIQUE, AEROBIC |
| SWIM_CSS | SWIM | THRESHOLD |
| STRENGTH_GENERAL | STRENGTH | STRENGTH |
| CROSSFIT | MIXED | STRENGTH, ANAEROBIC |

Dose includes total minutes, interval count, work minutes per interval, recovery
minutes between intervals, EASY/MODERATE/HARD intensity and optional volume
with an explicit M/KM/REPS/KG_REPS unit. With no intervals, count and work minutes
are zero. Interval work plus between-interval rest must fit total duration.

Execution is a reported category: A = as intended, B = modified/partial,
C = substantially unsuccessful. Quality is caller-normalized to [0,1], RPE and
pain to [0,10]. Duration is nonnegative for actual records (zero allows a
recorded non-execution); planned duration is strictly positive. Null is unknown.

v0.1 completion ratio uses duration only. Volume is retained for matching and
future features, but not used to claim strength-dose completion. The policy is
a conservative software baseline, not a validated sport-specific prescription.
