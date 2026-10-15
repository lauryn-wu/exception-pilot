# V5 workload, memory and cost scenarios

These are pre-run counts and assumptions, not measured Qwen v5 runtimes. Run
`python -m exception_study2_v5 workload` for machine-readable ceilings. Earlier
v4 and synthetic timing are not v5 performance measurements. Actual eligible
counts are fixed only after complete originals and independent review.

| Stage | Selection (12 worlds) | Confirmation (48 worlds) |
|---|---:|---:|
| Originals | 96 | 384 |
| Visible originals reviewed | 48 | 192 |
| Original generated-token ceiling | 196608 | 786432 |
| Fresh technical generation calls | ≤33 | ≤33 |
| Technical generated-token ceiling | 3882 | 3882 |
| 2A fixed + pre-answer sequence evaluations | ≤1728 | ≤6912 |
| 2A semantic-event sequence evaluations | ≤2304 | ≤9216 |
| Combined 2A sequence evaluations before deduplication | ≤4032 | ≤16128 |
| 2B-M eligible cases | ≤48 | ≤192 |
| 2B-M fresh continuations (4/case) | ≤192 | ≤768 |
| 2B-M post-prefix candidate evaluations (24/case) | ≤1152 | ≤4608 |
| 2B-O eligible cases, continuations and evaluations | Same ceilings, separate cohort | Same ceilings, separate cohort |

The four-world pilot is part of selection: 32 originals/65536 token ceiling;
completion adds at most 64, not another 96. Confirmation is separately authorized.
Two cues × three full candidates per distinct cut. Six fixed/pre-answer positions
and eight event positions per visible response. Identical task/cut/cue computations
are shared within the combined 2A plan; nonexistent events, short answers, inexact
boundaries and missing pre-answer markers lower the counts. No 2A answers generated.
For a frozen family with N cases and original cuts k_i, exact generation ceiling is
`4 * sum(2048-k_i)`, with 4N generation operations and 24N candidate evaluations.
Failed/ambiguous operations are consumed, not resent. O's clean/mixed strata do not
add operations. Both families can include the same response but never extra worlds.
Manual review has zero paid judge calls. Two initial reviews per visible response,
third review only on disagreement, plus independently drafted/verified edits.

Across both phases at worst: 480 originals, 1920 intervention continuations,
66 technical calls = 2466 generation calls; ≤4922964 generated tokens including
technical calls. This loose ceiling assumes every original and all four arms in
both families use their entire cap, with intervention k=0 (real events have k>0).
There are ≤31680 full-candidate evaluations (20160 in 2A + 11520 in 2B).
These are NOT 31680 generated answers. Each complete candidate has two pinned
Qwen tokens; candidate teacher-forced tokens ceiling is 63360. Failed attempts may
consume compute without returning usable telemetry.

## Input token accounting

The pinned local tokenizer was actually checked offline (no model weights or network):
selection has **38880** rendered original input tokens (388–422 per task), and
confirmation **155904** (387–424). Preflight rechecks these on the actual Pod.
At assumed mean direct output 12 and visible output 1024, output totals would be
49728/198912 respectively, versus hard caps 196608/786432. Output means remain
assumptions, not replications.
Each candidate evaluation reprocesses prompt + prefix + cue + the full candidate
with the unchanged backend (no shared candidate KV cache). With at most 424 prompt tokens,
original prefixes ≤2048, and four cue tokens and two candidate tokens,
combined 2A forward tokens are at most about 9.99M/39.97M. The code records exact
context/candidate token occurrences. Edited-prefix input totals depend on frozen
replacement lengths; no finite hard bound is claimed for arbitrary proposed edits.
At ≤2048-token edited prefixes use the same 2478-token forward assumption:
2B per family ≤2.85M/11.42M candidate-forward tokens, plus generation prefill inputs.
Use frozen manifests for exact per-stage counts before dispatch.

## Memory and storage

Official pinned safetensors: **65524328560 bytes = 65.52 GB / 61.02 GiB**.
Approximate weight memory is 61.02 GiB BF16, plus KV cache, eager attention, logits,
activation/workspace and CUDA allocator overhead. Qwen's 64 layers, 8 KV heads,
128 head dimension yield ~0.25 MiB KV per token per sequence (~0.75 GiB at 3072
context tokens). Eager full-sequence scoring materializes attention and full-vocab
logits: planning peak roughly **68–77 GiB** at these contexts, not measured and not
a fit guarantee. Large edited prefixes can increase peak substantially. One 80 GB
A100/H100 is the minimum plausible single-card option; H200 141 GB has more margin.
Do not silently quantize or change kernels if OOM; retain failure and reassess.

CPU-first loader holds the whole BF16 model before GPU transfer. Plan 128 GB host
RAM, preferably 192 GB for loading/transient buffers and token data. 150–200 GB
persistent Network Volume is comfortable for one ~66 GB snapshot, 10–20 GB environment,
repo, historical audits, and 5–15 GB results/headroom. Keep ≥25 GB free once existing
assets are present; duplicated snapshots/venvs/history need more. Technical full-
vocabulary telemetry adds tens to hundreds of MB, including journal/report copies.
No v5 command downloads weights or fills a new model cache. CUDA scratch/container
disk 20–30 GB is separate from the persistent volume.

## Rental scenarios

[RunPod's public pricing page](https://www.runpod.io/pricing), checked 2026-10-14
(page updated October 8), lists A100 80 GB SXM $1.79/h, H100 PCIe 80 GB $2.89/h,
H100 SXM $3.99/h and H200 141 GB $5.29/h. Availability/region/volume rates differ;
use the actual Pod quote. No rental was launched. Storage/taxes/manual review time
are outside compute figures below.

This implementation uses batch=1, serial requests, BF16, Hugging Face Transformers
4.51.3 / torch 2.7.1 cu126, eager attention, greedy decoding, no quantization, no
vLLM/FlashAttention/prefix sharing. Planning scenarios only:

| GPU | Decode assumption | Candidate prefill assumption | Assumed setup per invocation |
|---|---:|---:|---:|
| A100 SXM 80 GB | 15–25 generated tokens/s | 500–1200 input tokens/s | 2–10 min |
| H100 PCIe 80 GB | 25–45 tokens/s | 800–2000 tokens/s | 2–10 min |
| H200 141 GB | 35–60 tokens/s | 1000–2500 tokens/s | 2–10 min |

These are broad engineering guesses, not benchmark claims. More VRAM does not
parallelize this serial code. Actual synchronized pilot timing should replace them.
For selection originals at the assumed 49728 output tokens, 38880 prompt tokens,
`time = output/decode + input/prefill + setup` gives approximately:

| GPU | Selection originals only | Rental cost |
|---|---:|---:|
| A100 SXM | 36–67 min | $1.07–$2.00 |
| H100 PCIe | 21–44 min | $1.01–$2.12 |
| H200 | 16–35 min | $1.41–$3.09 |

The all-originals-hit-2048 cap gives roughly 2.2–3.9 h A100, 1.2–2.4 h H100,
0.9–1.8 h H200 for selection, plus any setup/host overhead. Confirmation is four
times the scientific work, not four setups. Combined 2A at the token ceiling is
~2.4–5.8 h A100, 1.4–3.7 h H100, 1.2–3.0 h H200 for selection; confirmation scales
fourfold. Actual 2A contexts/eligible cuts often reduce this markedly. 2B is cohort-
dependent: budget it from `4 sum(2048-k)` generation tokens plus 24N candidate
forwards and 4N generation prefills, rather than assuming every visible trace qualifies.
Total stage cost is time-hours × quoted hourly rate. Repeated explicit commands
reload/hash weights and add setup each time; preserve these measured costs.

Recommendation: **H100 PCIe 80 GB** for cost/speed with this serial implementation
if peak memory fits; **H200 141 GB** when extra memory margin or faster execution
justifies the premium. A100 is viable but may cost similarly in total while taking
longer. Start with the explicit technical gate and bounded pilot; no full-study
runtime or low total cost is promised before their live measurements.
