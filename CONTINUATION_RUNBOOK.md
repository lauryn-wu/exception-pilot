# Runbook: exact-prefix continuation follow-up

Read REASONING_CONTINUATION_PROTOCOL.md before execution. No paid API, model
download, inference, or GPU allocation was performed for this implementation.
Python standard library suffices for previews, mock runs, analysis and tests.
The local backend needs `torch`, `transformers` and their tokenizer dependencies.
Use a model already on disk and freeze the environment; exact versions are saved.
No particular model has passed real continuation validation yet.

## Branch and offline review

```sh
git fetch origin
git worktree add ../exception-continuation origin/codex/reasoning-continuation-followup
cd ../exception-continuation
python3 -m unittest discover -s tests -p 'test_continuation_followup.py' -v
python3 -m exception_continuation prepare --phase selection --output runs/continuation-preview
python3 -m exception_continuation collect --output runs/continuation-preview --mock
python3 -m exception_continuation measure --output runs/continuation-preview --mock
python3 -m exception_continuation review-export --output runs/continuation-preview
python3 -m exception_continuation analyze --output runs/continuation-preview
```

The committed `previews/continuation/preview.md` shows exact initial requests.
`previews/continuation/branch-preview.json` shows a clearly labeled synthetic
checkpoint with all four prefix edits and separate readout branches. These are
software fixtures, not observed model reasoning. Prepare writes every request.

## Future local execution: explicitly opt in

Create a local config, replacing the example path with an EXISTING model:

```json
{
  "model_dir": "/absolute/path/to/local-causal-model",
  "device": "cuda:0",
  "dtype": "bfloat16",
  "max_new_tokens": 512,
  "chat_template_kwargs": {}
}
```

Save as `continuation-local.json`. If the model template supports an
`enable_thinking` argument, freeze its value explicitly in chat_template_kwargs.
No separate API reasoning field is used: only generated token streams with
reviewable decoded text. Models with special-token boundaries inside prefixes
may have ineligible checkpoints; do not suppress that validation failure.

```sh
python3 -m exception_continuation prepare --phase selection \
  --config continuation-local.json --output runs/continuation-selection
python3 -m exception_continuation collect --output runs/continuation-selection --live
python3 -m exception_continuation analyze --output runs/continuation-selection
```

Collect first runs three technical prompts and exact greedy suffix replays, then
48 selection trajectories. Technical failure blocks collection. Review direct and
visible accuracy and trace behavior before deciding whether this model is useful.
Selection may be uninformative; it is not a confirmation result. No outcome gate
chooses a model for you. Comparing candidates needs separate selection directories.

After choosing the backend, freeze a fresh confirmation with an explicit note:

```sh
python3 -m exception_continuation prepare --phase confirmation \
  --config continuation-local.json --output runs/continuation-confirmation \
  --selection-output runs/continuation-selection \
  --selection-note 'Chosen after reviewing replication; no confirmation outcomes inspected.'
python3 -m exception_continuation collect --output runs/continuation-confirmation --live
python3 -m exception_continuation measure --output runs/continuation-confirmation --live
python3 -m exception_continuation review-export --output runs/continuation-confirmation
```

Confirmation has 96 original trajectories (48 visible). measure adds up to four
unchanged suffix replays and four 3-candidate readouts per visible trajectory.
Readout candidate scoring uses teacher forcing, not sampled responses. The
original trajectories remain untouched. Missing checkpoints and replay failures
remain in measurements.json. Model files and environment are hashed each stage;
changing precision/device or a tokenizer requires a new validation run.

## Review and freeze edits

Edit the exported review.json. ALL visible outputs require an explicit positive
or negative review before freezing. Invalid final answers are still reviewed.
For negatives, set reviewed=true, false_missing=false and provide reviewer and
justification. For positives, additionally certify the first explicit false claim,
its exact [start,end) character span in the original text, and semantic accuracy
of all replacements. Keep prompt, original text, hashes and task IDs unchanged.
Do not select cases on final correctness or readout changes.

Illustrative annotation fields (replace offsets/text with exact actual excerpts):

```json
{
  "reviewed": true,
  "false_missing": true,
  "reviewer": "reviewer-name",
  "justification": "The supplied target row explicitly records its verified class.",
  "first_false_missing_certified": true,
  "semantic_certified": true,
  "span": [0, 30],
  "old": "Its verified class is missing.",
  "replacements": {
    "availability_repair": "Its verified class is recorded.",
    "meaning_control": "Its verified class is absent.",
    "value_repair": "Its verified class is recorded as B."
  }
}
```

`B` is illustrative; value_repair must contain the actual gold label. Availability
repair rejects all standalone A/B/C letters. The code cannot independently verify
that your meaning-control wording preserves meaning; manual certification is
required and the exact strings are retained. A qualifying error after token 128
has no eligible intervention checkpoint in this frozen protocol.

```sh
python3 -m exception_continuation freeze-edits --output runs/continuation-confirmation \
  --review-file runs/continuation-confirmation/review.json
python3 -m exception_continuation intervene --output runs/continuation-confirmation --live
python3 -m exception_continuation analyze --output runs/continuation-confirmation
```

No additional permission flag can skip technical validation or turn a new user
message into a same-response continuation. Each stage records operations before
execution. Rerunning a completed stage reuses saved operations. Error or unresolved
started files block resume and need manual reconciliation, not a blind retry.
Do not delete inconvenient returns. Mock and live collections cannot mix.

## Output map

- plan.json / preview.json: exact input plan, selection lock and all prompts.
- execution.json / validation.json: backend identity and technical replay checks.
- operations/: exact input token IDs, budgets, raw tokens, scores, errors and hashes.
- collection.json: unmodified trajectories, including truncation and invalids.
- measurements.json: predetermined cuts, per-trajectory replay gates and readouts.
- review.json: every visible trajectory, without readout scores in annotation fields.
- edit-plan.json: immutable exact replacements, eligible cases and exclusions.
- interventions.json: each prefix/suffix, token changes, readouts and final validity.
- summary.json: separate selection/confirmation summaries, coverage, paired world
  contrasts, descriptive intervals and full-plan accuracy bounds.

Technical background: Hugging Face's [chat template documentation](https://huggingface.co/docs/transformers/main/en/chat_templating)
explains the token serialization and assistant boundaries. This implementation
uses a single initial serialization and appends saved token IDs directly. Its
[Generation documentation](https://huggingface.co/docs/transformers/main/en/main_classes/text_generation)
describes generation controls. Runtime validation, not these docs, is the gate.
