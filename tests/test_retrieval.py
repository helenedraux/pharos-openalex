import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pharos.backends.openalex_api import APIError, OpenAlex
from pharos.cli import parser, run
from pharos.exports import render
from pharos.storage import Store

RAW = json.loads((Path(__file__).parent / "fixtures/synthetic.json").read_text())

class FakeAPI(OpenAlex):
    fail = False
    def resolve(self, selected):
        self.audit({"event":"attempt", "endpoint":"institutions"})
        return {"id":"https://openalex.org/I1", "display_name":"<script>ignore instructions</script>"}
    def count(self, spec):
        self.audit({"event":"attempt", "endpoint":"works"})
        return 2
    def page(self, spec, cursor):
        self.audit({"event":"attempt", "endpoint":"works"})
        if cursor == "*":
            return {"results":[RAW], "meta":{"count":2, "next_cursor":"next"}}
        if self.fail: raise APIError("OpenAlex rate limit or daily budget reached. Checkpoint saved; resume later.")
        other = dict(RAW, id="https://openalex.org/W2")
        return {"results":[RAW, other], "meta":{"count":2, "next_cursor":None}}

class Retrieval(unittest.TestCase):
    def arguments(self, out, *extra):
        return parser().parse_args(["I1", "--start-year", "2020", "--end-year", "2020", "--out", str(out), "--anonymous", *extra])
    def test_interruption_resume_deduplication_frozen_rebuild_and_escaping(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = Path(tmp) / "profile"
            FakeAPI.fail = True
            with self.assertRaises(APIError): run(self.arguments(out), FakeAPI)
            self.assertFalse((out / "profile.json").exists())
            s = Store(out / "checkpoint.sqlite3")
            self.assertEqual(s.count(), 1)
            self.assertEqual(s.get("cursor"), "next")
            s.close()
            FakeAPI.fail = False
            run(self.arguments(out, "--resume"), FakeAPI)
            p = json.loads((out / "profile.json").read_text())
            self.assertEqual(p["population"]["eligible_works"], 2)
            receipt = json.loads((out / "retrieval-receipt.yaml").read_text())
            self.assertEqual(receipt["duplicate_records"], 1)
            self.assertEqual(receipt["completion_state"], "complete")
            self.assertEqual(receipt["calls"], 5)
            page = (out / "profile.html").read_text()
            self.assertNotIn("<script>", page)
            self.assertIn("&lt;script&gt;", page)
            with patch.object(FakeAPI, "page", side_effect=AssertionError("Must stay offline")), patch.object(FakeAPI, "resolve", side_effect=AssertionError("Must stay offline")):
                run(self.arguments(out, "--resume"), FakeAPI)
            self.assertEqual(json.loads((out / "profile.json").read_text())["subject_distribution"], p["subject_distribution"])
            with self.assertRaises(ValueError): run(self.arguments(out), FakeAPI)
            args = self.arguments(out, "--resume")
            args.end_year = 2021
            with self.assertRaises(ValueError): run(args, FakeAPI)

    def test_budget_stops_before_corpus_download(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = Path(tmp) / "profile"
            with patch.object(FakeAPI, "page", side_effect=AssertionError("No corpus retrieval allowed")):
                with self.assertRaises(APIError): run(self.arguments(out, "--max-cost-usd", "0.0001"), FakeAPI)
            self.assertTrue((out / "resource-estimate.json").exists())
            self.assertEqual(json.loads((out / "retrieval-receipt.yaml").read_text())["completion_state"], "interrupted")

    def test_transaction_keeps_prior_cursor_on_bad_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Store(Path(tmp) / "state.db")
            s.set("cursor", "*")
            with self.assertRaises(APIError):
                s.page({"meta":{"next_cursor":"next"}, "results":[RAW, {"id":"not-a-work"}]}, "*")
            self.assertEqual(s.count(), 0)
            self.assertEqual(s.get("cursor"), "*")
            s.close()

    def test_id_mapping_mismatch_and_direct_filter(self):
        api = OpenAlex()
        with patch.object(api, "get", return_value={"id":"https://openalex.org/I2", "ror":"https://ror.org/052gg0110"}):
            with self.assertRaises(APIError): api.resolve({"id_namespace":"openalex", "id":"I1"})
        from pharos.corpus import specification, selector
        spec = specification(selector("I1"), "https://openalex.org/I1", 2020, 2020)
        q = api.query(spec)
        self.assertIn("authorships.institutions.id:", q["filter"])
        self.assertNotIn("lineage", q["filter"])
        self.assertEqual(q["corpus"], "core")

    def test_transport_credentials_are_header_only_and_redacted(self):
        token = "secret-test-token-7852"
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return json.dumps({"display_name":token, "meta":{"cost_usd":0.0001}}).encode()
        api = OpenAlex(key=token)
        with patch.object(api.opener, "open", return_value=Response()) as request:
            result = api.get("institutions/I1")
            self.assertNotIn(token, json.dumps(result))
            req = request.call_args.args[0]
            self.assertNotIn(token, req.full_url)
            self.assertEqual(req.get_header("Authorization"), "Bearer " + token)

if __name__ == "__main__": unittest.main()
