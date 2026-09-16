import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from pharos.overview import CachedAPI, affiliation_audit, award_detail, candidates, evidence_signal_summary, funder_candidates, funder_overview, publisher_candidates, publisher_overview, get_groups, overview, publications, researcher_details, version_pairs, access_topics, make_spec, _name_compatible, resolve_author_identity
from pharos.backends.openalex_api import OpenAlex

class AggregateAPI:
    key=None
    def __init__(self): self.calls=[]
    query=staticmethod(OpenAlex.query)
    def resolve(self, selected):return {'id':'https://openalex.org/I1','display_name':'Test institution'}
    def get(self,path,params=None):
        self.calls.append((path,params))
        if 'group_by' in params:
            field=params['group_by'].split(':')[0]
            if field=='primary_topic.field.id':
                rows=[('https://openalex.org/fields/27','Medicine',2),('https://openalex.org/fields/unknown','Unknown',1)]
            elif field=='publication_year':rows=[('2020','2020',3)]
            elif field=='authorships.institutions.id':rows=[('https://openalex.org/I1','Home',3),('https://openalex.org/I2','Partner',2)]
            else:rows=[('article','Article',3)]
            return {'group_by':[dict(key=k,key_display_name=n,count=c) for k,n,c in rows]}
        return {'meta':{'count':3},'results':[]}

class FunderAPI(AggregateAPI):
    def get(self,path,params=None):
        if path.startswith('funders/F'):
            return {'id':'https://openalex.org/F1','display_name':'Test Funder','country_code':'GB',
                    'awards_count':4,'works_count':3,'ids':{'crossref':'1001'}}
        return super().get(path,params)

class PublisherAPI(AggregateAPI):
    def get(self,path,params=None):
        if path.startswith('publishers/P'):
            return {'id':'https://openalex.org/P1','display_name':'Test Publisher','country_codes':['GB'],
                    'hierarchy_level':0,'lineage':['https://openalex.org/P1'],'works_count':3}
        return super().get(path,params)

class OverviewTests(unittest.TestCase):
    def test_publisher_report_uses_primary_source_lineage(self):
        api=PublisherAPI()
        p=publisher_overview(api,'P1',1900,2025)
        self.assertEqual(p['report_type'],'publisher')
        self.assertIn('sources',p['groups'])
        self.assertTrue(all('primary_location.source.publisher_lineage:https://openalex.org/P1' in params['filter'] for path,params in api.calls if path=='works'))
        self.assertIn('imprints and subsidiaries',p['note'])

    def test_identity_name_rules_allow_nicknames_order_and_compound_surname_drift(self):
        self.assertTrue(_name_compatible('William J. Smith','Bill Smith'))
        self.assertTrue(_name_compatible('Karikó Katalin','Katalin Karikó'))
        self.assertTrue(_name_compatible('Ana González Sánchez','Ana Sánchez González'))
        self.assertFalse(_name_compatible('Andrew Webb','David Webb'))

    def test_identity_resolution_separates_outliers_from_partitions(self):
        core=[{'id':f'W{i}','display_name':f'Work {i}','publication_year':2000+i,'type':'article',
               'raw_names':['Bill Smith'],'raw_orcids':['O1'],'institution_ids':[],'coauthor_ids':[]} for i in range(6)]
        outlier={'id':'OLD','display_name':'Old work','publication_year':1970,'type':'article','raw_names':['W. Smith'],'raw_orcids':[],'institution_ids':[],'coauthor_ids':[]}
        result=resolve_author_identity('https://openalex.org/A1','William Smith','William Smith',core+[outlier])
        self.assertEqual(result['status'],'review_outliers')
        self.assertEqual([w['id'] for w in result['outlier_works']],['OLD'])
        second=[{'id':f'X{i}','display_name':f'Other {i}','publication_year':2000+i,'type':'article',
                 'raw_names':['David Smith'],'raw_orcids':['O2'],'institution_ids':[],'coauthor_ids':[]} for i in range(6)]
        result=resolve_author_identity('https://openalex.org/A1','William Smith','William Smith',core+second)
        self.assertEqual(result['status'],'recommend_partition')
        self.assertEqual(len(result['proposed_identities']),2)

    def test_award_detail_retains_real_grant_fields(self):
        row=award_detail({'id':'https://openalex.org/G1','display_name':'Project title','funder_award_id':'ABC-1',
            'funder':{'display_name':'Test Funder'},'funded_outputs_count':4,'amount':125000,'currency':'GBP',
            'funding_type':'grant','funder_scheme':'Discovery','start_year':2022,'end_year':2025,
            'lead_investigator':{'given_name':'Ada','family_name':'Lovelace'},
            'institution_awarded':[{'display_name':'Test University'}],'provenance':'test_source'})
        self.assertEqual(row['label'],'Project title')
        self.assertEqual(row['lead_investigator'],'Ada Lovelace')
        self.assertEqual(row['institutions'],['Test University'])
        self.assertEqual((row['amount'],row['currency']),(125000,'GBP'))

    def test_funder_report_uses_award_link_scope(self):
        api=FunderAPI()
        p=funder_overview(api,'F1',1900,2025)
        self.assertEqual(p['report_type'],'funder')
        self.assertEqual(p['population']['eligible_works'],3)
        self.assertTrue(all('awards.funder_id:https://openalex.org/F1' in params['filter'] for path,params in api.calls if path=='works'))
        self.assertIn('institutions',p['groups'])
        self.assertIn('Funding acknowledgements are incomplete',p['note'])

    def test_funder_crossref_identifier_is_resolved_exactly(self):
        api=AggregateAPI()
        api.get=lambda path,params=None: {'results':[{'id':'https://openalex.org/F1','display_name':'Test Funder','ids':{'crossref':'1001'}}]}
        rows=funder_candidates(api,'10.13039/1001')
        self.assertEqual(rows[0]['id'],'https://openalex.org/F1')
    def test_qualified_unknown_is_excluded_from_subject_denominator(self):
        p=overview(AggregateAPI(),'I1',2020,2020)
        self.assertEqual(p['population'],{'eligible_works':3,'classified_works':2,'unclassified_works':1})
        self.assertEqual(len(p['groups']['subjects']),1)
        self.assertEqual(p['groups']['subjects'][0]['percentage'],100)
        self.assertAlmostEqual(p['coverage']['primary_subject']['percentage'],66.666667)
        self.assertEqual(len(p['groups']['institutions']),1)
        self.assertEqual(p['groups']['institutions'][0]['id'],'https://openalex.org/I2')
        self.assertEqual(p['mode'],'live_aggregates')
        self.assertNotIn('narrative',p)
        self.assertNotIn('profile_specification',p)

    def test_evidence_signals_are_separate_presence_measures(self):
        result=evidence_signal_summary(AggregateAPI(),{'filter':'x'},[{'id':'article','count':3}],3)
        self.assertEqual(result['references']['overall']['count'],3)
        self.assertEqual(result['funder']['by_work_type'][0]['percentage'],100)
        self.assertIn('not the share',result['note'])

    def test_live_drilldown_keeps_corpus_scope(self):
        api=AggregateAPI()
        publications(api,'I1',2020,2021,'subject','https://openalex.org/fields/27',2)
        query=api.calls[-1][1]
        self.assertIn('authorships.institutions.id:https://openalex.org/I1',query['filter'])
        self.assertIn('primary_topic.field.id:https://openalex.org/fields/27',query['filter'])
        self.assertIn('to_publication_date:2021-12-31',query['filter'])
        self.assertEqual(query['page'],2)
        self.assertEqual(query['corpus'],'core')
        self.assertEqual(query['per_page'],20)
        publications(api,'I1',2020,2021,'source','unknown',1)
        self.assertIn('primary_location.source.id:null',api.calls[-1][1]['filter'])

    def test_untrusted_filters_and_bounds(self):
        api=AggregateAPI()
        for kind,value in [('subject','27,is_oa:true'),('year','2020,corpus:all'),('arbitrary','x')]:
            with self.assertRaises(ValueError):publications(api,'I1',2020,2021,kind,value)
        with self.assertRaises(ValueError):publications(api,'I1',2020,2021,page=501)
        with self.assertRaises(ValueError):make_spec('I1',1900,2025)
        with self.assertRaises(ValueError):make_spec('Oxford',2019,2025)

    def test_missing_metadata_drilldowns_use_boolean_filters(self):
        api=AggregateAPI()
        publications(api,'I1',2020,2021,'doi','false')
        self.assertIn('has_doi:false',api.calls[-1][1]['filter'])
        publications(api,'I1',2020,2021,'abstract','false')
        self.assertIn('has_abstract:false',api.calls[-1][1]['filter'])
        with self.assertRaises(ValueError):publications(api,'I1',2020,2021,'doi','null')

    def test_version_pairs_require_both_locations_on_same_scoped_work(self):
        api=AggregateAPI()
        version_pairs(api,'I1',2020,2021)
        query=api.calls[-1][1]
        self.assertIn('authorships.institutions.id:https://openalex.org/I1',query['filter'])
        self.assertIn('locations.version:submittedVersion',query['filter'])
        self.assertIn('locations.version:publishedVersion',query['filter'])
        self.assertIn('locations',query['select'])

    def test_access_topics_keeps_scope_and_labels_orcid_as_sample(self):
        api=AggregateAPI()
        result=access_topics(api,'I1',2020,2021)
        grouped=[params['group_by'] for path,params in api.calls if path=='works' and 'group_by' in params]
        self.assertIn('open_access.oa_status:include_unknown',grouped)
        self.assertIn('primary_topic.subfield.id:include_unknown',grouped)
        self.assertIn('primary_topic.id:include_unknown',grouped)
        self.assertEqual(result['state'],'live')
        self.assertEqual(result['orcid_sample']['population'],'sampled_target_authorships')
        self.assertEqual(result['orcid_sample']['seeds'],[61,62])

    def test_recent_researchers_are_ranked_by_recent_output(self):
        api=AggregateAPI()
        profiles=[
            {'id':'https://openalex.org/A2','display_name':'Zed','affiliations':[{'institution':{'id':'https://openalex.org/I1'},'years':[2020]}],'counts_by_year':[{'year':2020,'works_count':99}]},
            {'id':'https://openalex.org/A1','display_name':'Amy','affiliations':[{'institution':{'id':'https://openalex.org/I1'},'years':[2020]}],'counts_by_year':[{'year':2020,'works_count':1}]},
        ]
        with patch.object(api,'get',return_value={'results':profiles}):
            result=researcher_details(api,'I1',2020,2021)
        self.assertEqual([r['label'] for r in result['researchers']],['Zed','Amy'])
        self.assertEqual([r['recent_works'] for r in result['researchers']],[99,1])
        self.assertIn('not limited to works carrying this affiliation',result['note'])

    def test_recent_researchers_include_the_current_year_as_partial(self):
        api=AggregateAPI()
        current=date.today().year
        profile={'id':'https://openalex.org/A1','display_name':'Amy',
                 'affiliations':[{'institution':{'id':'https://openalex.org/I1'},'years':[current]}],
                 'counts_by_year':[{'year':current,'works_count':3}]}
        with patch.object(api,'get',return_value={'results':[profile]}):
            result=researcher_details(api,'I1',current-5,current)
        self.assertEqual((result['from_year'],result['through_year']),(current-2,current))
        self.assertTrue(result['through_year_is_partial'])
        self.assertEqual(result['researchers'][0]['recent_works'],3)

    def test_affiliation_audit_separates_mapped_and_possible_misses(self):
        api=AggregateAPI()
        responses=[
            {'meta':{'count':2},'results':[{'raw_affiliation_string':'University of Example','works_count':20,'institution_ids_final':['https://openalex.org/I1'],'countries':['GB']}]},
            {'results':[{'raw_affiliation_string':'Example University Lab','works_count':4,'institution_ids_final':[],'countries':['GB']}]},
        ]
        with patch.object(api,'get',side_effect=responses):
            result=affiliation_audit(api,'I1','University of Example','GB')
        self.assertEqual(result['matched_total'],2)
        self.assertEqual(result['matched'][0]['works_count'],20)
        self.assertEqual(result['possible_missed'][0]['label'],'Example University Lab')

    def test_name_search_returns_candidates_without_selection(self):
        api=AggregateAPI()
        with patch.object(api,'get',return_value={'results':[{'id':'https://openalex.org/I1','display_name':'A','external_id':'https://ror.org/abc'},{'id':'https://openalex.org/I2','display_name':'B'}]}) as request:
            rows=candidates(api,'University')
            self.assertEqual(len(rows),2)
            self.assertEqual(request.call_args.args,('autocomplete/institutions',{'q':'University'}))
            self.assertEqual(rows[0]['ror'],'https://ror.org/abc')

    def test_cached_query_reuses_source_and_records_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=CachedAPI(tmp)
            with patch.object(OpenAlex,'get',return_value={'meta':{'count':3}}) as remote:
                a=api.get('works',{'filter':'x'})
                b=api.get('works',{'filter':'x'})
                self.assertEqual(a,b)
                self.assertEqual(remote.call_count,1)
            self.assertEqual(api.requests[0]['response_hash'],api.requests[1]['response_hash'])
            self.assertTrue(api.requests[0]['retrieved_at'])

class ModernOxfordTests(unittest.TestCase):
    def test_frozen_live_aggregates_reconcile_and_do_not_count_unknown_as_subject(self):
        fixtures=json.loads((Path(__file__).parent/'fixtures/oxford-modern-aggregates.json').read_text())
        api=OpenAlex()
        def captured(path,params=None):
            for fixture in fixtures:
                if fixture['query']['path']==path and fixture['query']['params']==(params or {}):
                    return fixture['response']
            group=(params or {}).get('group_by','').split(':')[0]
            if path=='works' and group in ('primary_topic.subfield.id','primary_topic.id','sustainable_development_goals.id'):
                return {'group_by':[]}
            if path=='works' and group=='open_access.oa_status':
                return {'group_by':[{'key':'closed','key_display_name':'Closed','count':168935}]}
            if path=='works' and group=='publication_year' and any(x in (params or {}).get('filter','') for x in ('open_access.oa_status:','cited_by_count:','citation_normalized_percentile.')):
                return {'group_by':[]}
            if path=='works' and group=='type' and any(x in (params or {}).get('filter','') for x in ('referenced_works_count:','funders.id:','awards.id:','awards.funder_award_id:')):
                return {'group_by':[]}
            if path=='works' and (params or {}).get('per_page')==1 and 'sustainable_development_goals.id:!null' in (params or {}).get('filter',''):
                return {'meta':{'count':0},'results':[]}
            if path=='works' and (params or {}).get('per_page')==1 and any(x in (params or {}).get('filter','') for x in ('cited_by_count:','fwci:','citation_normalized_percentile.')):
                return {'meta':{'count':0},'results':[]}
            raise AssertionError('Unexpected query outside the frozen real corpus fixture')
        with patch.object(api,'get',side_effect=captured):
            p=overview(api,'I40120149',2019,2025)
        self.assertEqual(p['population']['eligible_works'],168935)
        self.assertEqual(p['population']['classified_works'],166615)
        self.assertEqual(p['population']['unclassified_works'],2320)
        self.assertEqual(sum(r['count'] for r in p['groups']['annual']),168935)
        self.assertEqual(sum(r['count'] for r in p['groups']['types']),168935)
        self.assertIn('subfields',p['groups'])
        self.assertIn('topics',p['groups'])
        self.assertIn('open_access',p)
        self.assertTrue(p['venues']['publishers'])
        self.assertEqual(p['affiliations']['sampled_works'],0)
        self.assertEqual(p['affiliations']['mode'],'live_audit')
        self.assertAlmostEqual(sum(r['percentage'] for r in p['groups']['subjects']),100,places=4)
        self.assertEqual(p['groups']['institutions'][0]['label'],'University College London')
        self.assertEqual(p['groups']['institutions'][0]['count'],11614)
        self.assertEqual(p['coverage']['doi']['count'],165985)
        self.assertEqual(p['diagnostics']['unclassified_subject']['count']['count'],2320)
        self.assertAlmostEqual(p['diagnostics']['unclassified_subject']['count']['percentage'],1.3733,places=3)
        self.assertEqual(len(p['diagnostics']['abstracts']['by_year']),7)
        self.assertEqual(p['briefing']['kind'],'deterministic')
        self.assertEqual(len(p['briefing']['sentences']),4)
        self.assertIn('Articles account for 61.2%',p['briefing']['sentences'][0]['text'])
        self.assertIn('Output has grown 15%',p['briefing']['sentences'][1]['text'])
        self.assertEqual(p['coverage_assessment']['weakest']['key'],'abstract')
        self.assertIn('abstract coverage at 80.8%',p['coverage_assessment']['line'])
        self.assertNotIn('label',p['coverage_assessment']['metrics'][0])
        self.assertEqual(p['groups']['institutions'][0]['country_code'],'GB')
        self.assertEqual(p['groups']['institutions'][0]['collaboration_scope'],'domestic')
        self.assertEqual(p['funding']['top_funders'][0]['label'],'Wellcome Trust')
        self.assertEqual(len(p['work_type_trend']),7)
        self.assertEqual(len(p['field_trend']),7)
        self.assertEqual(p['affiliations']['other_institutions'],[])

class ServerBoundaryTests(unittest.TestCase):
    def test_loopback_origin_and_host_required(self):
        from pharos.server import Deployment, Handler
        from types import SimpleNamespace
        deployment=Deployment('local','127.0.0.1',8765,frozenset(('127.0.0.1:8765',)),frozenset(('http://127.0.0.1:8765',)))
        request=SimpleNamespace(server=SimpleNamespace(server_port=8765,deployment=deployment),headers={'Host':'127.0.0.1:8765'},command='GET')
        self.assertTrue(Handler.trusted(request))
        request.headers['Origin']='https://example.com'
        self.assertFalse(Handler.trusted(request))
        request.headers={'Host':'example.com:8765'}
        self.assertFalse(Handler.trusted(request))
        request.headers={'Host':'127.0.0.1:8765','Sec-Fetch-Site':'cross-site'}
        self.assertFalse(Handler.trusted(request))


class CoverageTests(unittest.TestCase):
    def test_raw_strings_require_target_mapping_and_deduplicate_per_work(self):
        from pharos.overview import summarize_affiliations
        works=[{'id':'W1','authorships':[
            {'institutions':[{'id':'I1'}], 'affiliations':[{'raw_affiliation_string':'Department A','institution_ids':['I1']},{'raw_affiliation_string':'Other university','institution_ids':['I2']}]},
            {'institutions':[{'id':'I1'}], 'affiliations':[{'raw_affiliation_string':'Department A','institution_ids':['I1']}]},
            {'institutions':[{'id':'I1'}], 'raw_affiliation_strings':['Unmapped text']} ]},
            {'id':'W2','authorships':[{'institutions':[{'id':'I2'}],'affiliations':[{'raw_affiliation_string':'Other university','institution_ids':['I2']}]}]}]
        result=summarize_affiliations(works,'I1')
        self.assertEqual(len(result['rows']),1)
        self.assertEqual(result['rows'][0]['label'],'Department A')
        self.assertEqual(result['rows'][0]['count'],1)
        self.assertEqual(result['mapped_work_coverage']['denominator'],2)
        self.assertEqual(result['target_authorships_without_mapped_string'],1)

    def test_core_names_sub_affiliations_and_researchers_are_separate(self):
        from pharos.overview import summarize_affiliations
        works=[{'id':'W1','display_name':'One','publication_year':2022,'authorships':[{
            'author':{'id':'https://openalex.org/A1','display_name':'Jane Doe'},
            'institutions':[{'id':'I1'}],
            'affiliations':[{'raw_affiliation_string':"Jane's Lab, Physiology dept, Oxford University, UK",'institution_ids':['I1']}]
        }]},{'id':'W2','display_name':'Two','publication_year':2023,'authorships':[{
            'author':{'id':'https://openalex.org/A1','display_name':'Jane Doe'},
            'institutions':[{'id':'I1'}],
            'affiliations':[{'raw_affiliation_string':'Faculty of Physics, University of Oxford, Oxford, UK','institution_ids':['I1']}]
        }]}]
        result=summarize_affiliations(works,'I1','University of Oxford')
        self.assertEqual({r['label'] for r in result['core_names']},{'Oxford University','University of Oxford'})
        self.assertEqual({r['label'] for r in result['sub_affiliations']},{"Jane's Lab, Physiology dept",'Faculty of Physics'})
        self.assertEqual(result['researchers']['unique_count'],1)
        self.assertEqual([r['count'] for r in result['researchers']['by_year']],[1,1])

    def test_publisher_drilldown_keeps_selected_work_type(self):
        api=AggregateAPI()
        publications(api,'I1',2020,2021,'publisher','https://openalex.org/P123',1,'preprint')
        query=api.calls[-1][1]
        self.assertIn('primary_location.source.host_organization:https://openalex.org/P123',query['filter'])
        self.assertIn('type:preprint',query['filter'])
        self.assertNotIn('open_access',query['select'])
        with self.assertRaises(ValueError):publications(api,'I1',2020,2021,work_type='article,is_oa:true')
