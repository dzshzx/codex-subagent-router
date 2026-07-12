# DeepSWE v1.1 routing evidence

Date retrieved: 2026-07-12

## Scope

This report records the benchmark evidence behind the ordered compute profiles
in this repository. It uses only first-party DataCurve artifacts and the
official DeepSWE repository. Benchmark results inform routing defaults; they do
not predict success, latency, or billing for an arbitrary private codebase.

## Snapshot

DeepSWE v1.1 contains 113 long-horizon software-engineering tasks. The live
leaderboard snapshot reports four runs for each of the 15 GPT-5.6
family/effort combinations.

- Leaderboard `generated_at`: `2026-07-09T20:23:14.264468+00:00`
- [`leaderboard-live.json`](https://deepswe.datacurve.ai/artifacts/v1.1/leaderboard-live.json)
  SHA-256: `bce76d9f89ff36b2ef17e56d04b63fad83d67049bd58e8b98684bfbc3c5fc773`
- [`trials.json`](https://deepswe.datacurve.ai/artifacts/v1.1/trials.json)
  SHA-256: `9f66c404d141fc18efc3d3c67e4f495e0b8b103109cb430eb5e436c9020e9794`
- [DeepSWE v1.1 methodology](https://deepswe.datacurve.ai/blog/deepswe-v1-1)
- [Official DeepSWE repository](https://github.com/datacurve-ai/deep-swe)

The leaderboard `mean_duration_seconds` exactly reproduces the mean agent-stage
duration for all 15 combinations. The main analysis instead uses mean complete
trial duration because it better approximates end-to-end waiting. Repeating the
calculation with agent-stage duration produces the same ordering and the same
winner at every quality gate used below.

## Method

Pass@1 is a quality gate and is not included in the resource score. Among
profiles that meet a gate, the analysis minimizes a 60% time and 40% historical
cost score:

```text
time_norm = (trial_duration - minimum_duration) /
            (maximum_duration - minimum_duration)
cost_norm = (mean_cost - minimum_cost) /
            (maximum_cost - minimum_cost)
resource_score = 100 * (0.60 * time_norm + 0.40 * cost_norm)
```

Normalization uses the complete 15-profile GPT-5.6 set. A lower score is
better. The score depends on the candidate set and snapshot, so raw values and
hashes must remain available when the policy is reassessed.

## Quality-gate winners

| Pass@1 gate | Lowest-resource profile | Pass@1 | Mean trial time | Mean cost | Score |
|---:|---|---:|---:|---:|---:|
| 35% | `gpt-5.6-terra / medium` | 35.11% | 5.60 min | $0.5832 | 11.73 |
| 45% | `gpt-5.6-sol / low` | 45.35% | 6.00 min | $1.0743 | 15.42 |
| 50% | `gpt-5.6-terra / high` | 53.76% | 7.85 min | $1.1344 | 22.02 |
| 60% | `gpt-5.6-sol / medium` | 61.06% | 8.72 min | $1.8620 | 28.49 |
| 65% | `gpt-5.6-sol / high` | 69.40% | 11.61 min | $3.4698 | 46.07 |
| 70% | `gpt-5.6-sol / xhigh` | 70.73% | 15.01 min | $4.7037 | 63.58 |
| 72% | `gpt-5.6-sol / max` | 72.67% | 20.51 min | $8.3864 | 100.00 |

These seven winners are exactly the five routine and two conditional routes in
the project policy.

## Relevant comparisons

- `sol/low` has a higher observed Pass@1 and a lower resource score than
  `luna/high`, so `luna/high` is not needed in the automatic route ladder.
- `sol/medium` is faster, cheaper, and slightly higher quality than
  `terra/xhigh` in this snapshot.
- `sol/high` reaches 69.40% Pass@1 without the large time and cost increases of
  `terra/max` or `sol/xhigh`.
- `sol/xhigh` adds 1.33 percentage points over `sol/high` at an average increase
  of 3.40 minutes and $1.2338.
- `sol/max` adds 1.93 percentage points over `sol/xhigh` at an average increase
  of 5.50 minutes and $3.6828. It is therefore conditional rather than routine.
- `luna/max` is deliberately not an automatic route. Keeping it out of the
  route ladder is a policy choice, not an unsupported-effort claim.

## Recalculation outline

For each GPT-5.6 leaderboard row, select scored trials with the matching config,
average `trial_duration_seconds`, calculate the min-max score above, then choose
the lowest-scoring profile at each quality gate. Use full-precision values from
the JSON artifacts rather than the rounded display values in this report.

## Limits

- Provider load and host performance make historical duration unstable.
- Artifact cost is a historical aggregate, not a future price guarantee.
- DeepSWE Pass@1 is not the success probability for this repository.
- Attempt counts vary slightly between profiles, and this policy does not model
  confidence intervals.
- Any leaderboard or candidate-set change requires a new versioned analysis;
  the existing policy must not silently follow a mutable live artifact.
