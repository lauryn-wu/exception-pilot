# Offline rationale audit

Coder: `record-evidence-lexical-v2`. 24 scorable visible responses.

Provisional lexical codes describe detected written evidence; never_stated means no qualifying assertion was detected, not proof of absence. They do not establish retrieval, task recognition, or faithful internal reasoning. The conservative rule requires a target-record assertion, includes multiline record blocks, and rejects bare inferential comparisons. Missing-label evidence takes precedence; both flags remain in CSV. Evidence excerpts are Markdown-normalized, not raw character offsets.

The brief's single-line regex disagrees with the revised record-evidence flag on 7/24 responses. Both legacy flags are retained. JSON reasoning fields are decoded. Missing-gold tasks, nonreasoning anchors, and replay tasks are excluded. Revision and reasoning-first traces are also shown separately below.

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| mistral-prefix-v2-001 | all selected arms | correct | never_stated | 0 | 0.0% |
| mistral-prefix-v2-001 | all selected arms | correct | relabeled_missing | 4 | 26.7% |
| mistral-prefix-v2-001 | all selected arms | correct | stated_then_overridden | 0 | 0.0% |
| mistral-prefix-v2-001 | all selected arms | correct | stated_and_followed | 11 | 73.3% |
| mistral-prefix-v2-001 | all selected arms | wrong | never_stated | 3 | 33.3% |
| mistral-prefix-v2-001 | all selected arms | wrong | relabeled_missing | 5 | 55.6% |
| mistral-prefix-v2-001 | all selected arms | wrong | stated_then_overridden | 1 | 11.1% |
| mistral-prefix-v2-001 | all selected arms | wrong | stated_and_followed | 0 | 0.0% |

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| mistral-prefix-v2-001 | /visible | correct | never_stated | 0 | 0.0% |
| mistral-prefix-v2-001 | /visible | correct | relabeled_missing | 4 | 26.7% |
| mistral-prefix-v2-001 | /visible | correct | stated_then_overridden | 0 | 0.0% |
| mistral-prefix-v2-001 | /visible | correct | stated_and_followed | 11 | 73.3% |
| mistral-prefix-v2-001 | /visible | wrong | never_stated | 3 | 33.3% |
| mistral-prefix-v2-001 | /visible | wrong | relabeled_missing | 5 | 55.6% |
| mistral-prefix-v2-001 | /visible | wrong | stated_then_overridden | 1 | 11.1% |
| mistral-prefix-v2-001 | /visible | wrong | stated_and_followed | 0 | 0.0% |
