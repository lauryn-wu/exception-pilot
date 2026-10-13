# Offline rationale audit

Coder: `record-evidence-lexical-v2`. 24 scorable visible responses.

Provisional lexical codes describe detected written evidence; never_stated means no qualifying assertion was detected, not proof of absence. They do not establish retrieval, task recognition, or faithful internal reasoning. The conservative rule requires a target-record assertion, includes multiline record blocks, and rejects bare inferential comparisons. Missing-label evidence takes precedence; both flags remain in CSV. Evidence excerpts are Markdown-normalized, not raw character offsets.

The brief's single-line regex disagrees with the revised record-evidence flag on 11/24 responses. Both legacy flags are retained. JSON reasoning fields are decoded. Missing-gold tasks, nonreasoning anchors, and replay tasks are excluded. Revision and reasoning-first traces are also shown separately below.

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| order-001 | all selected arms | correct | never_stated | 12 | 80.0% |
| order-001 | all selected arms | correct | relabeled_missing | 1 | 6.7% |
| order-001 | all selected arms | correct | stated_then_overridden | 0 | 0.0% |
| order-001 | all selected arms | correct | stated_and_followed | 2 | 13.3% |
| order-001 | all selected arms | wrong | never_stated | 8 | 88.9% |
| order-001 | all selected arms | wrong | relabeled_missing | 1 | 11.1% |
| order-001 | all selected arms | wrong | stated_then_overridden | 0 | 0.0% |
| order-001 | all selected arms | wrong | stated_and_followed | 0 | 0.0% |

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| order-001 | /reasoning_first | correct | never_stated | 12 | 80.0% |
| order-001 | /reasoning_first | correct | relabeled_missing | 1 | 6.7% |
| order-001 | /reasoning_first | correct | stated_then_overridden | 0 | 0.0% |
| order-001 | /reasoning_first | correct | stated_and_followed | 2 | 13.3% |
| order-001 | /reasoning_first | wrong | never_stated | 8 | 88.9% |
| order-001 | /reasoning_first | wrong | relabeled_missing | 1 | 11.1% |
| order-001 | /reasoning_first | wrong | stated_then_overridden | 0 | 0.0% |
| order-001 | /reasoning_first | wrong | stated_and_followed | 0 | 0.0% |
