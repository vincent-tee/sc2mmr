# SPEC: Same-roster switching test of a captain effect (Stephan)

Status: FROZEN pre-registration. Written 2026-09-15, before any treatment-effect
coefficient was computed. Operationalizes section 7 of
`docs/reviews/2026-09-15-methodology-audit-and-coordination-plan.md`.

Feasibility inputs (measured 2026-09-15 on local DB only, before this freeze,
via `backend/scripts/captain_effect_coverage.py` -- this is design/coverage
information, not an effect estimate, so inspecting it before freezing is
consistent with the source document's own recommended order):

- Local DB chosen as canonical. The production snapshot is not an independent
  sample of this data (audit doc #1) and is not used for this analysis.
- Stephan: 57 receiver x session x exact-roster strata with complete
  `army_value_killed`/`army_value_lost` metric rows for the receiver, across
  62 raw switching sessions (5 sessions drop for incomplete metrics).
- DragonKing (this DB's identity for the doc's "ShadowDragon" candidate): 29
  metric-complete strata. Secondary candidate only; testing it formally
  requires a multiplicity adjustment relative to Stephan, per the source doc.
- Y (receiver appearances, unconditional on captain) has total_sd = 1.342,
  of which between-session variance is only ~1.0% of total (0.0189 / 1.801).
  Session clustering barely inflates variance for THIS outcome -- still use
  session-block resampling for inference (design-based correctness), but do
  not expect it to change conclusions much versus naive iid resampling.

## Hypothesis

Stephan's presence on a teammate's side improves that receiver's combat
resource exchange (Y, defined below) beyond what the receiver's own
chronological skill and the pre-match team/opponent strength already predict.
Mechanism: a captain-style effect on ally combat coordination or target
prioritization, distinct from the captain's own play. This is an associational
retrospective claim, not a causal one -- team assignment is not randomized.

## Primary candidate

Stephan only. DragonKing is a documented secondary candidate; if tested, its
p-value/CI must be reported alongside a multiplicity correction and it must
not be substituted for Stephan post hoc.

## Endpoint

`Y = log(1 + army_value_killed) - log(1 + army_value_lost)`, computed on the
RECEIVER's own `player_match_metrics` row. The captain's own row is excluded
from every receiver-side computation. Standardize using the training-fold
(session <= cutoff, defined below) mean/SD only.

Not used as primary: `overall_impact` (embeds hand-weighted teamwork scores --
circular for this question, audit doc #8), current game's win (a plausible
mediator, not a control), current-live `players.mu`/`matches.predicted_*_win_prob`
(post-hoc, not available pre-match in a chronological sense).

## Design

Within receiver x session x exact-roster strata (same session, identical
19-vs-... no, identical full participant set for that match), compare the
receiver's Y when Stephan is on their team ("with") vs on the opposing team
("against"). This bundles teammate-benefit and opponent-suppression into one
"same-side" association -- see Estimand below.

## Controls

- Pre-match teammate strength EXCLUDING the captain: mean chronological mu of
  the receiver's other teammates (rebuilt via `app.rating_policy`, not current
  `players.mu`).
- Pre-match opponent strength EXCLUDING the captain if the captain is on the
  opposing side: mean chronological mu of opponents other than the captain.
- Receiver's own pre-match mu, sigma.
- Race (receiver's own), map_name, game order within session (match index).
- Prior captain exposure count (has this receiver played with/against Stephan
  before this match, chronologically).

These controls exclude the captain from any aggregate the captain would
mechanically dominate (advisor-flagged crux: including the captain in
teammate-strength control partials out the very effect being measured, since
with-vs-against is what moves the captain in/out of that aggregate).

## Cohort exclusions

- Receiver must have a non-null `army_value_killed` and `army_value_lost` row
  (excludes unparsed-metric matches; see audit doc #8 on synthetic-fallback
  risk -- do not assume zero values are missing without provenance, but do
  require non-null for this endpoint).
- Receiver-race must be stable across the compared strata (if a receiver
  changed race between the "with" and "against" occurrence in the same
  roster/session, exclude that stratum from the primary comparison; log it).
- Strata with only one state ("with" or "against" but not both) are not part
  of the primary within-stratum comparison.

## Practical threshold (decision proposal, not derived from data)

0.2 standardized-residual SD, exactly as proposed in the source document.
This number was chosen before looking at any fitted coefficient.

## Folds and inference

- This is a within-stratum retrospective association analysis, not a
  predictive-holdout claim. It does NOT use chronological train/test splitting
  for the coefficient itself (there are only 57 strata; splitting further
  destroys power). The separate predictive question ("does this improve
  future outcome prediction") is the distinct, deferred gate described below.
- Inference: session-block resampling (resample sessions with replacement,
  keep all rows from a resampled session together), 3000 resamples, seed 42.
- Stability checks required before any positive verdict: leave-one-session-out
  and leave-one-stratum-out re-fits, reported explicitly, with a note on
  whether one session or one roster drives the point estimate.
- No player-label permutation test (historical assignment probabilities are
  unknown; audit doc #7 explicitly rules this out as a substitute for
  randomization).

## Kill / promotion criteria (fixed before fitting)

- Upper bound of the 95% session-block CI on the receiver association is
  below 0.2 SD: RULE OUT an effect of that size for this endpoint/population
  under these assumptions. Not proof of exactly zero.
- CI includes both 0 and 0.2 SD: INCONCLUSIVE. No promotion, no "trending"
  language.
- Point estimate positive, practically sized (>=0.2 SD), CI excludes 0, AND
  stable under leave-one-session-out / leave-one-stratum-out (no single
  session or stratum flips the sign or collapses the CI): SUPPORTED
  retrospective association. Still not causal, still not a balancing change
  by itself (see the deferred predictive gate).
- Any of: cohort collapses below a usable stratum count after exclusions,
  severe collinearity between the with/against indicator and a control
  (e.g. near-total confounding of captain presence with one specific
  opponent strength band), or metric-provenance concerns for the specific
  receivers/matches involved: NOT IDENTIFIABLE. Report as such; do not report
  a zero effect in this case.

## Required BEFORE fitting the real coefficient

A power/precision simulation on the actual 57-stratum design, injecting
synthetic effects of exactly 0 and exactly 0.2 SD with session-correlated
noise calibrated to the real Y variance decomposition measured above (not
to the treatment contrast itself). This estimates:
  (a) the false-positive rate of the CI-excludes-zero rule at true effect 0,
  (b) the probability the CI's upper bound is below 0.2 at true effect 0
      (correct "ruled out" behavior),
  (c) the attainable CI width / detection probability at true effect 0.2.
If (c) shows the design cannot plausibly distinguish 0 from 0.2 SD at this
stratum count, the correct action is to STOP and report the power limitation
-- not to fit the real data and report whatever comes out. That decision is
made from the simulation output alone, before the real fit runs.

## Deferred, separate gate (not part of this spec's promotion decision)

Whether a captain-presence x teammate-need interaction improves chronological
out-of-sample log loss versus a baseline with only a captain main effect.
Explicitly out of scope here per the source document (line 242: "This stage
has not been implemented"); only pursued if this spec's primary comparison
produces a supported, stable, practically-sized association.

## Result (2026-09-15, measured after this freeze and after the power sim)

Power sim (`captain_effect_power_sim.py`, 70 metric-complete strata, 227
receiver-pairs, same-session noise model): at true effect 0, ~4% false-positive
rate and ~58% correct rule-out rate below 0.2 SD; at true effect 0.2 SD, ~57%
detection probability. Moderate power -- proceeding to fit was justified, but
a null result should read as "did not detect," not "ruled out."

Real fit (`captain_effect_fit.py`): 201 qualifying receiver x session x roster
pairs (26 excluded for a race change between the two occurrences), 57
sessions, 23 distinct receivers. Point estimate +0.169 raw units (+0.126 SD).
Session-block bootstrap 95% CI (raw): [-0.133, +0.466] = SD units
[-0.099, +0.347]. **Verdict: INCONCLUSIVE (CI includes zero)**, consistent
with the measured power. The point estimate itself was stable and
same-signed under leave-one-session-out (range [+0.109, +0.263]) and
leave-one-receiver-out (range [+0.132, +0.251]) -- it is not an artifact of
one session or one player -- but the sampling noise is too large at this
stratum count to distinguish it from zero.

**Do not re-run this exact fit expecting a different verdict without either
more switching sessions or a lower-variance endpoint.** DragonKing was not
tested; if tested later, apply a multiplicity correction against this result.

**IMPORTANT caveat added after this result** (see
`docs/reviews/2026-09-15-replay-metrics-review.md`, "Metric definitions
currently drift" #4): `PlayerStatsEvent.resources_killed/resources_lost`
aggregate army, economy, AND technology value. Fields named `army_value_*`
can therefore include non-army (economic/tech) losses, not pure combat
exchange. This endpoint's construct validity -- whether it actually measures
"combat resource exchange" as intended -- has NOT been verified against that
finding. This is a reason for additional caution beyond the wide CI, not yet
a demonstrated contamination of these specific rows. Before any further
investment in this design, check whether `army_value_killed`/`army_value_lost`
in this dataset's rows are dominated by combat value or include meaningful
non-army losses.

## What this spec does not authorize

No production, rating, or database changes. No balancing-logic change. This
is a read-only retrospective analysis against `backend/data/sc2mmr.db`.
