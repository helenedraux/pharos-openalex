import io
import json
import unittest

from pharos.review_assist import ReviewAssistError, assistance_status, build_packet, generate_review_draft
from pharos.review_guide import build_review_guide


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *_): pass


class ReviewAssistTests(unittest.TestCase):
    def guide_and_item(self):
        report={"report_type":"institution","identity":{"id":"https://openalex.org/I1","display_name":"Example"},"corpus":{"period":{"from":"2020-01-01","to":"2024-12-31"}},"coverage":{"doi":{"count":80,"denominator":100,"percentage":80.0}}}
        guide=build_review_guide(report,"publication_reconciliation")
        return guide,next(row for row in guide["items"] if row["id"] == "reconciliation.doi")

    def test_unconfigured_assistance_is_explicitly_unavailable(self):
        self.assertFalse(assistance_status("", "")["available"])

    def test_packet_contains_only_controlled_check_and_optional_context(self):
        guide,item=self.guide_and_item()
        packet=build_packet(guide,item,"I will compare with our repository")
        self.assertEqual(packet["check"]["observation"]["missing"],20)
        self.assertEqual(packet["check"]["evidence_refs"],item["evidence_refs"])
        self.assertNotIn("report",packet)

    def test_model_draft_has_provenance_and_cannot_assign_status(self):
        guide,item=self.guide_and_item()
        captured={}
        def opener(request,timeout):
            captured["payload"]=json.loads(request.data)
            return Response(json.dumps({"choices":[{"message":{"content":"The saved report records 80 DOI assertions among 100 Works. Compare the remaining records with the local repository before documenting limitations."}}]}).encode())
        result=generate_review_draft(guide,item,endpoint="http://127.0.0.1:8080/v1/chat/completions",model="test-slm",opener=opener)
        self.assertEqual(result["kind"],"model_generated_draft")
        self.assertEqual(result["model"],"test-slm")
        self.assertEqual(result["location"],"local server")
        self.assertNotIn("status",result)
        self.assertIn("not a suitability verdict",result["warning"])
        self.assertIn("Do not decide suitability",captured["payload"]["messages"][0]["content"])

    def test_verdict_language_is_rejected(self):
        guide,item=self.guide_and_item()
        def opener(_request,timeout=None):
            return Response(b'{"choices":[{"message":{"content":"This is fit for purpose."}}]}')
        with self.assertRaisesRegex(ReviewAssistError,"verdict boundary"):
            generate_review_draft(guide,item,endpoint="http://127.0.0.1:8080/v1/chat/completions",model="test",opener=opener)

    def test_context_is_bounded(self):
        guide,item=self.guide_and_item()
        with self.assertRaisesRegex(ValueError,"1,000"):
            build_packet(guide,item,"x"*1001)

    def test_remote_model_endpoint_is_rejected(self):
        guide,item=self.guide_and_item()
        with self.assertRaisesRegex(ReviewAssistError,"loopback"):
            generate_review_draft(guide,item,endpoint="https://models.example/v1/chat/completions",model="test")


if __name__ == "__main__": unittest.main()
