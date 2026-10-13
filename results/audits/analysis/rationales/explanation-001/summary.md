# Offline rationale audit

Coder: `record-evidence-lexical-v2`. 48 scorable visible responses.

Provisional lexical codes describe detected written evidence; never_stated means no qualifying assertion was detected, not proof of absence. They do not establish retrieval, task recognition, or faithful internal reasoning. The conservative rule requires a target-record assertion, includes multiline record blocks, and rejects bare inferential comparisons. Missing-label evidence takes precedence; both flags remain in CSV. Evidence excerpts are Markdown-normalized, not raw character offsets.

The brief's single-line regex disagrees with the revised record-evidence flag on 16/48 responses. Both legacy flags are retained. JSON reasoning fields are decoded. Missing-gold tasks, nonreasoning anchors, and replay tasks are excluded. Revision and reasoning-first traces are also shown separately below.

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| explanation-001 | all selected arms | correct | never_stated | 11 | 44.0% |
| explanation-001 | all selected arms | correct | relabeled_missing | 2 | 8.0% |
| explanation-001 | all selected arms | correct | stated_then_overridden | 0 | 0.0% |
| explanation-001 | all selected arms | correct | stated_and_followed | 12 | 48.0% |
| explanation-001 | all selected arms | wrong | never_stated | 11 | 47.8% |
| explanation-001 | all selected arms | wrong | relabeled_missing | 9 | 39.1% |
| explanation-001 | all selected arms | wrong | stated_then_overridden | 3 | 13.0% |
| explanation-001 | all selected arms | wrong | stated_and_followed | 0 | 0.0% |

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| explanation-001 | /cot | correct | never_stated | 11 | 44.0% |
| explanation-001 | /cot | correct | relabeled_missing | 2 | 8.0% |
| explanation-001 | /cot | correct | stated_then_overridden | 0 | 0.0% |
| explanation-001 | /cot | correct | stated_and_followed | 12 | 48.0% |
| explanation-001 | /cot | wrong | never_stated | 11 | 47.8% |
| explanation-001 | /cot | wrong | relabeled_missing | 9 | 39.1% |
| explanation-001 | /cot | wrong | stated_then_overridden | 3 | 13.0% |
| explanation-001 | /cot | wrong | stated_and_followed | 0 | 0.0% |
