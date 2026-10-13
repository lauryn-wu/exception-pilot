# Instruction × output-interface diagnostic

Status: **COMPLETE**
Primary report: **COMPLETE**

Coverage: 192/192 returned responses; 0 missing; 0 transport errors.

Primary: `(initial − copy)JSON − (initial − copy)text`.
Positive values mean JSON increases copying's disadvantage.

Estimate: 0.22916666666666666; 95% whole-world percentile CI: [0.10416666666666667, 0.3541666666666667]

| Condition | Returned/48 | Correct first | Final correct/scored | Contract met | Correct first → wrong final |
|---|---:|---:|---:|---:|---:|
| copy_record/text | 48/48 | 47 | 29/48 | 48 | 19 |
| copy_record/json | 48/48 | 35 | 39/48 | 48 | 0 |
| initial_answer/text | 48/48 | 48 | 27/48 | 48 | 21 |
| initial_answer/json | 48/48 | 47 | 38/48 | 48 | 9 |

All first-entry categories and denominators appear in summary.json.

Manual review: traces.jsonl contains complete requests, raw responses and all attempts for every planned trial. manual_review_template.csv is a blank coding sheet; save edits under another name (analysis regenerates the template).

- Diagnostic using previously examined worlds; not independent confirmation.
- Interface package includes formatting instructions and schema constraints.
- Equal completion-token caps do not guarantee equal reasoning lengths.
- Percentile intervals can be degenerate; they do not establish equivalence.
- Condition accuracies use returned-response denominators; transport failures are missing.
- Final accuracy over returned responses counts missing final fields as unsuccessful; scored-final accuracy is also shown.
- No automatic contradiction-recognition labels or follow-up calls.
