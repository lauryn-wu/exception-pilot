# Mistral continuation map V3 — exploratory

Status: **exploratory_map_complete_with_unscorable**
SIMULATED: False. 1078/1075 attempts/planned responses.
12 reused parent worlds; 24 parent traces. No corrected text is supplied. No independent confirmation or internal mechanism claim.

## Scoring amendment

Parse a bounded terminal block with an ASCII case-insensitive ANSWER marker, optional ASCII whitespace, balanced Markdown emphasis/inline code, optionally one period or a complete text fence. Labels stay uppercase A/B/C; no prose or alternatives are guessed.
Collect all 48 base responses before evaluating format failures; retain every unscorable response without retry. Any unscorable response blocks mapping after collection.
Original V2 status: **sampling_check_failed_stop**. Imported attempts: 9; new attempts: 1069.
Whitespace-normalized responses: 25; additionally presentation-normalized: 32. Raw responses are unchanged. V1/V2 scores are retained in answers.csv and summary.json.
This amendment was made after nine calls. Collect all 48 base responses, retain unscorable answers, then evaluate the unchanged thresholds. Imported responses are not new draws.

## Sampling check

Decision: pass. Direct correct: 24/24; visible correct: 13/24.
Base responses: 48/48 returned; 48 valid; 0 unscorable; 0 pending. Decision basis: original_behavioral_thresholds.
The original source replay status is preserved; this study compares fresh continuation distributions.

## Target-record-line contrast

Positive values favor retaining the line. Whole-world descriptive intervals only.

| Subset (lexical) | After minus before | 95% interval | Complete / eligible worlds | Eligible cases |
|---|---:|---|---:|---:|
| all | 0.028 | [-0.15972222222222224, 0.2083333333333333] | 12/12 | 23 |
| missing_word | 0.069 | [-0.15277777777777776, 0.3194444444444444] | 6/6 | 10 |
| no_missing_word | -0.021 | [-0.23958333333333337, 0.16666666666666666] | 8/8 | 13 |

## All trajectories

Each checkpoint has six planned draws. Adjacent changes are exploratory and may be sampling noise. Exact retained blocks are in preview.md and summary.json.

### prefix-list-000/record_1/visible

Recorded: A; pattern: C; saved parent answer: A.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 5 | 0 | 0.833 | — |
| c01 | 111 | before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.000 |
| c02 | 310 | before_target_record_line | 6/6 | 6 | 0 | 1.000 | 0.167 |
| c03 | 355 | after_target_record_line, before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c04 | 1046 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-000/record_2/visible

Recorded: B; pattern: C; saved parent answer: B.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 6 | 0 | 1.000 | — |
| c01 | 111 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c02 | 313 | before_target_record_line | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c03 | 358 | after_target_record_line, before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c04 | 459 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c05 | 771 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c06 | 862 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-001/record_2/visible

Recorded: B; pattern: A; saved parent answer: B.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 2 | 4 | 0.333 | — |
| c01 | 111 | before_numbered_step | 6/6 | 3 | 3 | 0.500 | 0.167 |
| c02 | 351 | before_target_record_line | 6/6 | 6 | 0 | 1.000 | 0.500 |
| c03 | 377 | after_target_record_line, before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c04 | 1120 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c05 | 1479 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-001/record_1/visible

Recorded: C; pattern: A; saved parent answer: C.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 4 | 2 | 0.667 | — |
| c01 | 111 | before_numbered_step | 6/6 | 4 | 2 | 0.667 | 0.000 |
| c02 | 279 | before_target_record_line | 6/6 | 4 | 2 | 0.667 | 0.000 |
| c03 | 355 | after_target_record_line, before_numbered_step | 6/6 | 3 | 3 | 0.500 | -0.167 |
| c04 | 940 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.500 |
| c05 | 1378 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c06 | 1570 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c07 | 1895 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-002/record_1/visible

Recorded: C; pattern: B; saved parent answer: B.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | before_numbered_step, start_without_assistant_prefix | 6/6 | 4 | 2 | 0.667 | — |
| c01 | 133 | before_target_record_line | 6/6 | 3 | 3 | 0.500 | -0.167 |
| c02 | 157 | after_target_record_line | 6/6 | 3 | 3 | 0.500 | 0.000 |
| c03 | 205 | before_numbered_step | 6/6 | 1 | 5 | 0.167 | -0.333 |
| c04 | 333 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | 0.167 |
| c05 | 756 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | -0.333 |
| c06 | 909 | before_conclusion_or_summary | 4/6 | 0 | 4 | 0.000 | — |

### prefix-list-002/record_2/visible

Recorded: A; pattern: B; saved parent answer: B.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 5 | 1 | 0.833 | — |
| c01 | 111 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | -0.833 |
| c02 | 350 | before_target_record_line | 6/6 | 5 | 1 | 0.833 | 0.833 |
| c03 | 376 | after_target_record_line, before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.000 |
| c04 | 706 | before_numbered_step | 6/6 | 3 | 3 | 0.500 | -0.333 |
| c05 | 1223 | before_numbered_step | 6/6 | 1 | 5 | 0.167 | -0.333 |
| c06 | 1665 | before_conclusion_or_summary | 6/6 | 1 | 5 | 0.167 | 0.000 |

### prefix-list-003/record_2/visible

Recorded: A; pattern: C; saved parent answer: C.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 4 | 2 | 0.667 | — |
| c01 | 111 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | -0.333 |
| c02 | 313 | before_target_record_line | 6/6 | 1 | 5 | 0.167 | -0.167 |
| c03 | 369 | after_target_record_line, before_numbered_step | 6/6 | 1 | 5 | 0.167 | 0.000 |
| c04 | 1283 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | -0.167 |
| c05 | 1813 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | 0.000 |
| c06 | 2173 | before_conclusion_or_summary | 6/6 | 0 | 6 | 0.000 | 0.000 |

### prefix-list-003/record_1/visible

Recorded: B; pattern: C; saved parent answer: C.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 6 | 0 | 1.000 | — |
| c01 | 111 | before_numbered_step | 6/6 | 4 | 2 | 0.667 | -0.333 |
| c02 | 427 | before_numbered_step | 6/6 | 1 | 5 | 0.167 | -0.500 |
| c03 | 904 | before_target_record_line | 6/6 | 2 | 4 | 0.333 | 0.167 |
| c04 | 987 | after_target_record_line | 6/6 | 3 | 3 | 0.500 | 0.167 |
| c05 | 1203 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | -0.167 |
| c06 | 1685 | before_numbered_step | 6/6 | 1 | 5 | 0.167 | -0.167 |
| c07 | 1946 | before_numbered_step | 6/6 | 4 | 2 | 0.667 | 0.500 |
| c08 | 2470 | before_conclusion_or_summary | 6/6 | 0 | 6 | 0.000 | -0.667 |

### prefix-list-004/record_1/visible

Recorded: A; pattern: B; saved parent answer: A.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 1 | 5 | 0.167 | — |
| c01 | 111 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | 0.167 |
| c02 | 145 | before_target_record_line | 6/6 | 2 | 4 | 0.333 | 0.000 |
| c03 | 304 | after_target_record_line, before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.500 |
| c04 | 752 | before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.000 |
| c05 | 1028 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | -0.500 |
| c06 | 1346 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | 0.000 |
| c07 | 1713 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.667 |

### prefix-list-004/record_2/visible

Recorded: C; pattern: B; saved parent answer: B.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 3 | 3 | 0.500 | — |
| c01 | 111 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | -0.167 |
| c02 | 145 | before_target_record_line | 6/6 | 0 | 5 | 0.000 | -0.333 |
| c03 | 298 | after_target_record_line | 6/6 | 4 | 2 | 0.667 | 0.667 |
| c04 | 967 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | -0.333 |
| c05 | 1100 | before_numbered_step | 6/6 | 1 | 5 | 0.167 | -0.167 |
| c06 | 1375 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | 0.167 |
| c07 | 1744 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | -0.333 |
| c08 | 2109 | before_conclusion_or_summary | 6/6 | 0 | 6 | 0.000 | 0.000 |

### prefix-list-005/record_1/visible

Recorded: A; pattern: C; saved parent answer: A.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 4 | 2 | 0.667 | — |
| c01 | 111 | before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.167 |
| c02 | 258 | before_target_record_line | 6/6 | 1 | 5 | 0.167 | -0.667 |
| c03 | 314 | after_target_record_line, before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.667 |
| c04 | 810 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.167 |
| c05 | 1162 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-005/record_2/visible

Recorded: B; pattern: C; saved parent answer: B.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 5 | 1 | 0.833 | — |
| c01 | 111 | before_numbered_step | 6/6 | 1 | 5 | 0.167 | -0.667 |
| c02 | 370 | before_target_record_line | 6/6 | 5 | 1 | 0.833 | 0.667 |
| c03 | 396 | after_target_record_line, before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.167 |
| c04 | 1099 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-006/record_1/visible

Recorded: C; pattern: A; saved parent answer: C.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 2 | 3 | 0.333 | — |
| c01 | 109 | before_numbered_step | 6/6 | 3 | 3 | 0.500 | 0.167 |
| c02 | 375 | before_target_record_line | 6/6 | 3 | 3 | 0.500 | 0.000 |
| c03 | 559 | after_target_record_line, before_numbered_step | 6/6 | 4 | 2 | 0.667 | 0.167 |
| c04 | 1284 | before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.167 |
| c05 | 1798 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.167 |
| c06 | 2305 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-006/record_2/visible

Recorded: B; pattern: A; saved parent answer: B.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 5 | 0 | 0.833 | — |
| c01 | 109 | before_numbered_step | 6/6 | 1 | 5 | 0.167 | -0.667 |
| c02 | 283 | before_numbered_step | 6/6 | 3 | 2 | 0.500 | 0.333 |
| c03 | 413 | before_numbered_step | 6/6 | 1 | 4 | 0.167 | -0.333 |
| c04 | 489 | before_numbered_step | 6/6 | 4 | 2 | 0.667 | 0.500 |
| c05 | 559 | before_numbered_step | 6/6 | 5 | 0 | 0.833 | 0.167 |
| c06 | 636 | before_numbered_step, before_target_record_line | 6/6 | 3 | 3 | 0.500 | -0.333 |
| c07 | 749 | after_target_record_line | 6/6 | 5 | 1 | 0.833 | 0.333 |
| c08 | 2111 | before_conclusion_or_summary | 6/6 | 1 | 0 | 0.167 | -0.667 |

### prefix-list-007/record_1/visible

Recorded: B; pattern: C; saved parent answer: C.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 2 | 3 | 0.333 | — |
| c01 | 111 | before_numbered_step | 6/6 | 2 | 3 | 0.333 | 0.000 |
| c02 | 449 | before_numbered_step | 6/6 | 0 | 4 | 0.000 | -0.333 |
| c03 | 891 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | 0.000 |
| c04 | 1170 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | 0.000 |
| c05 | 1360 | before_numbered_step | 6/6 | 0 | 3 | 0.000 | 0.000 |
| c06 | 1519 | before_numbered_step | 6/6 | 2 | 4 | 0.333 | 0.333 |
| c07 | 1729 | before_numbered_step | 6/6 | 2 | 3 | 0.333 | 0.000 |
| c08 | 1910 | before_numbered_step | 6/6 | 0 | 3 | 0.000 | -0.333 |
| c09 | 1994 | before_target_record_line | 6/6 | 0 | 4 | 0.000 | 0.000 |
| c10 | 2020 | after_target_record_line | 6/6 | 1 | 1 | 0.167 | 0.167 |
| c11 | 2096 | before_numbered_step | 6/6 | 1 | 3 | 0.167 | 0.000 |
| c12 | 2264 | before_conclusion_or_summary | 6/6 | 1 | 5 | 0.167 | 0.000 |

### prefix-list-007/record_2/visible

Recorded: A; pattern: C; saved parent answer: A.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 4 | 2 | 0.667 | — |
| c01 | 111 | before_numbered_step | 6/6 | 4 | 2 | 0.667 | 0.000 |
| c02 | 344 | before_target_record_line | 6/6 | 5 | 1 | 0.833 | 0.167 |
| c03 | 370 | after_target_record_line, before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.167 |
| c04 | 946 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-008/record_1/visible

Recorded: B; pattern: A; saved parent answer: B.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 4 | 2 | 0.667 | — |
| c01 | 115 | before_numbered_step | 6/6 | 4 | 2 | 0.667 | 0.000 |
| c02 | 298 | before_target_record_line | 6/6 | 5 | 1 | 0.833 | 0.167 |
| c03 | 379 | after_target_record_line, before_numbered_step | 6/6 | 1 | 5 | 0.167 | -0.667 |
| c04 | 824 | before_numbered_step | 6/6 | 4 | 2 | 0.667 | 0.500 |
| c05 | 1525 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.333 |
| c06 | 1875 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-008/record_2/visible

Recorded: C; pattern: A; saved parent answer: A.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | before_numbered_step, start_without_assistant_prefix | 6/6 | 2 | 4 | 0.333 | — |
| c01 | 134 | before_numbered_step | 6/6 | 0 | 4 | 0.000 | -0.333 |
| c02 | 404 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | 0.000 |
| c03 | 557 | before_conclusion_or_summary | 6/6 | 0 | 6 | 0.000 | 0.000 |

### prefix-list-009/record_2/visible

Recorded: C; pattern: B; saved parent answer: C.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 4 | 2 | 0.667 | — |
| c01 | 111 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.333 |
| c02 | 294 | before_target_record_line | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c03 | 339 | after_target_record_line, before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c04 | 440 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c05 | 887 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c06 | 972 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-009/record_1/visible

Recorded: A; pattern: B; saved parent answer: A.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 5 | 1 | 0.833 | — |
| c01 | 111 | before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.000 |
| c02 | 294 | before_target_record_line | 6/6 | 5 | 1 | 0.833 | 0.000 |
| c03 | 339 | after_target_record_line, before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.167 |
| c04 | 440 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c05 | 713 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c06 | 909 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-010/record_2/visible

Recorded: C; pattern: A; saved parent answer: A.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 0 | 6 | 0.000 | — |
| c01 | 111 | before_numbered_step | 6/6 | 3 | 3 | 0.500 | 0.500 |
| c02 | 314 | before_target_record_line | 6/6 | 3 | 3 | 0.500 | 0.000 |
| c03 | 375 | after_target_record_line, before_numbered_step | 6/6 | 0 | 6 | 0.000 | -0.500 |
| c04 | 751 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | 0.000 |
| c05 | 1174 | before_numbered_step | 6/6 | 1 | 5 | 0.167 | 0.167 |
| c06 | 1469 | before_conclusion_or_summary | 6/6 | 0 | 6 | 0.000 | -0.167 |

### prefix-list-010/record_1/visible

Recorded: B; pattern: A; saved parent answer: A.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 1 | 5 | 0.167 | — |
| c01 | 111 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | -0.167 |
| c02 | 304 | before_target_record_line | 6/6 | 2 | 4 | 0.333 | 0.333 |
| c03 | 360 | after_target_record_line, before_numbered_step | 6/6 | 1 | 5 | 0.167 | -0.167 |
| c04 | 863 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | -0.167 |
| c05 | 1100 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | 0.000 |
| c06 | 1320 | before_numbered_step | 6/6 | 0 | 6 | 0.000 | 0.000 |
| c07 | 1595 | before_conclusion_or_summary | 6/6 | 0 | 6 | 0.000 | 0.000 |

### prefix-list-011/record_2/visible

Recorded: A; pattern: B; saved parent answer: A.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 6 | 0 | 1.000 | — |
| c01 | 111 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c02 | 274 | before_target_record_line | 6/6 | 5 | 1 | 0.833 | -0.167 |
| c03 | 319 | after_target_record_line, before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.000 |
| c04 | 582 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.167 |
| c05 | 1450 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c06 | 1877 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.000 |

### prefix-list-011/record_1/visible

Recorded: C; pattern: B; saved parent answer: C.

| Point | Cut | Labels | Valid / 6 | Correct | Pattern | Accuracy (valid only) | Change |
|---|---:|---|---:|---:|---:|---:|---:|
| c00 | 0 | start_without_assistant_prefix | 6/6 | 5 | 1 | 0.833 | — |
| c01 | 111 | before_numbered_step | 6/6 | 6 | 0 | 1.000 | 0.167 |
| c02 | 274 | before_target_record_line | 6/6 | 6 | 0 | 1.000 | 0.000 |
| c03 | 319 | after_target_record_line, before_numbered_step | 6/6 | 4 | 2 | 0.667 | -0.333 |
| c04 | 671 | before_numbered_step | 6/6 | 5 | 1 | 0.833 | 0.167 |
| c05 | 1308 | before_conclusion_or_summary | 6/6 | 6 | 0 | 1.000 | 0.167 |

## Interpretation limits

- Exploratory mapping of previously inspected traces on reused worlds. Six stochastic continuations per checkpoint are coarse estimates. No corrections or independent confirmation; no internal-state restoration or replay-agreement gate. Whitespace parsing was amended after six V1 calls; this is disclosed exploratory continuation, not a fresh or preregistered confirmation. V3 presentation parsing and complete-screen collection were amended after nine responses. All past answers are retained; this is exploratory continuation, not independent confirmation.
- Before/after includes the entire retained text block. It does not isolate semantic content from length or wording.
- MISSING is a lexical flag only; it does not establish a target-specific false availability claim.
- All returned invalid answers are retained. Only transport errors/unresolved requests can be retried.
- World contrasts average eligible cases within each world, then weight complete worlds equally. No individual rollouts are independent worlds.
- 10,000 whole-world bootstrap draws, seed 981723: descriptive unadjusted intervals, no multiplicity correction. Six draws per checkpoint provide coarse probabilities only. Degenerate intervals are not certainty or equivalence.
- Bounds assign all unscorable or pending slots incorrect/correct; they are not confidence intervals. No novelty or mechanism pass/fail test.
- V3 parsing and complete-screen collection were amended after nine responses. V1/V2 failed checks are preserved; prior scoring of later responses is a sensitivity view, not executed old protocols. Imported calls are not fresh samples.
