import json
from pathlib import Path
import unittest

from pharos.review_guide import VERSION, available_purposes, build_review_guide, questions_for_purpose


class ReviewGuideTests(unittest.TestCase):
    def report(self, report_type="institution"):
        return {
            "report_type": report_type,
            "identity": {"id": "https://openalex.org/I1", "display_name": "Example"},
            "corpus": {"period": {"from": "2020-01-01", "to": "2024-12-31"}},
            "retrieved_at": "2026-09-14T12:00:00Z",
        }

    def test_catalogue_is_scoped_by_report_type(self):
        institution = {row["id"] for row in available_purposes("institution")}
        researcher = {row["id"] for row in available_purposes("researcher")}
        self.assertIn("publication_reconciliation", institution)
        self.assertIn("institutional_reporting", institution)
        self.assertIn("funding_evidence", institution)
        self.assertIn("open_access_evidence", institution)
        self.assertIn("adoption_due_diligence", institution)
        self.assertNotIn("source_publisher_scope", institution)
        self.assertIn("researcher_identity", researcher)
        self.assertNotIn("publication_reconciliation", researcher)

    def test_guide_is_versioned_deterministic_and_evidence_linked(self):
        first = build_review_guide(self.report(), "publication_reconciliation")
        second = build_review_guide(self.report(), "publication_reconciliation")
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], VERSION)
        self.assertEqual(first["generator"], "deterministic")
        self.assertTrue(all(item["evidence_refs"] for item in first["items"]))
        self.assertTrue(all(item["destination"] for item in first["items"]))
        self.assertTrue(all(item["action"] for item in first["items"]))
        self.assertTrue(all(item["record"] for item in first["items"]))

    def test_bibliometric_checks_explain_the_action_and_expected_record(self):
        report = self.report()
        report["coverage"] = {"primary_subject": {"count": 80, "denominator": 100, "percentage": 80.0}}
        guide = build_review_guide(report, "bibliometric_analysis")
        denominator = next(item for item in guide["items"] if item["id"] == "analysis.denominators")
        subjects = next(item for item in guide["items"] if item["id"] == "analysis.subjects")
        self.assertIn("every result", denominator["action"])
        self.assertIn("denominator", denominator["record"])
        self.assertIn("how many Works", subjects["action"])
        self.assertIn("number excluded", subjects["record"])

    def test_identity_guide_cannot_be_applied_to_institution(self):
        with self.assertRaisesRegex(ValueError, "not available"):
            build_review_guide(self.report(), "researcher_identity")

    def test_guide_contains_no_suitability_verdict(self):
        guide = build_review_guide(self.report("researcher"), "researcher_identity")
        self.assertNotIn("verdict", guide)
        self.assertIn("does not decide", " ".join(guide["limitations"]))

    def test_interview_answers_are_allowlisted_and_retained(self):
        questions = questions_for_purpose("institution", "publication_reconciliation")
        answers = {question["id"]: question["options"][0]["id"] for question in questions}
        guide = build_review_guide(self.report(), "publication_reconciliation", answers)
        self.assertEqual(guide["answers"], answers)
        self.assertTrue(all(item["priority"] in (1, 2, 3) for item in guide["items"]))
        with self.assertRaisesRegex(ValueError, "not valid"):
            build_review_guide(self.report(), "publication_reconciliation", {"tolerance": "invented"})

    def test_actual_coverage_is_included_as_an_observation(self):
        report = self.report()
        report["coverage"] = {
            "doi": {"count": 80, "denominator": 100, "percentage": 80.0},
            "primary_source": {"count": 20, "denominator": 100, "percentage": 20.0},
        }
        guide = build_review_guide(report, "publication_reconciliation")
        doi = next(item for item in guide["items"] if item["id"] == "reconciliation.doi")
        source = next(item for item in guide["items"] if item["id"] == "reconciliation.source")
        self.assertEqual(doi["observation"]["missing"], 20)
        self.assertEqual(doi["priority"], 1)
        self.assertEqual(source["priority"], 2, "coverage percentages must not silently determine sequence")

    def test_published_schemas_are_valid_json_and_versioned(self):
        root = Path(__file__).parents[1] / "schemas"
        guide_schema = json.loads((root / "pharos-review-guide-v1.schema.json").read_text())
        record_schema = json.loads((root / "pharos-review-record-v1.schema.json").read_text())
        self.assertEqual(guide_schema["properties"]["schema_version"]["const"], VERSION)
        self.assertEqual(record_schema["properties"]["schema_version"]["const"], "pharos-review-record-v1")


if __name__ == "__main__":
    unittest.main()
