# Offline rationale audit

Coder: `record-evidence-lexical-v2`. 96 scorable visible responses.

Provisional lexical codes describe detected written evidence; never_stated means no qualifying assertion was detected, not proof of absence. They do not establish retrieval, task recognition, or faithful internal reasoning. The conservative rule requires a target-record assertion, includes multiline record blocks, and rejects bare inferential comparisons. Missing-label evidence takes precedence; both flags remain in CSV. Evidence excerpts are Markdown-normalized, not raw character offsets.

The brief's single-line regex disagrees with the revised record-evidence flag on 39/96 responses. Both legacy flags are retained. JSON reasoning fields are decoded. Missing-gold tasks, nonreasoning anchors, and replay tasks are excluded. Revision and reasoning-first traces are also shown separately below.

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| revision-001 | all selected arms | correct | never_stated | 45 | 71.4% |
| revision-001 | all selected arms | correct | relabeled_missing | 5 | 7.9% |
| revision-001 | all selected arms | correct | stated_then_overridden | 0 | 0.0% |
| revision-001 | all selected arms | correct | stated_and_followed | 13 | 20.6% |
| revision-001 | all selected arms | wrong | never_stated | 30 | 90.9% |
| revision-001 | all selected arms | wrong | relabeled_missing | 2 | 6.1% |
| revision-001 | all selected arms | wrong | stated_then_overridden | 1 | 3.0% |
| revision-001 | all selected arms | wrong | stated_and_followed | 0 | 0.0% |

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| revision-001 | /reasoning_first | correct | never_stated | 24 | 80.0% |
| revision-001 | /reasoning_first | correct | relabeled_missing | 2 | 6.7% |
| revision-001 | /reasoning_first | correct | stated_then_overridden | 0 | 0.0% |
| revision-001 | /reasoning_first | correct | stated_and_followed | 4 | 13.3% |
| revision-001 | /reasoning_first | wrong | never_stated | 16 | 88.9% |
| revision-001 | /reasoning_first | wrong | relabeled_missing | 1 | 5.6% |
| revision-001 | /reasoning_first | wrong | stated_then_overridden | 1 | 5.6% |
| revision-001 | /reasoning_first | wrong | stated_and_followed | 0 | 0.0% |
| revision-001 | /revision | correct | never_stated | 21 | 63.6% |
| revision-001 | /revision | correct | relabeled_missing | 3 | 9.1% |
| revision-001 | /revision | correct | stated_then_overridden | 0 | 0.0% |
| revision-001 | /revision | correct | stated_and_followed | 9 | 27.3% |
| revision-001 | /revision | wrong | never_stated | 14 | 93.3% |
| revision-001 | /revision | wrong | relabeled_missing | 1 | 6.7% |
| revision-001 | /revision | wrong | stated_then_overridden | 0 | 0.0% |
| revision-001 | /revision | wrong | stated_and_followed | 0 | 0.0% |
