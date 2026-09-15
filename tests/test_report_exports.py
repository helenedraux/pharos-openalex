import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pharos.backends.openalex_api import OpenAlex
from pharos.overview import overview
from pharos.report_exports import prepare, csv_bytes, table_rows, export_bytes
from pharos.server import Application


class ReportExports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures=json.loads((Path(__file__).parent/'fixtures/oxford-modern-aggregates.json').read_text())
        def get(path,params=None):
            match=next((f['response'] for f in fixtures if f['query']['path']==path and f['query']['params']==(params or {})),None)
            if match is not None: return match
            group=(params or {}).get('group_by','').split(':')[0]
            if path=='works' and group in ('primary_topic.subfield.id','primary_topic.id','sustainable_development_goals.id'): return {'group_by':[]}
            if path=='works' and group=='open_access.oa_status': return {'group_by':[{'key':'closed','key_display_name':'Closed','count':168935}]}
            if path=='works' and group=='publication_year' and any(x in (params or {}).get('filter','') for x in ('open_access.oa_status:','cited_by_count:','citation_normalized_percentile.')): return {'group_by':[]}
            if path=='works' and group=='type' and any(x in (params or {}).get('filter','') for x in ('referenced_works_count:','funders.id:','awards.id:','awards.funder_award_id:')): return {'group_by':[]}
            if path=='works' and (params or {}).get('per_page')==1 and 'sustainable_development_goals.id:!null' in (params or {}).get('filter',''): return {'meta':{'count':0},'results':[]}
            if path=='works' and (params or {}).get('per_page')==1 and any(x in (params or {}).get('filter','') for x in ('cited_by_count:','fwci:','citation_normalized_percentile.')): return {'meta':{'count':0},'results':[]}
            raise AssertionError('Unexpected query outside the frozen real corpus fixture')
        with patch.object(OpenAlex,'get',side_effect=get):
            cls.report=overview(OpenAlex(),'I40120149',2019,2025)

    def test_csv_reconciles_counts_and_preserves_denominators(self):
        p=prepare(self.report)
        rows=list(csv.DictReader(io.StringIO(csv_bytes(p).decode('utf-8-sig'))))
        annual=[r for r in rows if r['Section']=='Publications by year']
        subjects=[r for r in rows if r['Section']=='Primary Fields']
        self.assertEqual(sum(int(r['Count']) for r in annual),168935)
        self.assertEqual(sum(int(r['Count']) for r in subjects),166615)
        self.assertAlmostEqual(sum(float(r['Share']) for r in subjects),1)
        sample=[r for r in rows if r['Section']=='Published affiliation names: sample']
        self.assertTrue(all(r['Denominator']=='598' for r in sample))
        self.assertTrue(all(r['Snapshot ID']==p['export_snapshot_id'] for r in rows))

    def test_snapshot_identity_changes_with_selected_view_not_format(self):
        p=prepare(self.report)
        self.assertEqual(prepare(p)['export_snapshot_id'],p['export_snapshot_id'])
        other=copy.deepcopy(p)
        other['selected_venue_view']=copy.deepcopy(p['venues'])
        other['selected_venue_view']['work_type']='preprint'
        self.assertNotEqual(prepare(other)['export_snapshot_id'],p['export_snapshot_id'])
        data,mime=export_bytes(self.report,'json')
        self.assertEqual(mime,'application/json')
        self.assertEqual(json.loads(data)['export_snapshot_id'],p['export_snapshot_id'])

    def test_csv_source_strings_cannot_become_formulas(self):
        p=prepare(self.report)
        p['groups']['subjects'][0]['label']='=HYPERLINK("https://example.com")'
        rows=list(csv.DictReader(io.StringIO(csv_bytes(p).decode('utf-8-sig'))))
        row=next(r for r in rows if r['Section']=='Primary Fields')
        self.assertTrue(row['Recorded item'].startswith("'="))

    def test_saved_listing_collapses_equivalent_entries_without_deleting(self):
        with tempfile.TemporaryDirectory() as tmp:
            first=copy.deepcopy(self.report)
            second=copy.deepcopy(first)
            second['retrieved_at']='2099-09-08T00:00:00+00:00'
            Path(tmp,'first.json').write_text(json.dumps(first))
            Path(tmp,'second.json').write_text(json.dumps(second))
            rows=Application(tmp).saved()
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['retrieved_at'],second['retrieved_at'])
            self.assertEqual(len(list(Path(tmp).glob('*.json'))),2)

    def test_saved_listing_includes_non_institution_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=copy.deepcopy(self.report)
            report.pop('corpus',None)
            report.update(report_type='researcher',period={'from':'2012-01-01','to':'2025-12-31'})
            report['identity']={'id':'https://openalex.org/A1','display_name':'Example Researcher'}
            Path(tmp,'author-example.json').write_text(json.dumps(report))
            rows=Application(tmp).saved()
            self.assertEqual(rows[0]['kind'],'author')
            self.assertEqual((rows[0]['start'],rows[0]['end']),(2012,2025))

    def test_export_format_allowlist(self):
        with self.assertRaises(ValueError): export_bytes(self.report,'../../secret')
