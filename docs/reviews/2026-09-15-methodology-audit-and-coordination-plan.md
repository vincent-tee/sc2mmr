# Methodology audit and next coordination experiment

Date: 2026-09-15. Written at the owner's request to preserve an adversarial review for subsequent models.

## Read this first

This document corrects material claims in [the earlier handoff](2026-09-15-big-picture-handoff.md). The earlier document's instructions to treat conclusions as settled must not override the owner's explicit request to audit them. This audit is also reviewable evidence, not a new source of unquestionable conclusions.

**The strongest finding is that the probability model benefited from recalibration. The evidence does not establish the claimed skill-dependent mechanism. The two databases are not independent. Neither null result rules out coordination generally.**

No production changes, rating changes, database repairs, or deployments were performed in this audit. The proposed coordination experiment has NOT been run. Only its data availability and switching opportunities were inspected. Do not turn the proposed design into a reported positive result.

The owner asked for two things: (1) skeptical validation of the win-probability change, two null results, composite objective, and player scan; (2) a concrete falsifiable next coordination experiment using existing data. The owner then asked to document this work for other models before usage ran out.

## Evidence and reproduction

- Local database: `backend/data/sc2mmr.db`.
- Production **snapshot**, not a fresh live pull: `/home/vtee/.claude/jobs/969106c5/tmp/prod-before.db`.
- Read-only audit script: [backend/scripts/handoff_methodology_audit.py](../../backend/scripts/handoff_methodology_audit.py).
- Saved numerical output: [artifacts/2026-09-15-methodology-audit-output.txt](artifacts/2026-09-15-methodology-audit-output.txt).
- Original evaluations: `backend/scripts/skill_dependent_variance_eval.py`, `uncertainty_aware_balance_eval.py`, `synergy_residual_eval.py`, `balancer_objective_shootout.py`, `all_players_residual_scan.py`, `named_player_effect_eval.py`.
- Shared data loader/session assignment: `backend/scripts/walkforward_session_eval.py`.
- Shared rating code: `backend/app/rating_policy.py`; settings in `backend/app/config.py`.

Run with the backend dependencies installed:

```sh
python backend/scripts/handoff_methodology_audit.py --prod /path/to/prod-before.db
```

The helper reproduces continuous calibration fits, paired session-bootstrap comparisons, the alternative player correlation, usable-match overlap, metric coverage, and within-session switching counts. It does not reproduce every separate SQL inspection listed below or run the coordination study. It imports current code/settings: preserve the source and settings alongside any future results. A changed result after a policy change is not automatically a contradiction.

During this audit the policy was `trueskill-decay-v3`, prediction variance scale 11, TrueSkill beta 5, tau 0.25, initial mu 25, initial sigma 8.333, draw probability 0, and session gap 4 hours. The bootstrap in the helper uses 3,000 session resamples; the original formula script uses 1,000. Small CI differences are expected.

The original session's own narrative in `/home/vtee/.claude/jobs/969106c5/timeline.jsonl` acknowledges that the motivating correlation was discovered using the full data before the 75/25 formula evaluation. This establishes hypothesis-selection contamination, even though per-match ratings were constructed chronologically.

## 1. Dataset independence: false

Direct SQL comparisons of both `matches.replay_hash` and `matches.game_fingerprint` found:

| Quantity | Local | Production snapshot | Shared |
|---|---:|---:|---:|
| All matches | 860 | 874 | 860 |
| Usable evaluation matches | 837 | 851 | 837 |
| Training matches | 565 | 584 | 565 |
| Test matches | 272 | 267 | 253 |

Production adds only 14 games across two sessions. All local matches are in production. Nineteen local test matches become production training matches because the percentile split moves. Local test begins 2024-10-13; production test begins 2024-11-03. Both tests have 26 sessions.

This does not by itself introduce future outcomes into a single chronological run. It invalidates the independent-replication claim. Cross-snapshot agreement is principally a sensitivity check to a small extension and the DragonKing/ShadowDragon identity merge. Do not combine the two tests as independent samples or multiply their evidence.

To verify raw overlap, open each DB with `sqlite3.connect('file:'+path+'?mode=ro', uri=True)` and intersect sets from `SELECT replay_hash FROM matches WHERE replay_hash IS NOT NULL`; repeat with `game_fingerprint`. Use replay identifiers rather than player names or match IDs.

## 2. Win probability: improvement reproduced, mechanism not validated

### The k=11 optimum is not suspicious rounding

The grid brackets a real interior training-loss minimum. Continuous optimization gives local k=10.67723 and production k=10.61046. Local training losses at k=10,11,12 are 0.6237338, 0.6236896, 0.6238444. Loss rises again at much larger k. Calling 11 a "true out-of-sample optimum" is incorrect: it is an integer-grid training optimum tested on later matches.

Original-script rerun:

| Held-out log loss | Local n=272 | Production n=267 |
|---|---:|---:|
| Old formula, beta=5 | 0.7515 | 0.7641 |
| New formula, k=11 | 0.6591 | 0.6678 |
| Improvement | 0.0924 | 0.0963 |
| Session-bootstrap 95% CI | [0.0402, 0.1507] | [0.0415, 0.1532] |

### The correlation validation checks the wrong quantity

`skill_dependent_variance_eval.mu_residual_correlation()` correlates average mu of ALL participants in each match with the outcome residual signed toward team 1. The motivating analysis was about each PLAYER'S mu and that PLAYER'S team's residual.

Swapping team labels changes the sign of the implemented residual but leaves the average mu unchanged. The implemented statistic is not a valid test that strong players stopped being underpredicted. Its baseline was already approximately zero: local +0.007, production +0.011.

An exploratory, more relevant held-out diagnostic uses each player's mean pre-match mu and mean signed residual, requiring at least ten held-out appearances (19 players in each snapshot):

| Correlation | Old formula | k=11 |
|---|---:|---:|
| Local | 0.405 | 0.539 |
| Production | 0.249 | 0.501 |

This does not prove the correlation increased in a population: player observations are dependent, the threshold is an audit diagnostic, and no formal interval was calculated. It DOES refute the assertion that the supplied validation established elimination of the original pattern. Do not present this as an exact reproduction of the earlier full-history correlation, which used a different analysis.

### Missing control: ordinary recalibration

Hold the chronological ratings fixed. Fit each prediction-only parameter on the same training split:

| Model | Local test loss | Production test loss |
|---|---:|---:|
| Continuously fitted k | 0.659559 | 0.668405 |
| Old formula with fitted prediction beta | 0.656178 | 0.665771 |
| Old total variance multiplied by one fitted factor | 0.657116 | 0.666599 |

Fitted prediction betas: 13.5409 and 13.3696. Variance multipliers: 4.5057 and 4.4334. These do NOT change beta in `rate_teams`.

The k model's log-loss improvement over fitted beta is negative: local -0.00338, CI [-0.01449, +0.00414]; production -0.00263, CI [-0.01365, +0.00533]. Neither distinguishes the models. Brier scores also improve substantially over the old beta=5 baseline; see saved output.

Interpretation: simple correction of overconfidence explains the gain at least as well as the new mechanism in these retrospective diagnostics. These extra comparisons were performed on an already inspected test set, so they are NOT a validated replacement winner. Do not deploy fitted beta from this audit.

### Selection leakage and revised verdict

Ratings are advanced after predicting each match; no direct future-outcome leakage was found in that chronological pass. Updating state using earlier test matches is legitimate online evaluation. But the formula was motivated by full-history results, and the same later data supported several experiments. The holdout was not untouched by hypothesis selection. Session-bootstrap intervals condition on the chosen model and training fit; they do not correct this research process or all longer-term dependence.

Keep: substantial retrospective evidence for better probability calibration than the old fixed beta=5 formula. Withdraw: independent replication, precise scientific significance of 11, validated sigma-dependent mechanism, and elimination of the original correlation. The audit is not authorization to change live ratings or predictions.

## 3. Uncertainty-aware balancing: wrong decision and baseline

The script selects the closest quarter of historical games under each metric, then compares pooled favored-side win rates. It does not observe outcomes under alternative splits of the same roster. Its point-estimate baseline is summed-mu difference, NOT default display-MMR difference. Display MMR includes a sigma penalty.

For a fixed two-team roster, total sigma-squared S and total player count n are constant across splits. Under the current formula, probability closeness is monotonic in absolute delta-mu. Ordinary two-team TrueSkill quality has the form:

`sqrt(n*beta^2 / (n*beta^2 + S)) * exp(-delta_mu^2 / (2*(n*beta^2 + S)))`.

It therefore induces the same split ordering by absolute delta-mu. These uncertainty terms change comparisons across different rosters, not the ordering of splits within a fixed roster under these assumptions. This is another reason the historical quartile comparison cannot establish the claimed balancing improvement.

Local rerun: favored-side win rate 55.8% in 206 decided mu-selected games, versus 56.9% in 209 quality-selected games. Bootstrap deviation-gap CI [-6.7,+3.4] percentage points. This is inconclusive, not an equivalence result. Pooling can also cancel opposite subgroup miscalibration. The selected-quarter threshold uses the whole retrospective sample.

Verdict: this ranking diagnostic showed no clear advantage. It did not establish that uncertainty-aware balancing is generally inferior.

## 4. Synergy: the tested feature is not a conditional chemistry estimator

The feature is pair win rate minus the average of each member's marginal individual win rates. Those marginal rates are not expected outcomes conditional on teammates and opponents, and include the pair's own shared games.

If two players always play together, all three win rates are identical and the feature is exactly zero regardless of any true coordination advantage. In that case separation is not identifiable; zero is not evidence of no effect.

Further limitations: hard small-sample thresholds; noisy historical estimates; averaging all eligible pairs dilutes a particular directed relationship; candidate sklearn regularization differs from the hand-fit baseline; stricter thresholds reduce power as well as noise. A CI crossing zero is not an equivalence test.

Current-policy local rerun: train 565/test 272; every test match has at least one qualifying pair. Baseline loss 0.6586, candidate 0.6580, gain about 0.0006 with CI [-0.0027,+0.0038]. The older session reported slightly different values before the shared probability policy changed. This illustrates why code/settings snapshots matter.

Verdict: do not deploy this particular feature. Do not claim teammate chemistry or leadership was ruled out.

## 5. Composite objective: arithmetic tradeoff, not observed outcome improvement

The shootout feeds historical rosters to today's optimizer using CURRENT player ratings. It scores each proposed split using the same internal quantities the objectives optimize. It never observes outcomes for the proposed counterfactual splits.

The default minimizes MMR difference by construction. Requiring a challenger to be no worse on that metric restricts acceptable alternatives largely to minimum-MMR ties. That is a legitimate product constraint but not a neutral empirical contest.

Local rerun, 837 historical roster occurrences:

- Mean absolute predicted probability distance: default 0.0704, composite 0.0557.
- Mean MMR difference: default 356.6, composite 505.4.
- Composite-minus-default intervals: probability distance [-0.0169,-0.0126]; rating difference [+132.7,+166.8].

The 20 most recent roster occurrences show the same direction. Match bootstrap treats repeated roster decisions as independent observations and understates uncertainty for generalization. Present-day ratings are acceptable for describing today's optimizer on those rosters, not for historical prediction validation.

Verdict: retaining default respected the stated promotion rule. Neither objective's actual fairness advantage has been established. The reported tradeoff is among internal scores.

## 6. Player scan: no multiplicity correction, stale named lead

`all_players_residual_scan.py` runs separate ordinary 95% bootstrap intervals and prints a multiple-testing caveat. It applies NO correction. Sixteen players currently qualify at >=50 games, so roughly 0.8 nominal false positives would be expected under valid null tests. "Survives in both databases" is not replication because the histories overlap.

The underlying `bootstrap_mean_ci` resamples games independently, not sessions. Outcomes create positive and negative dependence between player residuals through team membership. The population-weighted mean residual is also not a useful general calibration certificate: for equal teams, all-player signed residuals cancel algebraically before cohort filtering.

For a confirmatory scan, construct valid session-level tests and use Holm correction, which permits arbitrary dependence. A correctly constructed joint maximum-statistic bootstrap can instead provide simultaneous intervals while retaining all players' contributions from each session. Do not shuffle player labels or assume historical assignments were random. A joint bootstrap must be centered under the appropriate null and its model-fitting uncertainty considered. An exploratory ranking may report unadjusted intervals if no discovery claim follows.

Current-policy scan:

- Local DragonKing: n=387, mean +0.008, interval [-0.039,+0.055].
- Production ShadowDragon: n=401, mean +0.005, interval [-0.042,+0.050].
- Both rank fifth of 16 by mean residual. The earlier +0.029/highest-player statement is stale under current policy.
- ChrisO is the only nominal interval excluding zero in both snapshots; this is not an adjusted discovery.

## 7. Proposed next experiment: same receiver, same session, same roster

### What the experiment can establish

A constant leadership contribution can be absorbed into an additive rating. A positive team residual is neither necessary nor sufficient for leadership. To identify what an additive model misses, investigate whether benefit depends on recipient or team composition.

Primary hypothesis: Stephan's presence on another player's team improves that receiver's combat resource exchange beyond their usual performance and pre-match composition/strength. Stephan is the primary candidate because a captain hypothesis preceded the residual scan. ShadowDragon is secondary; testing both formally requires adjustment.

This is a proposed retrospective observational design. Its effect estimates have NOT been inspected. It cannot prove verbal direction or communication occurred.

### Measured feasibility

In the production snapshot, before metric restrictions:

| Candidate | Present matches | Present sessions | Sessions with receiver switching sides | Exact-roster switching sessions | Receiver x session x exact-roster switching strata |
|---|---:|---:|---:|---:|---:|
| Stephan | 722 | 93 | 83 | 63 | 270 |
| ShadowDragon | 401 | 44 | 40 | 31 | 144 |

The audit helper reproduces the non-exact-roster exposure counts. Exact-roster counts came from a separate structural check: group usable games by `(session_id, tuple(sorted(all_player_ids)))`; for each noncaptain receiver, collect whether their team equals the captain's team; retain groups containing both states. Count unique sessions and receiver/group pairs. These are opportunities, not independent samples.

Requiring merely that a match have any joined metric row reduces exact-roster switching sessions to 59 for Stephan and 30 for ShadowDragon. This is NOT a complete-case check for the actual receiver: recheck receiver-specific coverage before fitting.

### Tables, joins, outcome

- `matches`: `id`, `played_at`, `map_name`, `game_mode`, `duration_seconds`, replay identifiers.
- `match_players`: `id`, `match_id`, `player_id`, `team_number`, `race`, `won`.
- `player_match_metrics`: `match_player_id`, `army_value_killed`, `army_value_lost`.
- Join metrics through `player_match_metrics.match_player_id = match_players.id`, then matches through `match_players.match_id = matches.id`.
- Rebuild mu/sigma from strictly earlier outcomes through shared rating policy. Do not use current `players.mu` or stale historical `matches.predicted_team1_win_prob` as pre-match controls.

Primary receiver outcome:

`Y = log(1 + army_value_killed) - log(1 + army_value_lost)`.

Exclude the captain's own row. Standardize with training-only residual scale. This measures resource exchange, not complete skill or actual damage. Avoid `overall_impact` as the primary endpoint because it embeds hand-weighted teamwork scores.

Production has 4,906 joined metric rows over 803 matches before usable-match restrictions. Nonzero killed/lost values occur in 4,811/4,801 rows. Zeros are not automatically missing: distinguish legitimate zeros from unparsed defaults using parser provenance and consistency checks.

### Model, identification, and confounding

Compare the same receiver within session and exact roster when assigned with versus against the captain. Use receiver-by-session-by-roster fixed effects for the retrospective association. Control pre-match team and opponent strength, race composition, map, game order, earlier outcomes, and prior captain exposure. Restrict the primary comparison to stable receiver race and adequate overlap in pre-match strength. Inspect collinearity and effective assignment variation before claiming an identified coefficient.

Do not condition the primary model on the current game's win, captain's realized combat performance, or other downstream outcomes. These may mediate the effect. Duration normalization can be a sensitivity analysis, but duration itself may be affected by team assignment.

With versus against bundles teammate benefit and opponent suppression. In captain-present fixed-roster games, these exposures are complementary. Separate teammate and opponent coefficients require captain-absent variation with adequate overlap. Otherwise label the estimand a same-side association.

Team assignment may respond to tilt, perceived form, prior losses, and social preferences. Session/receiver restrictions reduce some confounds but do not randomize assignments. Coaching may persist into subsequent games, contaminating the nominal control condition. Model/order checks and sensitivity analysis are required, not a claim of causal proof.

### Validation and kill criteria

Freeze candidate, endpoint, controls, cohort exclusions, practical threshold, and folds BEFORE looking at coefficients.

1. Use expanding chronological outer folds for transferable prediction; estimate transforms and nuisance models on earlier sessions only. Never use held-out receiver/session fixed-effect estimates as though available pregame. The within-stratum association analysis and predictive validation are distinct estimands and must be reported separately.
2. Keep all observations from the same game/session together for inference. Refit the analysis in session resamples; assess longer blocks for persistent dependence. Thousands of receiver rows are not thousands of independent games.
3. Examine leave-one-receiver-out and leave-one-session-out stability. Report whether one pair drives the estimate.
4. Use next-game captain assignment as a diagnostic predictor of current performance after accounting for current assignment. A lead association raises selection/carryover concerns; it is not an automatic exact negative-control test.
5. No arbitrary team-label permutation presented as an exact randomization test. Historical assignment probabilities are unknown.
6. Predeclare a practical receiver effect, proposed here as 0.2 training residual SD. This threshold is a decision proposal, NOT derived from observed effect sizes.

Decision categories:

- Upper CI below 0.2 SD: rule out an effect of that size for this endpoint/population under the analysis assumptions.
- CI includes both zero and 0.2: inconclusive; no promotion.
- A positive practically sized effect with chronological stability and no single-receiver dependence: supported retrospective teammate-performance association. Explicitly distinguish evidence for any positive effect from evidence that the true effect exceeds 0.2.
- Bad metric provenance, insufficient assignment overlap, or severe collinearity: not identifiable; do not report zero effect.

Before committing to full fitting, simulate effects of 0 and 0.2 on the actual exposure design with session-correlated noise to estimate false-positive behavior and attainable precision. This uses existing data/design; do not report invented power based only on player-row count.

### Separate gate: does nonadditivity improve outcome prediction?

Even a real receiver effect might already be captured in the captain's mu. Test one structured interaction, not all possible triples:

- Baseline: calibrated chronological rating predictor plus a signed captain-presence main effect.
- Candidate: same baseline plus signed captain-presence x teammate-need interaction.
- Define teammate need continuously from pre-match teammate mu with training-only centering/normalization. Fix the definition before testing. Exclude the captain from their own teammate aggregate.
- Ask whether the captain's benefit increases with teammate need beyond the captain main effect. Control comparable strength/composition effects in the baseline.
- Fit on earlier sessions and compare log loss on strictly later sessions. Use paired session inference. No prediction change if the incremental gain fails the frozen promotion criterion; a suggested minimum useful gain must be selected before estimating it.

This stage has not been implemented. Positive receiver association without incremental predictive value is not grounds to change balancing. A positive predictive interaction without clean mechanism evidence is a useful association, not proven leadership.

### Why not raw within-team variance or unrestricted triples?

Leadership may reduce weaker players' failures OR enable specialization that increases score dispersion. Lower raw within-team variance is not a necessary signature. If studied secondarily, use receiver-adjusted residuals, remove the captain's own performance, account for team size, and predeclare the direction/endpoint. Do not select whichever of mean, variance, lower tail, or synchronization looks favorable after inspection.

There are 969 possible triples among 19 players. Unrestricted triple coefficients against roughly 850 games are an invitation to unstable fitting. A one-parameter composition interaction is a much more falsifiable next step. Generalization across receivers distinguishes broad captain effects from one special relationship.

## 8. Metric provenance traps

`backend/app/advanced_parser.py` can fabricate equal-value damage events every 30 seconds from second 60 when killed army value is positive but no timeline events were extracted. It can also scale timeline values using total killed value. Therefore timing synchronization and early-game damage cannot be treated as independent raw observations solely because the JSON exists.

A separate inspection found ZERO exact matches to that full synthetic fingerprint in this production snapshot. Do not falsely claim contamination was observed. The concern is an implemented fallback and incomplete provenance, not demonstrated corruption of these rows. Recheck actual provenance if choosing a timing endpoint.

Both parser paths assign `damage_dealt` from army value killed. `overall_impact` includes team-fight participation and other derived scores. A test of coordination using that composite risks circular measurement.

The snapshot still has 287 orphan metric rows. Inner joins exclude these, but this is an old snapshot: do not infer current live repair status. Do not run a repair as part of this review.

## 9. Literature used to inform the design

- [Kenny: Social Relations Model](https://davidakenny.net/srm/soremo.htm): distinguishes actor, partner, and directed relationship effects. This motivates separating own performance from effects on others; the game data are not a textbook dyadic round robin.
- [Kenny and Garcia (2012), group actor-partner model](https://scholarworks.smith.edu/psy_facpubs/85/): extends composition analysis to group settings. This informs the proposed adaptation, not a guarantee that its assumptions hold here.
- [Aronow and Samii, interference framework](https://arxiv.org/abs/1305.6156): emphasizes assignment mechanisms and exposure definitions. Their randomized framework does not grant causal identification to these nonrandom historical teams.

## 10. Instructions for the next reviewer

1. Read this and the original handoff fully. Check source and saved outputs; neither document's confidence is evidence.
2. Reproduce only the disputed checks needed for your task. Label changes in policy, cohort, metric, or bootstrap explicitly.
3. Never call these snapshots independent. Never call a nonsignificant CI proof of no effect.
4. Preserve the distinction between probability calibration, additive rating ability, receiver-performance association, and incremental nonadditive prediction. They answer different questions.
5. Freeze a coordination protocol and inspect support/provenance before effect estimation. Do not search all players/metrics until something passes.
6. Report baselines, unique games, sessions, switching strata, effect sizes, and intervals. Include inconclusive and non-identifiable results.
7. No deployment or production mutation is authorized by this review. Follow the existing explicit sign-off requirements for formula changes and production actions.

Recommended next action: verify receiver-specific metric quality and overlap for the proposed same-roster switching design, then freeze the exact analysis and power/precision check. Do not promote another model based on the already reused calibration holdout.
