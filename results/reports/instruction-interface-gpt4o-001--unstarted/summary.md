# Instruction × output-interface diagnostic

Status: **INCOMPLETE**
Primary report: **INCOMPLETE**

Coverage: 0/192 returned responses; 192 missing; 0 transport errors.

Primary: `(initial − copy)JSON − (initial − copy)text`.
Positive values mean JSON increases copying's disadvantage.

Estimate: None; 95% whole-world percentile CI: None

| Condition | Returned/48 | Correct first | Final correct/scored | Contract met | Correct first → wrong final |
|---|---:|---:|---:|---:|---:|
| copy_record/text | 0/48 | 0 | 0/0 | 0 | 0 |
| copy_record/json | 0/48 | 0 | 0/0 | 0 | 0 |
| initial_answer/text | 0/48 | 0 | 0/0 | 0 | 0 |
| initial_answer/json | 0/48 | 0 | 0/0 | 0 | 0 |

All first-entry categories and denominators appear in summary.json.

Manual review: traces.jsonl contains complete requests, raw responses and all attempts for every planned trial. manual_review_template.csv is a blank coding sheet; save edits under another name (analysis regenerates the template).

- Diagnostic using previously examined worlds; not independent confirmation.
- Interface package includes formatting instructions and schema constraints.
- Equal completion-token caps do not guarantee equal reasoning lengths.
- Percentile intervals can be degenerate; they do not establish equivalence.
- Condition accuracies use returned-response denominators; transport failures are missing.
- Final accuracy over returned responses counts missing final fields as unsuccessful; scored-final accuracy is also shown.
- No automatic contradiction-recognition labels or follow-up calls.
