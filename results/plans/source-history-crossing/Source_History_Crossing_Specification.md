# Source × reasoning-history crossing: implementation specification

Prepared 18 October 2026. Status: offline specification and audited input manifest; no new model calls, repository changes, or implementation have been made.

## Scientific question

Does changing the original target record change the eventual classification when the entire supplied reasoning prefix is held fixed?

This is a test of causal influence of context text under fresh continuation. It is not an assay of continuous hidden-state retention, intentional override, or natural mediation of every reasoning error.

The first study uses one checkpoint, k=512, to examine the late-history regime motivated by the completed source-report experiment. This is an exploratory follow-up designed after observing earlier results; freeze the protocol before collecting new outcomes.

## Population and exact workload

- Existing remaining-world Qwen3-32B original-question/visible-reasoning trajectories, worlds 004–059.
- Include every world with both original variant prefixes eligible at k512 under existing boundary checks.
- 52 worlds, 104 saved histories, 208 planned and distinct continuation contexts.
- Exclude worlds 011, 026, 027, and 059 because one variant lacks an eligible 512-token prefix. Do not substitute a shorter or event-selected checkpoint.
- No selection by original correctness, source-report failure, missingness statements, or any new outcome.
- These results apply to the eligible late-prefix population, not all 56 worlds or all reasoning trajectories.

Let r0 and r1 denote the two target-record labels, and p the third, feature-pattern label. These are roles; their actual A/B/C assignments vary by world. Retain all existing assignments rather than forcing p=C.

Each world has four cells:
1. original input IDs from variant0 + first512 output IDs from variant0;
2. original input IDs from variant1 + first512 output IDs from variant0;
3. original input IDs from variant0 + first512 output IDs from variant1;
4. original input IDs from variant1 + first512 output IDs from variant1.

The history-origin label is provenance. It must never be reported as the label the history asserts without inspecting that history.

## Offline checks already completed

For all52 eligible worlds:
- Source variants share the target plate, features, question, reasoning instruction, and all other table content.
- Full prompt strings have equal length and differ at exactly one character: the target's class.
- Original model-input ID sequences have equal length and differ at exactly one token.
- Each history is exactly512 saved output tokens and matches the archived eligible source-report prefix.
- All four crossed contexts therefore have equal token length within a world.
- The two source labels and pattern label are all distinct.
- All208 context hashes are distinct; there is no duplicate generation to eliminate.

The accompanying manifest records each source/history parent hash, role label, token-context hash, input length, and the 208cell identities. Its hash is:
18c9731cf794e69708f1cfe5d20b3789eb04d09a34505fd1d190cc6093116629

Original source-main plan hash:
0bbad97bda79e9c249f7cea110b1f2fd96671470f190faae64181e3267f77379

Remaining source identity:
- source_hash: e35ee9fb0e61276bddf83192c9e204b22918fa84b8575e98cb2ab0b00ea48a90
- plan_hash: 7a7ad23ac63d8c06c1e68fd2a1232f159da7f1201ac1d970a07618394cedfc22
- backend_hash: a7a7eb1cd399fd4a3a74c0cee48546c6db219840c5ccc960d4c984dc04a3b1c4

## Continuation procedure

Reuse the existing token-ID backend and durable operation journal. Implement this as a separate versioned experiment that leaves frozen prior protocols and outputs intact.

For source s and history h:
context_ids = source_row[s].input_ids + source_row[h].raw.tokens[:512]

Continue the same assistant turn. Do not close it, add a user transcription request, insert a reminder, append ANSWER/Final answer cues, or reconstruct the history through a new chat rendering.

Use the pinned original Qwen3-32B model/tokenizer revision 9216db5781bf21249d130ec9da846c4624c16137 and unchanged verified backend: BF16, batch1, eager attention, deterministic greedy generation, original plain-visible-assistant interface with enable_thinking=False. The visible reasoning remains part of the assistant output; this setting is not a request to remove it.

Generate at most1536 new tokens: original v5 budget2048 minus supplied512. Preserve the original EOS handling and terminal parser. Score prefix text plus new suffix against the current source label r_s, not the history-origin label r_h. A terminal-format sensitivity may be separately labeled; never silently change the frozen primary parser.

All four cells require fresh prefills and fresh continuations, including the two diagonal cells. Cached natural final answers cannot replace diagonal outcomes: prior technical checks showed that a fresh-prefix continuation can differ from the original incremental-generation suffix. Report diagonal agreement with the original trajectory descriptively; do not use exact suffix agreement as a scientific pass gate.

The offline environment lacks the pinned model/tokenizer assets. Implementation must perform tokenizer-only context/decode checks on Runpod before loading model weights. Reuse the existing backend identity validation; do not silently waive it or rerun completed scientific calibrations.

## Primary outcome and estimand

For each world, let Y_sh be the valid final class after source variant s and history variant h. For any label r, I(Y_sh=r) is1 when that valid class was returned and0 otherwise.

For each fixed history h:
R_h = 0.5 × [(I(Y_0h=r0) − I(Y_1h=r0)) + (I(Y_1h=r1) − I(Y_0h=r1))].

World score R_w = (R_0 + R_1)/2. Primary summary is the equal-weight mean across the52 worlds.

Interpretation:
- +1: both histories yield answers that fully track the source-label change.
- 0: no net shift toward the changed source label. This may include fixed-label or pattern responses and is not evidence of forgetting.
- −1: answers systematically track the opposite source variant.

Report all categorical outcomes and transitions alongside the score; do not let a single mean conceal pattern choices or failures.

Completed but unparseable/truncated outcomes contribute zero to label indicators and remain separate visible categories. Unavailable calls are not silently treated as returned incorrect answers: show completion coverage and worst-case bounds for the planned-cohort score. A complete-world estimate, if needed, is explicitly secondary with its denominator. Low responsiveness is not a clean scientific finding if output completion is poor.

Use descriptive whole-world bootstrap intervals, preserving all four cells per sampled world (10,000 draws; fixed seed2026101801). The independent analysis unit is the world, not208 independent generations.

## Secondary outcomes

- Accuracy against the current source for each of the four cells.
- Pattern-label response rate, wrong-other-record-label rate, invalid/truncated/unavailable counts.
- For each fixed source, whether switching history changes the categorical answer; report the full transition table. Call this whole-history influence, not following a presumed belief or origin label.
- Same-history source-switch transition tables in r0/r1/p coordinates.
- Diagonal final-answer and suffix agreement with original saved trajectories, descriptive only.
- Completion lengths, stop reasons, actual generation wall time, backend setup time, and new/reused operation counts.

No extra source-transcription endpoint, likelihood readout, semantic judge, activation collection, or second checkpoint is part of this first run.

## Efficiency and execution contract

- Reuse original trajectories and saved token IDs; do not recollect them.
- Reuse source-main snapshots for input/boundary validation if convenient; do not generate new source reports.
- Do not blindly call the old intervention stage: it automatically computes two historical cue readouts for every arm.
- Build a dedicated plan and use existing generation/journal components without those extra measurements.
- Preparation and inspection remain CPU/tokenizer-only and show exact planned/new/reusable counts before any weight load.
- Load the model once when executable live work exists. A completed rerun should inspect/reuse results without loading weights.
- Stable content-addressed operation identities must bind source row, history row, checkpoint, context IDs, backend identity, generation budget, and parser/protocol version.
- Follow the existing durable dispatch/return rules. Never regenerate a committed return. Preserve ambiguous/failed operations explicitly and do not silently retry terminal operations.
- Freeze a balanced deterministic order of the four conditions across worlds before generation.
- Do not vary checkpoint, wording, cohort, or token budget in response to preliminary outcomes.

## Compute scale

- Exact call count:208.
- Maximum generated-token budget:319,488.
- The104 saved diagonal suffixes contain46,015 tokens in total; median397, mean442.45.
- Twice that historical total is92,030 tokens, an illustrative planning proxy if crossed continuations had comparable lengths. It is not a runtime promise or bound.
- The preceding four-minute source-report run generated only short labels; its runtime must not be used to predict this run.
- Report any runtime estimate from actual measured continuation throughput and make its assumptions explicit.

## Meaningful implementation verification

Test only the concrete risks:
- source/history indices and current-source answer keys cannot be swapped;
- source inputs differ only at the verified target label and prefixes remain byte/token exact;
- no source-report bridge or readout cue enters continuation inputs;
- source-responsiveness gives +1/0/−1 on tracking/constant/reversed synthetic outcomes;
- parser failures and unavailable operations remain distinguishable;
- durable resume never duplicates returned generations and completed inspection does not load weights.

Validate all planned contexts offline before the GPU run. No full historical experiment or semantic judge suite needs rerunning.

## How this guides later research

Strong source responsiveness means the original source retains causal influence under these supplied histories. Whole-history effects motivate localization of the influential content. Persistent pattern responses motivate testing the feature argument or task framing. Mixed outcomes should be reported rather than forced into one explanation.

A subsequent local text edit can distinguish a false availability claim from other history content. That later study should be chosen from this evidence; it is not automatically launched.

No result here alone establishes internal forgetting, intentional override, or that any specific sentence mediated the naturally generated direct-versus-reasoning gap.

