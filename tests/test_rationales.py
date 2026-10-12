import json
from pathlib import Path
import tempfile
import unittest

from code_rationales import audit_run, code_text, reasoning_text


class RationaleTests(unittest.TestCase):
    def test_four_classes(self):
        cases = [
            ("UX1234 has cold features, suggesting class A.", "A", "never_stated"),
            ("UX1234: Verified class: MISSING", "A", "relabeled_missing"),
            ("UX1234 has recorded class B, but I choose class A.", "A", "stated_then_overridden"),
            ("UX1234 is listed as class B.", "B", "stated_and_followed"),
        ]
        for text, answer, category in cases:
            with self.subTest(category=category):
                self.assertEqual(code_text(text, "UX1234", "B", answer)["class"], category)

    def test_multiline_and_legacy_disagreement(self):
        text = "UX1234 has these attributes:\n - Description: cold\n - Transmission: Manual\n - Verified class: B\n\nANSWER: A"
        result = code_text(text, "UX1234", "B", "A")
        self.assertTrue(result["states_recorded_class"])
        self.assertFalse(result["legacy_states_recorded_class"])
        self.assertIn("Verified class: B", result["record_evidence"])

    def test_inferential_comparison_not_record_evidence(self):
        result = code_text("UX1234 characteristics align with both class A and class B.", "UX1234", "B", "A")
        self.assertFalse(result["states_recorded_class"])
        self.assertTrue(result["legacy_states_recorded_class"])
        for text in ("UX1234 shares characteristics with both Class A and Class B vehicles.",
                     "UX1234 has a manual transmission, more common in class B vehicles like UX1234.",
                     "UX1234 is cold. Given these factors, the initial prediction is class B."):
            self.assertFalse(code_text(text, "UX1234", "B", "A")["states_recorded_class"])

    def test_group_membership_and_copied_row(self):
        for text in ("Class B: UX1234 (Manual), UY9999 (Automatic)",
                     "Doors: Class A (UY9999) and Class B (UX1234).",
                     "- UX1234 (Class B): Arctic station, automatic, cloth, four doors.",
                     "- UX1234: Manual - Class B (currently marked)"):
            self.assertTrue(code_text(text, "UX1234", "B", "A")["states_recorded_class"])

    def test_other_row_boundary(self):
        result = code_text("UX1234 attributes:\nUY9999 has verified class B.", "UX1234", "B", "A", ["UY9999"])
        self.assertFalse(result["states_recorded_class"])

    def test_missing_priority_negation_and_question(self):
        self.assertEqual(code_text("UX1234 has verified class B.\nUX1234: class: MISSING", "UX1234", "B", "B")["class"], "relabeled_missing")
        self.assertFalse(code_text("Is UX1234 missing? UX1234 is not missing.", "UX1234", "B", "A")["relabels_missing"])
        self.assertFalse(code_text("Which class does UX1234 belong to?", "UX1234", "B", "A")["relabels_missing"])
        self.assertTrue(code_text("UX1234 | ? |", "UX1234", "B", "A")["relabels_missing"])
        self.assertTrue(code_text("- UX1234: ?", "UX1234", "B", "A")["relabels_missing"])

    def test_json_fields_and_escaped_lines(self):
        text = json.dumps({"initial_answer": "B", "reasoning": "UX1234:\\nVerified class: B", "final_answer": "A"})
        self.assertEqual(reasoning_text(text), "UX1234:\nVerified class: B")
        self.assertEqual(code_text(text, "UX1234", "B", "A")["class"], "stated_then_overridden")

    def test_refuses_writing_into_source(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "outside"):
                audit_run(directory, Path(directory) / "analysis")


if __name__ == "__main__":
    unittest.main()
