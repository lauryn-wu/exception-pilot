# Staged v5 workload, storage and runtime assumptions

Run `python -m exception_study2_v5 workload` for machine-readable ceilings. One
60-world schedule: the first four are an operational pilot, not selected worlds.
No Qwen runtime, peak VRAM, event prevalence or paid judge performance is measured
by this offline implementation. Never infer behavioral success from these counts.

| Stage | Pilot: 4 worlds | Remaining: 56 | Full: 60 |
|---|---:|---:|---:|
| Original attempts | 32 | 448 | 480 |
| Visible originals | 16 | 224 | 240 |
| Original output-token cap | 65,536 | 917,504 | 983,040 |
| Technical generation calls | ≤33 | 0 (same run) | ≤33 |
| Technical output-token cap | 3,882 | 0 | 3,882 |
| 2A fixed/pre-answer candidate sequences | ≤576 | ≤8,064 | ≤8,640 |
| 2A event candidate sequences | ≤768 | ≤10,752 | ≤11,520 |
| Total 2A sequences before deduplication | ≤1,344 | ≤18,816 | ≤20,160 |
| Eligible cases per M or O family | ≤16 | ≤224 | ≤240 |
| Fresh continuations per family | ≤64 | ≤896 | ≤960 |
| Candidate evaluations per family | ≤384 | ≤5,376 | ≤5,760 |

Six fixed/pre-answer positions plus eight event positions, two cues and three complete
candidates. Ineligible cuts/events reduce actual counts. A combined measurement plan
deduplicates exact task/cut/cue aliases; separate fixed/event plans may repeat aliases
but remain within the displayed sum. Do not run combined plus separate plans and
claim the same budget. Downstream `remaining` scope avoids recomputing the pilot.

Per family with N frozen cases at original cuts k_i: exactly 4N attempted continuations,
24N candidate evaluations, output ceiling `4*sum(2048-k_i)`. Frozen edit lengths affect
input/VRAM but do not change remaining budgets. Failed/ambiguous attempts are consumed.
No 2A answers are generated. Across the full run, loose maxima are **2,433 generation
calls** (480 originals + 1,920 M/O arms + 33 technical), **4,919,082 generated tokens**,
and **31,680 candidate sequences / 63,360 teacher-forced candidate tokens**. This loose
output bound allows k=0 for every intervention; actual eligible events have k>0.
Manual independent review uses zero paid API calls. There are 480 initial reviews
(2×240 visible), plus adjudication only on disagreement and separate edit verification.

## Storage budget

Plan for approximately **200 GB persistent Network Volume at `/workspace`**, including
existing history. Weights: **65,524,328,560 bytes = 65.52 GB / 61.02 GiB** for the pinned
BF16 snapshot. Environment roughly 10–20 GB. Avoid duplicate model snapshots/caches;
keep at least 25 GB free after actual history and environment are accounted for.
20–30 GB container/scratch space is separate; persistent outputs belong on the volume.

Conservative uncompressed JSON estimates for the full 60-world run, assuming edited
prefixes remain near the 2048-token original cap and no extra experimental reruns:

| Data | Planning allowance |
|---|---:|
| Plan, 480 originals, request/start/return journals, compact boundary fingerprints | 0.2–0.6 GB |
| 2A candidate readouts, context IDs, journals and checkpoint manifests | 0.3–1.0 GB |
| Independent reviews, event annotations, drafts/verifications | 0.02–0.15 GB |
| Both families' maximum 1,920 continuations plus associated readouts/journals | 0.4–1.5 GB |
| Separate technical full-vocabulary telemetry | 0.1–0.5 GB |
| Total practical scientific/technical artifact reserve | 2–5 GB; allow 5–10 GB with exports/backups |

These are engineering allowances, not measurements or hard caps; arbitrary long edits,
JSON formatting, archive copies and extra runs increase them. Save lossless token IDs
and compact boundary fingerprints, not repeated prefix text at every token. No dense
hidden activations or every-step full-vocabulary logits are saved for scientific
originals, readouts or interventions. Technical telemetry stays separately labeled.

**Future activations are not included in that budget.** BF16 residual vectors at 5,120
hidden dimensions cost 10,240 bytes/token/layer. At 2,048 generated tokens for 240 visible
trajectories: about **5.03 GB for one layer**, **322.1 GB for all 64 layers**, excluding
prompts/metadata. All 480 originals at that cap double those amounts; intervention
replays can add terabytes. No activation extractor exists here. A later probe study
must predeclare layers/cuts/storage, stream or selectively retain data, and must not
assume the 200 GB volume can hold indefinite dense activation caches.

## Input tokens, memory and time

The pinned tokenizer is audited offline over all 480 frozen prompts; exact counts
are in `audits/study2-v5-staged/tokenizer-audit.json`. Run local preflight on the Pod.
Output counts are unknown until collected. A planning mean of 12 tokens/direct and
1,024/visible yields 16,576 pilot output tokens and 248,640 across all 60 worlds,
compared with hard caps above. For candidate scoring, this backend reprocesses each
prompt+prefix+cue+candidate independently. With at most 430 prompt tokens, 2,048 prefix,
4 cue and 2 candidate tokens, full 2A ceiling is ~50.1M forward token occurrences;
pilot ~3.34M. Actual eligibility/lengths substantially affect this. Arbitrarily long
edited prefixes have no finite bound until edits freeze; budget from their manifests.

Existing backend: batch one, serial Hugging Face Transformers 4.51.3 / torch 2.7.1 cu126,
eager attention, native BF16, greedy, no quantization, no vLLM/FlashAttention/prefix
cache sharing. Approximate weights 61.02 GiB + KV ~0.25 MiB/token/sequence + eager
attention/full-vocabulary scoring logits/workspace. Planning peak **68–77 GiB** near
these contexts, not measured or guaranteed. H100/A100 80 GB is plausible; H200 141 GB
has more headroom. Host 128–192 GB accommodates CPU-first weight loading. OOM is a
preserved failure, not permission to quantize or change scientific settings.

Existing planning assumptions (not benchmark results): A100 15–25 generated tokens/s,
500–1,200 prefill tokens/s; H100 PCIe 25–45 and 800–2,000; H200 35–60 and 1,000–2,500.
Model hashing/loading adds roughly 2–10 minutes per invocation. Using approximately
13k pilot input tokens and the assumed 16,576 outputs, pilot originals take roughly
13–29 min A100, 8–22 min H100, 7–18 min H200. At the 65,536 output cap they can take
46–83, 26–54, or 20–42 minutes respectively. Technical validation, scoring, manual
review and interventions are additional. Full originals are 15 times the scientific
token work, not 15 setups. Replace these estimates with the synchronized pilot timings.

The prior pricing audit on 2026-10-14 recorded [RunPod public rates](https://www.runpod.io/pricing)
of $1.79/h A100 SXM, $2.89/h H100 PCIe and $5.29/h H200. Treat these as dated planning
quotes; region, availability, storage and taxes vary. GPU cost is actual hours × the
Pod's quoted rate. Human review while a GPU is running also incurs rental cost.
No cloud resources or paid calls were launched for this amendment.
