import copy
import json
import unittest
from pathlib import Path
from pharos.corpus import selector, specification, digest
from pharos.backends.openalex_api import observe
from pharos.profile import calculate

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic.json"

class Contracts(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads(FIXTURE.read_text())
        self.spec = specification(selector("I1"), "https://openalex.org/I1", 2020, 2020)

    def test_resolution_inputs_and_no_silent_names(self):
        self.assertEqual(selector("https://openalex.org/i123")["id"], "I123")
        self.assertEqual(selector("052gg0110")["id"], "https://ror.org/052gg0110")
        for name in ("Oxford", "https://evil.org/I1", "I0"):
            with self.assertRaises(ValueError): selector(name)

    def test_hash_tracks_defaults(self):
        other = dict(self.spec, entity_projection="hierarchy")
        self.assertNotEqual(digest(self.spec), digest(other))
        self.assertEqual(digest(self.spec), digest(dict(reversed(list(self.spec.items())))))

    def test_denominators_unknowns_whole_counts_and_retractions(self):
        missing = {"id":"https://openalex.org/W2", "publication_date":"2020-01-01", "publication_year":2020}
        p = calculate([observe(self.raw), observe(missing)], self.spec, {}, {"retrieved_at":"2026-09-07T00:00:00Z"})
        self.assertEqual(p["population"]["eligible_works"], 2)
        self.assertEqual(p["population"]["classified_works"], 1)
        self.assertEqual(p["subject_distribution"][0]["percentage"], 100)
        self.assertEqual(p["collaborators"][0]["count"], 1)
        self.assertEqual(p["retracted_works"]["count"], 1)
        self.assertEqual(p["open_access"]["count"], 1)
        self.assertEqual(p["open_access"]["denominator"], 2)
        self.assertEqual(p["coverage"]["oa_information"]["count"], 1)
        self.assertEqual(p["coverage"]["resolved_authorships"]["denominator"], 2)
        self.assertEqual({x["id"] for x in p["work_type_distribution"]}, {"novel-type", "unknown"})

    def test_empty_and_current_year(self):
        from datetime import date
        year = date.today().year
        spec = specification(selector("I1"), "https://openalex.org/I1", year, year)
        p = calculate([], spec, {}, {"retrieved_at":f"{year}-09-07T00:00:00Z"})
        self.assertIsNone(p["open_access"]["percentage"])
        self.assertFalse(p["annual_counts"][0]["complete_year"])
        self.assertTrue(any("current year" in w for w in p["warnings"]))

if __name__ == "__main__": unittest.main()
