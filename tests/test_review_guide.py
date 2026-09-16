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
        self.assertIn("interoperability_assessment", institution)
        self.assertNotIn("source_publisher_scope", institution)
        self.assertIn("researcher_identity", researcher)
        self.assertIn("interoperability_assessment", researcher)
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
        self.assertTrue(all(item["cannot_decide"] for item in first["items"]))
        self.assertTrue(all(item["next_step"] for item in first["items"]))
        self.assertTrue(all(item["measurement_definition"] for item in first["items"]))
        self.assertTrue(all(item["requirement"] for item in first["items"]))
        self.assertNotIn("score", first)

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

    def test_guide_contains_a_provisional_use_specific_readiness_result(self):
        guide = build_review_guide(self.report("researcher"), "researcher_identity")
        self.assertEqual(guide["readiness"]["status"],"validation_needed")
        self.assertIn("provisional", guide["readiness"]["note"].lower())
        self.assertNotIn("score", guide)

    def test_explicit_saved_scope_is_not_treated_as_unresolved(self):
        guide = build_review_guide(self.report(), "publication_reconciliation")
        scope = next(item for item in guide["items"] if item["id"] == "common.scope")
        self.assertEqual(scope["provisional_status"], "validation_needed")
        self.assertIn("does not confirm", scope["observed"]["summary"])

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
        guide_schema = json.loads((root / "pharos-review-guide-v2.schema.json").read_text())
        record_schema = json.loads((root / "pharos-review-record-v2.schema.json").read_text())
        current_guide = json.loads((root / "pharos-review-guide-v3.schema.json").read_text())
        current_record = json.loads((root / "pharos-review-record-v3.schema.json").read_text())
        matrix = json.loads((root / "pharos-readiness-matrix-v1.schema.json").read_text())
        self.assertEqual(current_guide["properties"]["schema_version"]["const"], VERSION)
        self.assertEqual(current_record["properties"]["schema_version"]["const"], "pharos-review-record-v3")
        self.assertEqual(guide_schema["properties"]["schema_version"]["const"], "pharos-review-guide-v2")
        self.assertEqual(record_schema["properties"]["schema_version"]["const"], "pharos-review-record-v2")
        self.assertEqual(matrix["properties"]["schema_version"]["const"], "pharos-readiness-matrix-v1")
        self.assertTrue((root / "pharos-review-guide-v1.schema.json").exists())
        self.assertTrue((root / "pharos-review-record-v1.schema.json").exists())

    def test_case_level_guides_have_a_validation_ceiling(self):
        guide=build_review_guide(self.report("researcher"),"researcher_identity")
        identity=next(item for item in guide["items"] if item["id"]=="identity.selection")
        self.assertEqual(identity["requirement"]["status_ceiling"],"validation_needed")
        self.assertEqual(identity["measurement_definition"]["unit"],"count")

    def test_interoperability_separates_automatic_and_destination_tests(self):
        guide=build_review_guide(self.report(),"publication_reconciliation")
        kinds={item["test_type"] for item in guide["interoperability"]}
        self.assertEqual(kinds,{"automatic","destination_specific"})

    def test_numeric_defaults_create_transparent_provisional_results(self):
        report=self.report();report["coverage"]={"doi":{"count":79,"denominator":100,"percentage":79.0},"primary_source":{"count":95,"denominator":100,"percentage":95.0}}
        guide=build_review_guide(report,"publication_reconciliation")
        doi=next(item for item in guide["items"] if item["measurement_definition"]["id"]=="doi")
        self.assertEqual(doi["requirement"]["numeric_default"],80.0)
        self.assertEqual(doi["provisional_status"],"does_not_meet_configured_requirement")
        self.assertEqual(guide["readiness"]["status"],"not_supported")

    def test_items_publish_join_and_benchmark_boundaries(self):
        report=self.report();report["coverage"]={"abstract":{"count":75,"denominator":100,"percentage":75.0}}
        guide=build_review_guide(report,"discovery")
        abstract=next(item for item in guide["items"] if item["measurement_definition"]["id"]=="abstract")
        self.assertIn("required_join",abstract["interoperability"])
        self.assertTrue(abstract["benchmark"]["eligible"])
        self.assertEqual(abstract["benchmark"]["status"],"not_calculated")


if __name__ == "__main__":
    unittest.main()
