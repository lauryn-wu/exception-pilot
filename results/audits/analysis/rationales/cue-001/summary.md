# Offline rationale audit

Coder: `record-evidence-lexical-v2`. 48 scorable visible responses.

Provisional lexical codes describe detected written evidence; never_stated means no qualifying assertion was detected, not proof of absence. They do not establish retrieval, task recognition, or faithful internal reasoning. The conservative rule requires a target-record assertion, includes multiline record blocks, and rejects bare inferential comparisons. Missing-label evidence takes precedence; both flags remain in CSV. Evidence excerpts are Markdown-normalized, not raw character offsets.

The brief's single-line regex disagrees with the revised record-evidence flag on 13/48 responses. Both legacy flags are retained. JSON reasoning fields are decoded. Missing-gold tasks, nonreasoning anchors, and replay tasks are excluded. Revision and reasoning-first traces are also shown separately below.

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| cue-001 | all selected arms | correct | never_stated | 9 | 39.1% |
| cue-001 | all selected arms | correct | relabeled_missing | 1 | 4.3% |
| cue-001 | all selected arms | correct | stated_then_overridden | 0 | 0.0% |
| cue-001 | all selected arms | correct | stated_and_followed | 13 | 56.5% |
| cue-001 | all selected arms | wrong | never_stated | 13 | 52.0% |
| cue-001 | all selected arms | wrong | relabeled_missing | 9 | 36.0% |
| cue-001 | all selected arms | wrong | stated_then_overridden | 3 | 12.0% |
| cue-001 | all selected arms | wrong | stated_and_followed | 0 | 0.0% |

| Run | Cell | Outcome | Code | Count | Share within cell/outcome |
|---|---|---|---|---:|---:|
| cue-001 | /visible | correct | never_stated | 9 | 39.1% |
| cue-001 | /visible | correct | relabeled_missing | 1 | 4.3% |
| cue-001 | /visible | correct | stated_then_overridden | 0 | 0.0% |
| cue-001 | /visible | correct | stated_and_followed | 13 | 56.5% |
| cue-001 | /visible | wrong | never_stated | 13 | 52.0% |
| cue-001 | /visible | wrong | relabeled_missing | 9 | 36.0% |
| cue-001 | /visible | wrong | stated_then_overridden | 3 | 12.0% |
| cue-001 | /visible | wrong | stated_and_followed | 0 | 0.0% |
