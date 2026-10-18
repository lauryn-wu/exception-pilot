# New-user-turn source-transcription pilot

Mode: LIVE_LOCAL; collection: COMPLETE; criterion: PASSED.
Parent v2: FAILED (8/8 present correct; 0/4 MISSING correct). V1 remains FAILED.
Main planned: 0. Main eligible: false.
Counts: {"planned": 12, "returned": 12, "never_started": 0, "failed": 0, "ambiguous": 0, "correct": 12, "correct_per_returned": {"numerator": 12, "denominator": 12}, "successful_per_planned": {"numerator": 12, "denominator": 12}, "returned_unsuccessful": 0, "unavailable": 0}
Source-present: {"planned": 8, "returned": 8, "never_started": 0, "failed": 0, "ambiguous": 0, "correct": 8, "correct_per_returned": {"numerator": 8, "denominator": 8}, "successful_per_planned": {"numerator": 8, "denominator": 8}, "returned_unsuccessful": 0, "unavailable": 0}
Literal-MISSING: {"planned": 4, "returned": 4, "never_started": 0, "failed": 0, "ambiguous": 0, "correct": 4, "correct_per_returned": {"numerator": 4, "denominator": 4}, "successful_per_planned": {"numerator": 4, "denominator": 4}, "returned_unsuccessful": 0, "unavailable": 0}
This invocation: {"model_loads": 0, "model_load_attempts": 0, "new_generations": 0, "reused_child_returns": 12, "prior_v2_returns": 12, "prior_v2_generations_rerun": 0, "main_calls": 0, "extension_revision": "c47897b9e12bf6529b0ef3de1a8ce23e97ad9350"}
Timing: {"finished_invocations": 1, "unfinished_invocations": 0, "generation_events": 12, "generation_seconds": 4.266174091026187, "note": "Finished-invocation load totals are lower bounds if an invocation was interrupted."}

Development controls selected after v1/v2 failures. Message structure, wording and response format change together; improvement cannot be attributed to the role boundary. At k=0 with the source available, this measures recovery after a fresh request, not uninterrupted retention, deliberate override, an endogenous mechanism, long-prefix behavior, population accuracy, or matched-interface accuracy advantage.

## staged-v5-000 v0 calibration_present
Source: staged-v5-000/v0/original/visible; plate: V5T9NUGW; expected: C.
Parent query: v5/source-report-v2/4440b3d41ee22855c06cc28878c8055b9df6109316734e6bf9ef9edbdb900f69; child: v5/source-user-pilot-v1/99a266aecec3aad91f4be5f559c66f0e181897394f6ce3b2ebbb681665bd94f7.
Status: returned
Child raw payload (complete):
{"tokens": [34, 151645], "stopped": true, "text": "C", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "C", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 2, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "7844c9f366afd62c528f3d3c48566282b507173d455b9c891f4dee0104b9df84", "raw": {"tokens": [34, 1, 151645], "stopped": true, "text": "C\"", "next_token_logits": {}, "finish": "eos"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": true, "field_valid": true, "valid": true, "field_text": "C", "field_value": "C", "closing_quote_offset": 1, "trailing_text": "", "answer": "C", "correct": true, "diagnostic_label": "C", "category": "C", "eos_observed": true, "generation_length_stop": false, "token_count": 3, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-000 v1 calibration_present
Source: staged-v5-000/v1/original/visible; plate: V5T9NUGW; expected: A.
Parent query: v5/source-report-v2/9145061c646bd294bdeed6e7703543f46902500ecbd08274c44e3fdb0be38dc6; child: v5/source-user-pilot-v1/c503d0c8b4f2fbf8d9c7495494ecccdb22f9fe0f83d36b552e78a776a9f9f00e.
Status: returned
Child raw payload (complete):
{"tokens": [32, 151645], "stopped": true, "text": "A", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "A", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 2, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "8e5f35d574134a70bf9dd51ef55684036aaf060f370dd8a417d2fffea2770d8d", "raw": {"tokens": [32, 1, 151645], "stopped": true, "text": "A\"", "next_token_logits": {}, "finish": "eos"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": true, "field_valid": true, "valid": true, "field_text": "A", "field_value": "A", "closing_quote_offset": 1, "trailing_text": "", "answer": "A", "correct": true, "diagnostic_label": "A", "category": "A", "eos_observed": true, "generation_length_stop": false, "token_count": 3, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-000 v0 calibration_missing
Source: staged-v5-000/v0/original/visible; plate: V5T9NUGW; expected: MISSING.
Parent query: v5/source-report-v2/cde4f573085efe05f0747e6125882b3eef29943e27d58ca705835bd0f0d192cb; child: v5/source-user-pilot-v1/c626ef51f440082c451542dbd617398835429c152ee3cf22e32f028df56dcf14.
Status: returned
Child raw payload (complete):
{"tokens": [79470, 1718, 151645], "stopped": true, "text": "MISSING", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "MISSING", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 3, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "325cbd1bafa65b9a48f4f67599272b8eb020631c4276025049971eb2ce59f9d8", "raw": {"tokens": [53, 20, 51, 24, 45, 2941, 54, 760, 47425, 369, 65938, 79669, 760, 14539, 760, 83635], "stopped": false, "text": "V5T9NUGW | Designed for humid summers | Manual | Cloth", "next_token_logits": {}, "finish": "length"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": false, "field_valid": false, "valid": false, "field_text": "V5T9NUGW | Designed for humid summers | Manual | Cloth", "field_value": "V5T9NUGW | Designed for humid summers | Manual | Cloth", "closing_quote_offset": null, "trailing_text": null, "answer": null, "correct": false, "diagnostic_label": null, "category": "incomplete_field", "eos_observed": false, "generation_length_stop": true, "token_count": 16, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-001 v0 calibration_present
Source: staged-v5-001/v0/original/visible; plate: V5TF73KA; expected: A.
Parent query: v5/source-report-v2/95ac95a5f8a3b225620a47b487fda9bcb1485933e576b276809d036ce73fcc97; child: v5/source-user-pilot-v1/b48acd1c1231efe1b4084db06c23bbdb516be4185c821f5eb6f7a15aafe1b46d.
Status: returned
Child raw payload (complete):
{"tokens": [32, 151645], "stopped": true, "text": "A", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "A", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 2, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "a9bc1d5e53f447e38fd87304518454af7d8fd16cc099859549786c0d9ae02f8f", "raw": {"tokens": [32, 1, 151645], "stopped": true, "text": "A\"", "next_token_logits": {}, "finish": "eos"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": true, "field_valid": true, "valid": true, "field_text": "A", "field_value": "A", "closing_quote_offset": 1, "trailing_text": "", "answer": "A", "correct": true, "diagnostic_label": "A", "category": "A", "eos_observed": true, "generation_length_stop": false, "token_count": 3, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-001 v1 calibration_present
Source: staged-v5-001/v1/original/visible; plate: V5TF73KA; expected: C.
Parent query: v5/source-report-v2/6ff183484a922a15ea9a0356a5a6c0e7be010754339ac97d4c43120ababe9da2; child: v5/source-user-pilot-v1/421ee70ae9a4fc0ba840e33b7af92a9d7fb5c4602dc61d22dcabbaf2e1694aee.
Status: returned
Child raw payload (complete):
{"tokens": [34, 151645], "stopped": true, "text": "C", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "C", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 2, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "7a9b820a5829aca715ebf55152b504afe5da71849e009b075553e0a09c96e3fc", "raw": {"tokens": [34, 1, 151645], "stopped": true, "text": "C\"", "next_token_logits": {}, "finish": "eos"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": true, "field_valid": true, "valid": true, "field_text": "C", "field_value": "C", "closing_quote_offset": 1, "trailing_text": "", "answer": "C", "correct": true, "diagnostic_label": "C", "category": "C", "eos_observed": true, "generation_length_stop": false, "token_count": 3, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-001 v0 calibration_missing
Source: staged-v5-001/v0/original/visible; plate: V5TF73KA; expected: MISSING.
Parent query: v5/source-report-v2/2008f6b687027e73f5c643a2b17e2d0fb56eda2891d7eefddd57a9c1d9aa5f01; child: v5/source-user-pilot-v1/a4a2fbcfd28fbcfcb925e7e3b1d881cdc22b52877620f8e8ea1f424a5562ccd5.
Status: returned
Child raw payload (complete):
{"tokens": [79470, 1718, 151645], "stopped": true, "text": "MISSING", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "MISSING", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 3, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "f4d079d79f02c54f6cff85fdc1f0b73631d42264696a8be105d42bf64929404c", "raw": {"tokens": [53, 20, 10808, 22, 18, 26444, 760, 47425, 369, 65938, 79669, 760, 14539, 760, 53534, 760], "stopped": false, "text": "V5TF73KA | Designed for humid summers | Manual | Vinyl |", "next_token_logits": {}, "finish": "length"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": false, "field_valid": false, "valid": false, "field_text": "V5TF73KA | Designed for humid summers | Manual | Vinyl |", "field_value": "V5TF73KA | Designed for humid summers | Manual | Vinyl |", "closing_quote_offset": null, "trailing_text": null, "answer": null, "correct": false, "diagnostic_label": null, "category": "incomplete_field", "eos_observed": false, "generation_length_stop": true, "token_count": 16, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-002 v0 calibration_present
Source: staged-v5-002/v0/original/visible; plate: V5TD48HZ; expected: A.
Parent query: v5/source-report-v2/1f8e9ae1bfdabf5d0c972f23e62859d11a61338adf528ef6f54327b348c3ff35; child: v5/source-user-pilot-v1/32d388c839f461b73e18bf5e86029b8da49ca9eac5168b4149504249362f366d.
Status: returned
Child raw payload (complete):
{"tokens": [32, 151645], "stopped": true, "text": "A", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "A", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 2, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "58e71efb3d2dd9408dcbbc03957cde8dcc2795065f718bb49ede1d5d4916d2d8", "raw": {"tokens": [32, 1, 151645], "stopped": true, "text": "A\"", "next_token_logits": {}, "finish": "eos"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": true, "field_valid": true, "valid": true, "field_text": "A", "field_value": "A", "closing_quote_offset": 1, "trailing_text": "", "answer": "A", "correct": true, "diagnostic_label": "A", "category": "A", "eos_observed": true, "generation_length_stop": false, "token_count": 3, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-002 v1 calibration_present
Source: staged-v5-002/v1/original/visible; plate: V5TD48HZ; expected: B.
Parent query: v5/source-report-v2/c44fe5a2c554c6751e8504733c9e442ab91e99616a9b132e45200ba50729ac08; child: v5/source-user-pilot-v1/0d93ebc91a9f8cfeb8dd5248beee5f34d4ec7cd12288e76c1d022ba4941f54f0.
Status: returned
Child raw payload (complete):
{"tokens": [33, 151645], "stopped": true, "text": "B", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "B", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 2, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "3975daee9d8e943b980f2114b7bc0f5ede9400829655ede4212ccd42fe391c50", "raw": {"tokens": [33, 1, 151645], "stopped": true, "text": "B\"", "next_token_logits": {}, "finish": "eos"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": true, "field_valid": true, "valid": true, "field_text": "B", "field_value": "B", "closing_quote_offset": 1, "trailing_text": "", "answer": "B", "correct": true, "diagnostic_label": "B", "category": "B", "eos_observed": true, "generation_length_stop": false, "token_count": 3, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-002 v0 calibration_missing
Source: staged-v5-002/v0/original/visible; plate: V5TD48HZ; expected: MISSING.
Parent query: v5/source-report-v2/9ecbb0b49b95f5924d248feb60cffb29fcb5a170646ffcb72ab7b62e44b3fbc2; child: v5/source-user-pilot-v1/336c9b9b5b5c52cc119cba6b3fd35d6bbbd274eedec8f03aa48ed8d00049837a.
Status: returned
Child raw payload (complete):
{"tokens": [79470, 1718, 151645], "stopped": true, "text": "MISSING", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "MISSING", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 3, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "c2a5cd79fd9429fcd572eb084131688fea58016a6ddd3f958285bc4678d8c64f", "raw": {"tokens": [53, 20, 16985, 19, 23, 61759, 760, 11702, 6450, 369, 4017, 9278, 760, 33981, 760, 83635], "stopped": false, "text": "V5TD48HZ | Equipped for hot sand | Automatic | Cloth", "next_token_logits": {}, "finish": "length"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": false, "field_valid": false, "valid": false, "field_text": "V5TD48HZ | Equipped for hot sand | Automatic | Cloth", "field_value": "V5TD48HZ | Equipped for hot sand | Automatic | Cloth", "closing_quote_offset": null, "trailing_text": null, "answer": null, "correct": false, "diagnostic_label": null, "category": "incomplete_field", "eos_observed": false, "generation_length_stop": true, "token_count": 16, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-003 v0 calibration_present
Source: staged-v5-003/v0/original/visible; plate: V5TT4GSL; expected: A.
Parent query: v5/source-report-v2/d3cb43048d4d28d53f39e6878b29eca37a9d6d7622a91630fdde8ba375e21961; child: v5/source-user-pilot-v1/d09b811cf989de5e8bd9b4018a659f2562270ca8f769c9ac4176a2357ed02dfd.
Status: returned
Child raw payload (complete):
{"tokens": [32, 151645], "stopped": true, "text": "A", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "A", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 2, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "69b35969819e234110450eaeef7767113433d392e3a51da8f56111a8e3622f4e", "raw": {"tokens": [32, 1, 151645], "stopped": true, "text": "A\"", "next_token_logits": {}, "finish": "eos"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": true, "field_valid": true, "valid": true, "field_text": "A", "field_value": "A", "closing_quote_offset": 1, "trailing_text": "", "answer": "A", "correct": true, "diagnostic_label": "A", "category": "A", "eos_observed": true, "generation_length_stop": false, "token_count": 3, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-003 v1 calibration_present
Source: staged-v5-003/v1/original/visible; plate: V5TT4GSL; expected: C.
Parent query: v5/source-report-v2/3700358c00d90e06f255c353af7738c11992e1e0b774f9d3b0b8c106d725a647; child: v5/source-user-pilot-v1/07a0cdc9ed2b34162071a8f591d387f9a8e7c3eed25ba790e16f72fcb5355a9b.
Status: returned
Child raw payload (complete):
{"tokens": [34, 151645], "stopped": true, "text": "C", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "C", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 2, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "afef2e1046c8376ed8dd5b4d699822d5c466a19511421ff6f484f10fdefcaefe", "raw": {"tokens": [34, 1, 151645], "stopped": true, "text": "C\"", "next_token_logits": {}, "finish": "eos"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": true, "field_valid": true, "valid": true, "field_text": "C", "field_value": "C", "closing_quote_offset": 1, "trailing_text": "", "answer": "C", "correct": true, "diagnostic_label": "C", "category": "C", "eos_observed": true, "generation_length_stop": false, "token_count": 3, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

## staged-v5-003 v0 calibration_missing
Source: staged-v5-003/v0/original/visible; plate: V5TT4GSL; expected: MISSING.
Parent query: v5/source-report-v2/707185d144ee00b1c8ad45e950a518fdfd6f188e8d5e2afb302de1bf10f48135; child: v5/source-user-pilot-v1/69dd2ebafeba9c7810d5904032bf567b54642ca7b882b57dcb0a70825f47151f.
Status: returned
Child raw payload (complete):
{"tokens": [79470, 1718, 151645], "stopped": true, "text": "MISSING", "next_token_logits": {}, "finish": "eos"}
Child score:
{"parser_version": "whole-response-exact-label-terminal-eos-v1", "raw_integrity": true, "complete": true, "format_valid": true, "valid": true, "answer": "MISSING", "correct": true, "eos_observed": true, "generation_length_stop": false, "token_count": 3, "finish": "eos", "metadata_errors": [], "category": "correct"}
Prior v2 raw + frozen score (different interface/parser):
{"interface": "same-assistant-quoted-source-query-v2", "parser": "first-closed-quoted-field-four-labels-v2", "operation_hash": "004f8526a44953656665f46ed82bf39f08a8856aba659dcfcff5127cd93a671a", "raw": {"tokens": [53, 20, 14903, 19, 38, 7984, 760, 7461, 973, 389, 24660, 9853, 760, 14539, 760, 53534], "stopped": false, "text": "V5TT4GSL | Operates on polar ice | Manual | Vinyl", "next_token_logits": {}, "finish": "length"}, "frozen_score": {"parser_version": "first-closed-quoted-field-four-labels-v2", "field_complete": false, "field_valid": false, "valid": false, "field_text": "V5TT4GSL | Operates on polar ice | Manual | Vinyl", "field_value": "V5TT4GSL | Operates on polar ice | Manual | Vinyl", "closing_quote_offset": null, "trailing_text": null, "answer": null, "correct": false, "diagnostic_label": null, "category": "incomplete_field", "eos_observed": false, "generation_length_stop": true, "token_count": 16, "metadata_errors": []}, "note": "Prior evidence under a different interface/parser; never a child cache hit or matched-interface answer control."}

STOP_AFTER_PILOT
Review all twelve replies before any separately specified larger experiment.
