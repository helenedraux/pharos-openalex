"""Offline regression against the complete three-work Oxford 1900 API capture."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from pharos.backends.openalex_api import OpenAlex, observe
from pharos.cli import parser, run
from pharos.corpus import digest

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/oxford-1900.json').read_text())

class CapturedAPI(OpenAlex):
    def resolve(self, selected): return FIXTURE['identity']
    def count(self, spec): return len(FIXTURE['works'])
    def page(self, spec, cursor):
        assert cursor == '*'
        return {'meta': {'count':3, 'next_cursor':None}, 'results':FIXTURE['works']}

class OpenInstitution(unittest.TestCase):
    def test_frozen_complete_corpus_through_application_and_exports(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = Path(tmp) / 'oxford'
            args = parser().parse_args(['https://ror.org/052gg0110', '--start-year','1900','--end-year','1900','--anonymous','--out',str(out)])
            run(args, CapturedAPI)
            p = json.loads((out / 'profile.json').read_text())
            self.assertEqual(p['identity']['id'], 'https://openalex.org/I40120149')
            self.assertEqual(p['population']['eligible_works'], 3)
            self.assertEqual(p['population']['classified_works'], 3)
            self.assertEqual(p['annual_counts'][0]['count'], 3)
            self.assertAlmostEqual(sum(x['percentage'] for x in p['subject_distribution']), 100)
            self.assertEqual({x['id']: x['count'] for x in p['subject_distribution']},
                {'https://openalex.org/fields/13':2, 'https://openalex.org/fields/23':1})
            self.assertEqual(p['backend']['source_assertions_hash'], digest(FIXTURE['works']))
            self.assertEqual(len((out / 'work-ids.csv').read_text().splitlines()), 4)
            self.assertEqual(p['coverage']['resolved_authorships']['denominator'], 10)
            self.assertEqual(p['collaborators'], [])
            for raw in FIXTURE['works']:
                self.assertIn('https://openalex.org/I40120149', dict(observe(raw).institutions))
            self.assertEqual(json.loads((out / 'retrieval-receipt.yaml').read_text())['record_count_difference'], 0)
