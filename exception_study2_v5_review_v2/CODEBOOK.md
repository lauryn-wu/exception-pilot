# Study 2 Review v2.0 frozen semantic codebook

Scope: only the saved generated pre-answer text, including truncated or invalid-answer
originals. The source table is authoritative evidence, never a generated assertion.
Offsets are Python Unicode character offsets, half-open. A statement means an
endorsed assertion, not merely a keyword, quote, conditional, question or negation.
The target row index is zero-based among vehicle data rows; exclude both Markdown
header and separator. Index 9 means vehicle 10, table line index 11.

## Six independent phenomena

- A / acknowledgment: explicitly and correctly reports the target's RECORDED Verified
  class. A correct guess or prediction is insufficient. Reconstructed target cells
  can acknowledge the source. A does not imply that later reasoning retains it.
- M / erasure (Family M): falsely asserts the supplied target Verified class is
  missing, unknown, blank, unavailable or unreadable, including reconstructed cells.
  Prediction uncertainty, other fields/entities, hypotheticals and negations do not
  qualify. A structured false reconstruction still needs an assertion-mode check.
- X / miscopy (Family M): reports or reconstructs the target's RECORDED value as a
  different A/B/C value. An inferred alternative is P, not X; unknown is M, not X.
- C / conflict (Family O): generated text explicitly recognizes a mismatch between
  the target's recorded value and its pattern-derived alternative. Analyst-observed
  inconsistency, or juxtaposition without recognition, is insufficient.
- P / substitution (observational sidecar): endorses a pattern-derived target class
  different from the recorded class. Neither prior A nor explicit O is required.
  A wrong final answer by itself is not evidence. P never changes v5 event schemas.
- O / override (Family O): AFTER a correct A, explicitly argues for preferring an
  inferred alternative OVER that recorded value. Requires a linked earlier A,
  recognition of the relationship, and preference. Conflict or wrong prediction
  alone is insufficient. The accepted A must end before the O begins.

## Examples (target T, recorded C, peer pattern A)

| Phenomenon | Positive | Negative / insufficient | Ambiguous (uncertain) |
|---|---|---|---|
| A | T's recorded Verified class is C. | I predict C for T. | T seems to have C. |
| M | T: Verified class: MISSING. | T's verified value is not missing. | I cannot tell whether T's entry is readable. |
| X | T's recorded Verified class is A. | From its features I predict A. | T: A (column/meaning unclear). |
| C | T's recorded C conflicts with the pattern's A. | Recorded C. The pattern suggests A. | There may be an inconsistency somewhere. |
| P | Based on the peer pattern, T belongs to A. | I considered A, but reject that inference. | The pattern might suggest A or B. |
| O | T's recorded value is C. I prefer the inferred A over that recorded C. | T's C conflicts with pattern A; retain C. | Recorded C. Perhaps A should take priority? |

Hypothetical/nonendorsed examples, for EVERY event: "If T's recorded value were C,
...", "Suppose the entry were missing", "Imagine it were copied as A", "If C
conflicted with A", "If the pattern predicted A", "One could prefer A, but I do
not." Do not convert these into positive events. Likewise "It is false that ..."
negates its embedded claim. A quoted assertion is not endorsed merely by quotation.
"The previous draft says 'Verified class: MISSING', which is wrong" is not a new
M assertion; "The entry is MISSING. Correction: it is C" contains an earlier M
and later A. Retain both exact locations; later repair does not erase history.
"Recorded C. I prefer inferred A over C. Correction: retain C" still contains O.
Statements about another plate or its Doors/Audit marker are not target Verified
class events. Source values can be compared mechanically; endorsement and inferred
relationships require independent semantic judgments.

## Resolution and limits

All source text is presegmented before judges run. Canonical IDs denote locations,
not invented quotations. Candidates combine structural and independent semantic
extraction; IDs are deduplicated by location/event. Structural facts never certify
semantics. J1/J2 independently classify every candidate/event with separate checks;
conditional J3 sees the same evidence and no votes. Contradictory mechanical checks
cannot be outvoted. Event existence is resolved before earliest qualifying location
selection. Earlier uncertain candidates block first-occurrence certification.

A separate full-text negative auditor reviews all statements without seeing votes
or candidate omissions. Its candidates receive independent J1/J2 (conditional J3)
verification, including previously rejected candidates. Failed extraction/audit or
incomplete full-text coverage never establishes absence. Disagreement between the
two phases remains uncertain; it cannot be silently overridden. A negative audit
is still fallible: passing is not proof of exhaustive human-level semantic recall.

No human review is required for this detection procedure. Unresolved evidence is
uncertain. Existing independent intervention-edit verification remains mandatory;
automating that verification needs a separate protocol amendment. Repeated spans
without a unique legacy 40-character anchor cannot be exported as present. Complex
compound clauses that cannot meet the existing nonoverlap rule for A→O remain
uncertain. Do not adjust this codebook using held-out or intervention outcomes.
