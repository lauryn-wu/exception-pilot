# Target-record availability: selected-case diagnostic

Status: **replay_gate_failed_stop**

10/40 returned; 10 valid; 0 unscorable.

Post-hoc diagnostic: 10 cases selected from 9 parent worlds. This is not an independent confirmation set.

Results describe this selected subset. They cannot establish prevalence, an internal mechanism, or novelty. Do not treat the 40 calls as 40 independent observations.

## Replay feasibility check

Decision: **stop**. Exact parent-answer matches: 7/10; scorable: 10; invalid: 0; missing: 0.

All 10 original continuations must be scorable; at least 8 must exactly match their saved parent answers.
Fixed practical feasibility threshold, not statistical significance or evidence of a mechanism.

## Paired contrasts

Positive values favor the first arm. The primary contrast is available minus unavailable. Cases are averaged within each parent world before giving each complete world equal weight.

| Contrast | World-weighted mean | Descriptive 95% interval | Complete worlds | Case-weighted mean |
|---|---:|---|---:|---:|
| available_minus_unavailable | — | — | 0/9 | — |
| available_minus_original | — | — | 0/9 | — |
| gold_minus_available | — | — | 0/9 | — |
| unavailable_minus_original | — | — | 0/9 | — |

10,000 whole-world bootstrap resamples, seed 981723, descriptive unadjusted 95% intervals only. Degenerate intervals do not establish certainty or equivalence. Full-plan unscorable bounds are point-estimate bounds, not confidence intervals.

Each contrast excludes a world if any selected case lacks a scorable answer in either required arm. Case-weighted estimates use all scorable pairs. The JSON also records exclusions, paired improvement/worsening counts, and full-plan bounds after all planned responses have returned.

## Arm counts

| Arm | Valid / planned | Correct | Case-weighted accuracy | Pattern choices |
|---|---:|---:|---:|---:|
| original | 10/10 | 4 | 0.400 | 6 |
| unavailable | 0/10 | 0 | — | 0 |
| available | 0/10 | 0 | — | 0 |
| gold | 0/10 | 0 | — | 0 |

## All selected cases

| Case | Gold | Parent answer | Replay | Unavailable | Available | Gold continuation |
|---|---|---|---|---|---|---|
| ex-list-000/record_2/cot | C | C | C | pending | pending | pending |
| ex-list-001/record_2/cot | A | B | A | pending | pending | pending |
| ex-list-005/record_2/cot | C | B | B | pending | pending | pending |
| ex-list-006/record_2/cot | A | C | C | pending | pending | pending |
| ex-list-008/record_1/cot | C | B | B | pending | pending | pending |
| ex-list-010/record_2/cot | B | A | B | pending | pending | pending |
| ex-list-010/record_1/cot | A | A | A | pending | pending | pending |
| ex-list-014/record_2/cot | C | B | A | pending | pending | pending |
| ex-list-018/record_1/cot | C | B | B | pending | pending | pending |
| ex-list-020/record_2/cot | C | B | B | pending | pending | pending |

The saved parent answer is descriptive; causal arm comparisons use the new original replay. A replay feasibility pass only permits the fixed diagnostic to continue. It is not a scientific finding.
