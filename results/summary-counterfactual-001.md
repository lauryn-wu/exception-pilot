# Verified-facts counterfactual diagnostic

Model: `gpt-4o-2024-08-06`; protocol: `verified-facts-counterfactual-v1`.

Valid: 160/160; invalid: 0; provider errors: 0; attempts: 160.

Complete independent list pairs: 20 (not 160 independent samples).

Separate exploratory study designed after the original stage-1 stop decision. The 15 pp rule is an investment screen, not a significance test. A positive interaction alone does not establish an internal mechanism or novelty. A stop decision does not establish the absence of smaller effects.

Screen: **review_for_confirmation**.

All queried target labels are identical across the two backgrounds. Both backgrounds have 20% exceptions.

| Response | Supporting pattern | Conflicting pattern | Conflict penalty |
|---|---:|---:|---:|
| direct | 100.0% | 100.0% | 0.0 pp |
| cot | 100.0% | 40.0% | 60.0 pp |

**Extra conflict penalty under CoT: 60.0 pp; 95% list bootstrap: [47.5 pp, 72.5 pp].**

The table and primary contrast use complete matched lists only.

List-level interaction: 18 positive, 2 zero, 0 negative.

Review for confirmation requires all planned answers valid, at least 20 lists, an extra penalty of at least 15 pp, an actual CoT accuracy drop under conflict, and lower CoT than direct accuracy under conflict. Inspect the interval and individual lists before any new experiment. No further calls start automatically.

| Response | Correct → wrong | Wrong → correct | Correct in both | Wrong in both |
|---|---:|---:|---:|---:|
| direct | 0 | 0 | 40 | 0 |
| cot | 24 | 0 | 16 | 0 |

Transitions run from the supporting to the conflicting background; these are independent calls, not chronological revisions in a conversation.

| Response | Background | Correct / valid / planned | Accuracy among valid |
|---|---|---:|---:|
| direct | conflict | 40 / 40 / 40 | 100.0% |
| direct | support | 40 / 40 / 40 | 100.0% |
| cot | conflict | 16 / 40 / 40 | 40.0% |
| cot | support | 40 / 40 / 40 | 100.0% |
