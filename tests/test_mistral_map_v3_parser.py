"""Correctness-independent, bounded terminal-answer parsing matrix."""

import unittest

from exception_mistral_map_v3.parser import answer_boundary


class TerminalAnswerGrammarTests(unittest.TestCase):
    def assert_block(self, block, answer, prefix=""):
        self.assertEqual(answer_boundary(prefix + block), (answer, len(prefix)), repr(prefix + block))

    def test_ascii_marker_case_and_all_labels_and_whitespace(self):
        for marker in ("ANSWER", "answer", "Answer", "aNsWeR"):
            for label in "ABC":
                for whitespace in ("", " ", "\t", "\n", "\r\n", "\n\n", "\f\v "):
                    for prefix in ("", "A reason.\n", "A reason.\r\n\n"):
                        with self.subTest(marker=marker, label=label, whitespace=repr(whitespace), prefix=prefix):
                            self.assert_block(marker + ":" + whitespace + label + " \t\r\n\f\v", label, prefix)

    def test_every_wrapper_around_block_marker_or_label(self):
        for wrapper in ("*", "**", "_", "__", "`"):
            for label in "ABC":
                forms = (
                    f"{wrapper}ANSWER: {label}{wrapper}",
                    f"{wrapper}ANSWER{wrapper}: {label}",
                    f"{wrapper}ANSWER:{wrapper} {label}",
                    f"ANSWER: {wrapper}{label}{wrapper}",
                    f"{wrapper}ANSWER:{wrapper}\n{wrapper}{label}{wrapper}",
                    f"{wrapper}\nANSWER:\n{label}\n{wrapper}",
                )
                for form in forms:
                    with self.subTest(form=form):
                        self.assert_block(form, label)
                        self.assert_block(form, label, "Reasoning.\n")

    def test_period_inside_and_outside_wrappers(self):
        for label in "ABC":
            forms = (
                f"ANSWER: {label}.", f"ANSWER: **{label}.**", f"ANSWER: **{label}**.",
                f"**ANSWER: {label}.**", f"**ANSWER: {label}**.",
                f"**ANSWER: _{label}._**", f"**ANSWER: _{label}_.**", f"**ANSWER: _{label}_**.",
                f"**ANSWER:** `{label}.`", f"**ANSWER:** `{label}`.",
            )
            for form in forms:
                with self.subTest(form=form):
                    self.assert_block(form, label)

    def test_nested_wrappers_at_three_levels(self):
        for label in "ABC":
            for form in (
                f"**_`ANSWER: {label}`_**",
                f"**_`ANSWER`_:** {label}",
                f"**_`ANSWER:`_** **_`{label}`_**",
                f"**_ANSWER: `{label}`_**",
                f"***ANSWER: {label}***",
                f"******ANSWER: {label}******",
                f"* **ANSWER:** {label} *",
                f"**ANSWER:****{label}**",
            ):
                with self.subTest(form=form):
                    self.assert_block(form, label)

    def test_fences_all_labels_languages_and_line_endings(self):
        for fence in ("```", "~~~"):
            for language in ("", "text", "plaintext", "TEXT", "PlainText", " text "):
                for label in "ABC":
                    for newline in ("\n", "\r\n"):
                        block = newline.join(("  " + fence + language, "", f"**ANSWER:** `{label}`.", "", " " + fence)) + "\n\t"
                        with self.subTest(fence=fence, language=language, label=label, newline=repr(newline)):
                            self.assert_block(block, label)
                            self.assert_block(block, label, "Reasoning.\n")

    def test_exact_offsets_include_opening_markup_and_indent(self):
        prefix = "Unicode reasoning π🙂.\n\n"
        for block in ("  ANSWER:A", "\t**ANSWER:A**", "_\nANSWER:A\n_", "  ```text\nANSWER:A\n```", "~~~\nANSWER:A\n~~~"):
            self.assert_block(block, "A", prefix)
        self.assertEqual(answer_boundary("\n\n**ANSWER:A**"), ("A", 2))
        self.assertEqual(answer_boundary("Reasoning.\n\t**\nANSWER:A\n**"), ("A", len("Reasoning.\n")))

    def test_earlier_mentions_and_nonadjacent_blocks_do_not_blanket_reject(self):
        for prefix in (
            "The instruction says ANSWER: A, B, or C.\n",
            'A quoted example is "ANSWER: B".\n',
            "ANSWER: B was the initial hypothesis, but this is prose.\n",
            "ANSWER: B\nFurther reasoning resolves the issue.\n",
            "```text\nANSWER: B\n```\nFurther reasoning.\n",
            "```text\nReasoning shown as a code block.\n```\n",
            "~~~\nReasoning shown as a code block.\n~~~\n",
            "> ANSWER: B\n",
        ):
            self.assert_block("ANSWER: C", "C", prefix)

    def test_arbitrary_blank_whitespace_does_not_consume_structural_bound(self):
        gap = "\n" * 200
        self.assert_block("**" + gap + "ANSWER:" + gap + "A" + gap + "**", "A", "Reasoning.\n")
        self.assert_block("ANSWER:" + " " * 10000 + "A", "A")

    def test_rejects_alternatives_extra_text_quotes_and_invalid_labels(self):
        rejected = (
            "", "A", "ANSWER:", "ANSWER: a", "ANSWER: b", "ANSWER: c", "ANSWER: D",
            "ANSWER: A/B", "ANSWER: A or B", "ANSWER: A B", "ANSWER: A\nB",
            "ANSWER: A because it fits", "ANSWER: A\nMore commentary", "ANSWER: A!",
            "ANSWER: A,", "ANSWER: (A)", "ANSWER: [A]", "ANSWER: A..", "ANSWER: **A.**.",
            "**ANSWER: A.**.", '"ANSWER: A"', "'ANSWER: A'", "> ANSWER: A",
            "- ANSWER: A", "The answer is ANSWER: A", "ANS WER: A", "ANſWER: A",
            "ANSWER： A", "ANSWER:\u00a0A", "ANSWER: A\u200b", "ANSWER: **A** B",
        )
        for text in rejected:
            with self.subTest(text=repr(text)):
                self.assertEqual(answer_boundary(text), (None, None))
                self.assertEqual(answer_boundary("Reasoning.\n" + text), (None, None))

    def test_rejects_unbalanced_and_excessively_nested_wrappers(self):
        for text in (
            "**ANSWER: A*", "*ANSWER: A**", "ANSWER: **A*", "**ANSWER:** A**",
            "ANSWER: `A", "_ANSWER: A", "ANSWER: A_", "**\nANSWER: A", "`\nANSWER: A",
            "**_`*ANSWER: A*`_**", "ANSWER: **_`*A*`_**", "********ANSWER: A********",
            "**_`*ANSWER*`_**: A", "**_ANSWER: `*A*`_**",
        ):
            with self.subTest(text=text):
                self.assertEqual(answer_boundary(text), (None, None))

    def test_rejects_unmatched_invalid_or_nonterminal_fences(self):
        for text in (
            "```\nANSWER: A", "~~~text\nANSWER: A", "```python\nANSWER: A",
            "```\nANSWER: A\n~~~", "~~~\nANSWER: A\n```", "````\nANSWER: A\n````",
            "```python\nANSWER: A\n```", "```text/plaintext\nANSWER: A\n```",
            "```ANSWER: A```", "```\nReasoning.\nANSWER: A\n```",
            "```\nANSWER: A\n```\nAfterward", "```\nANSWER: A\n```.",
            "```\nANSWER: A\n``` trailing", "```\nANSWER: A\n````",
            "```python\nUnclosed code.\nANSWER: A", "~~~\nUnclosed code.\nANSWER: A",
            "~~~\n```\nANSWER: A\n```", "~~~\nANSWER: A\n~~~\n```\nANSWER: B",
        ):
            with self.subTest(text=text):
                self.assertEqual(answer_boundary(text), (None, None))

    def test_adjacent_duplicate_and_conflicting_answer_blocks_are_rejected(self):
        for first in "ABC":
            for second in "ABC":
                for prior in (f"ANSWER: {first}", f"**ANSWER: {first}**", f"```text\nANSWER:{first}\n```", f"ANSWER:\n{first}."):
                    for final in (f"ANSWER:{second}", f"**ANSWER:{second}**", f"~~~\nANSWER:{second}\n~~~"):
                        for gap in ("\n", "\n\t\n", "\n" * 100):
                            with self.subTest(prior=prior, final=final, gap=len(gap)):
                                self.assertEqual(answer_boundary("Reasoning.\n" + prior + gap + final), (None, None))

    def test_long_unrelated_prose_is_outside_candidate_window(self):
        prefix = "Ordinary reasoning mentions ANSWER: A without selecting it.\n" * 10000
        self.assert_block("**ANSWER: B**", "B", prefix)


if __name__ == "__main__":
    unittest.main()
