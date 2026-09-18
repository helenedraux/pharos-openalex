"""Low-cost live aggregates, deliberately separate from a downloaded profile."""
import json
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from pharos.backends.openalex_api import OpenAlex, APIError
from pharos.corpus import selector, specification, digest
from pharos.exports import save_json
from pharos.profile import measure
from pharos.resources import RATE_CARD, estimate
from pharos.storage import now

GROUPS = {
    'annual': 'publication_year', 'subjects': 'primary_topic.field.id',
    'domains': 'primary_topic.domain.id',
    'types': 'type',
    'institutions': 'authorships.institutions.id', 'countries': 'authorships.countries',
    'sources': 'primary_location.source.id',
}
DRILL_FILTERS = {'year':'publication_year', 'subject':'primary_topic.field.id',
    'institution':'authorships.institutions.id', 'country':'authorships.countries',
    'source':'primary_location.source.id', 'type':'type', 'publisher':'primary_location.source.host_organization',
    'author':'authorships.author.id', 'doi':'has_doi', 'abstract':'has_abstract',
    'oa':'open_access.oa_status','sdg':'sustainable_development_goals.id',
    'cited':'cited_by_count','uncited':'cited_by_count','top10':'citation_normalized_percentile.is_in_top_10_percent',
    'top1':'citation_normalized_percentile.is_in_top_1_percent'}
AWARD_SELECT='id,display_name,description,funder_award_id,funder,funded_outputs_count,amount,currency,funding_type,funder_scheme,start_year,end_year,landing_page_url,provenance,lead_investigator,institution_awarded'

def dated_filter(base, start, end):
    if not (1900 <= start <= end <= date.today().year): raise ValueError('Choose a valid report period.')
    period={'from':f'{start}-01-01','to':f'{end}-12-31'}
    return ','.join([base,f'from_publication_date:{period["from"]}',f'to_publication_date:{period["to"]}']),period

class CachedAPI(OpenAlex):
    """Successful responses cached by public query and UTC day; never cache credentials."""
    def __init__(self, directory, key=None, key_provider=None):
        super().__init__(key=key,key_provider=key_provider)
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.requests = []

    def get(self, path, params=None):
        query = {'path':path, 'params':params or {}, 'day':str(datetime.now(timezone.utc).date())}
        filename = self.directory / (digest(query).split(':')[1] + '.json')
        if filename.exists():
            cached = json.loads(filename.read_text())
        else:
            cached = {'query':query, 'retrieved_at':now(), 'response':super().get(path, params)}
            save_json(filename, cached)
        self.requests.append({'path':path, 'params':params or {}, 'retrieved_at':cached['retrieved_at'],
                              'response_hash':digest(cached['response']),
                              'reported_cost_usd':(cached['response'].get('meta') or {}).get('cost_usd')})
        return cached['response']


def candidates(api, text):
    text = text.strip()
    if not text or len(text) > 160: raise ValueError('Enter an institution name or identifier (up to 160 characters).')
    try:
        exact = selector(text)
    except ValueError:
        exact = None
    if exact:
        rows = [api.resolve(exact)]
    else:
        rows = api.get('autocomplete/institutions', {'q':text})['results'][:8]
    return [{**{k:r.get(k) for k in ('id','display_name','country_code','type','homepage_url','works_count')},
             'ror':r.get('ror') or r.get('external_id'),'hint':r.get('hint')} for r in rows]


def author_candidates(api, text):
    text=text.strip()
    if not text or len(text)>160: raise ValueError('Enter a researcher name, ORCID or OpenAlex Author ID (up to 160 characters).')
    token=text.removeprefix('https://openalex.org/').upper()
    orcid=text.removeprefix('https://orcid.org/').upper()
    if re.fullmatch(r'A\d+',token): rows=[api.get('authors/'+token)]
    elif re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]',orcid):
        rows=api.get('authors',{'filter':'orcid:'+orcid,'per_page':8}).get('results',[])
    else: rows=api.get('autocomplete/authors',{'q':text}).get('results',[])[:8]
    return [{'id':r.get('id'),'display_name':r.get('display_name'),'orcid':r.get('orcid'),
             'works_count':r.get('works_count'),'cited_by_count':r.get('cited_by_count'),
             'hint':r.get('hint'),'orcid':r.get('orcid') or r.get('external_id'),
             'last_known_institutions':r.get('last_known_institutions') or []} for r in rows if r.get('id')]


def source_candidates(api, text):
    text=text.strip()
    if not text or len(text)>160: raise ValueError('Enter a source name, ISSN or OpenAlex Source ID (up to 160 characters).')
    token=text.removeprefix('https://openalex.org/').upper()
    issn=text.removeprefix('https://issn.org/resource/ISSN/').upper()
    if re.fullmatch(r'S\d+',token): rows=[api.get('sources/'+token)]
    elif re.fullmatch(r'\d{4}-\d{3}[\dX]',issn): rows=api.get('sources',{'filter':'issn:'+issn,'per_page':8}).get('results',[])
    else: rows=api.get('autocomplete/sources',{'q':text}).get('results',[])[:8]
    return [{'id':r.get('id'),'display_name':r.get('display_name'),'issn_l':r.get('issn_l') or r.get('external_id'),'issn':r.get('issn') or [],
             'type':r.get('type'),'host_organization_name':r.get('host_organization_name'),'hint':r.get('hint'),'works_count':r.get('works_count')} for r in rows if r.get('id')]


def funder_candidates(api, text):
    text=text.strip()
    if not text or len(text)>160: raise ValueError('Enter a funder name, Crossref Funder ID or OpenAlex Funder ID (up to 160 characters).')
    token=text.removeprefix('https://openalex.org/').upper()
    crossref=text.removeprefix('https://doi.org/').removeprefix('http://doi.org/').removeprefix('doi:').strip()
    if re.fullmatch(r'F\d+',token): rows=[api.get('funders/'+token)]
    elif re.fullmatch(r'(?:10\.13039/)?\d+',crossref):
        crossref=crossref.removeprefix('10.13039/')
        rows=api.get('funders',{'filter':'ids.crossref:'+crossref,'per_page':8}).get('results',[])
    else: rows=api.get('autocomplete/funders',{'q':text}).get('results',[])[:8]
    return [{'id':r.get('id'),'display_name':r.get('display_name'),'country_code':r.get('country_code'),
             'description':r.get('description'),'works_count':r.get('works_count'),'awards_count':r.get('awards_count'),
             'hint':r.get('hint'),'ids':r.get('ids') or ({'crossref':r.get('external_id')} if r.get('external_id') else {})} for r in rows if r.get('id')]


def publisher_candidates(api, text):
    text=text.strip()
    if not text or len(text)>160: raise ValueError('Enter a publisher name or OpenAlex Publisher ID (up to 160 characters).')
    token=text.removeprefix('https://openalex.org/').upper()
    rows=[api.get('publishers/'+token)] if re.fullmatch(r'P\d+',token) else api.get('autocomplete/publishers',{'q':text}).get('results',[])[:8]
    return [{'id':r.get('id'),'display_name':r.get('display_name'),'country_codes':r.get('country_codes') or [],
             'hierarchy_level':r.get('hierarchy_level'),'parent_publisher':r.get('parent_publisher'),
             'works_count':r.get('works_count'),'hint':r.get('hint'),'ids':r.get('ids') or {}} for r in rows if r.get('id')]


def source_overview(api, source, start, end, progress=lambda message:None):
    token=source.removeprefix('https://openalex.org/').upper()
    if not re.fullmatch(r'S\d+',token): raise ValueError('Confirm a source from the search results first.')
    identity=api.get('sources/'+token); source_id=identity.get('id'); filters,period=dated_filter(f'primary_location.source.id:{source_id}',start,end); query={'filter':filters,'corpus':'core'}
    progress('Counting works in this source'); n=get_count(api,query)
    groups={}
    for key,field in [('annual','publication_year'),('types','type'),('domains','primary_topic.domain.id'),
                      ('subjects','primary_topic.field.id'),('subfields','primary_topic.subfield.id'),('topics','primary_topic.id'),
                      ('sdgs','sustainable_development_goals.id'),('institutions','authorships.institutions.id'),('funders','funders.id')]:
        rows=get_groups(api,query,field); denominator=sum(r['count'] for r in rows if r['id']!='unknown') if key=='subjects' else n
        groups[key]=shares([r for r in rows if r['id']!='unknown'],denominator,'classified_works' if key=='subjects' else 'eligible_works')
    groups['annual']=sorted([dict(r,complete_year=int(r['id'])<date.today().year) for r in groups['annual'] if re.fullmatch(r'\d{4}',r['id'])],key=lambda r:int(r['id']))
    progress('Reading coverage and access')
    coverage={'doi':measure(get_count(api,query,'has_doi:true'),n),'abstract':measure(get_count(api,query,'has_abstract:true'),n)}
    access=open_access_summary(api,query,groups['annual'],n); citations=citation_summary(api,query,groups['annual'],n)
    return {'schema_version':'1.0','report_type':'source','implementation_version':3,'mode':'live_aggregates','identity':identity,
            'period':period,'retrieved_at':now(),'population':{'eligible_works':n},'coverage':coverage,'groups':groups,
            'open_access':access,'citations':citations,
            'note':'This report covers core-corpus works whose primary location is this OpenAlex Source. A Source may be a journal, repository, conference series, book series, or platform; verify the type and ISSNs before interpreting it as a journal.'}


def funder_overview(api, funder, start, end, progress=lambda message:None):
    token=funder.removeprefix('https://openalex.org/').upper()
    if not re.fullmatch(r'F\d+',token): raise ValueError('Confirm a funder from the search results first.')
    identity=api.get('funders/'+token); funder_id=identity.get('id')
    filters,period=dated_filter(f'awards.funder_id:{funder_id}',start,end); query={'filter':filters,'corpus':'core'}
    progress('Counting works linked to this funder')
    n=get_count(api,query); groups={}
    for key,field in [('annual','publication_year'),('types','type'),('domains','primary_topic.domain.id'),
                      ('subjects','primary_topic.field.id'),('subfields','primary_topic.subfield.id'),('topics','primary_topic.id'),
                      ('sdgs','sustainable_development_goals.id'),('institutions','authorships.institutions.id')]:
        progress('Reading '+key)
        rows=get_groups(api,query,field)
        denominator=sum(r['count'] for r in rows if r['id']!='unknown') if key=='subjects' else n
        groups[key]=shares([r for r in rows if r['id']!='unknown'],denominator,'classified_works' if key=='subjects' else 'eligible_works')
    groups['annual']=sorted([dict(r,complete_year=int(r['id'])<date.today().year) for r in groups['annual'] if re.fullmatch(r'\d{4}',r['id'])],key=lambda r:int(r['id']))
    progress('Reading affiliation coverage by year')
    institution_years=[]
    for annual in groups['annual']:
        year=annual['id']; year_query={**query,'filter':query['filter']+',publication_year:'+year}
        progress(f'Reading affiliation coverage for {year}')
        recorded=get_count(api,year_query,'authorships.institutions.id:!null')
        leading=next((row for row in get_groups(api,year_query,'authorships.institutions.id') if row['id']!='unknown'),None)
        institution_years.append({'year':int(year),'linked_works':annual['count'],'with_institution':recorded,
                                  'coverage':measure(recorded,annual['count']),
                                  'leading_institution':leading and {'id':leading['id'],'label':leading['label'],'count':leading['count']}})
    progress('Reading coverage and access')
    coverage={'doi':measure(get_count(api,query,'has_doi:true'),n),'abstract':measure(get_count(api,query,'has_abstract:true'),n)}
    access=open_access_summary(api,query,groups['annual'],n); citations=citation_summary(api,query,groups['annual'],n)
    progress('Reading grant records')
    award_response=api.get('awards',{'filter':'funder.id:'+funder_id,'sort':'funded_outputs_count:desc','per_page':25,'select':AWARD_SELECT})
    detailed_response=api.get('awards',{'filter':'funder.id:'+funder_id+',amount:>0','sort':'amount:desc','per_page':25,'select':AWARD_SELECT})
    start_year_response=api.get('awards',{'filter':'funder.id:'+funder_id,'group_by':'start_year','per_page':200})
    currency_response=api.get('awards',{'filter':'funder.id:'+funder_id+',amount:>0','group_by':'currency','per_page':200})
    start_years=[{'id':str(r.get('key')),'label':str(r.get('key')),'count':r.get('count',0)} for r in start_year_response.get('group_by') or [] if str(r.get('key','')).isdigit()]
    currencies=[{'id':str(r.get('key')),'label':str(r.get('key')),'count':r.get('count',0)} for r in currency_response.get('group_by') or [] if r.get('key')]
    progress('Reading global funding context')
    funders_with_awards=api.get('funders',{'filter':'awards_count:>0','per_page':1})
    funders_with_works=api.get('funders',{'filter':'works_count:>0','per_page':1})
    award_funder_countries=api.get('funders',{'filter':'awards_count:>0','group_by':'country_code','per_page':20})
    work_funder_countries=api.get('funders',{'filter':'works_count:>0','group_by':'country_code','per_page':20})
    recipient_countries=api.get('awards',{'group_by':'institution_awarded.country_code','per_page':20})
    global_award_years=api.get('awards',{'group_by':'start_year','per_page':200})
    global_work_years=api.get('works',{'filter':'awards.funder_id:!null','group_by':'publication_year','per_page':200})
    grouped=lambda response:[{'id':str(r.get('key')),'label':r.get('key_display_name') or str(r.get('key')),'count':r.get('count',0)} for r in response.get('group_by') or [] if r.get('key') is not None]
    award_year_rows=[r for r in grouped(global_award_years) if r['id'].isdigit() and start<=int(r['id'])<=end]
    work_year_rows=[r for r in grouped(global_work_years) if r['id'].isdigit() and start<=int(r['id'])<=end]
    global_context={'funders_with_awards':(funders_with_awards.get('meta') or {}).get('count',0),
                    'funders_with_linked_works':(funders_with_works.get('meta') or {}).get('count',0),
                    'award_records':(recipient_countries.get('meta') or {}).get('count',0),
                    'linked_works':(global_work_years.get('meta') or {}).get('count',0),
                    'award_funder_countries':grouped(award_funder_countries),'work_funder_countries':grouped(work_funder_countries),
                    'recipient_countries':grouped(recipient_countries),
                    'award_years':sorted(award_year_rows,key=lambda r:int(r['id'])),
                    'work_years':sorted(work_year_rows,key=lambda r:int(r['id']))}
    awards={'count':(award_response.get('meta') or {}).get('count',0),
            'detailed_count':(detailed_response.get('meta') or {}).get('count',0),
            'detailed_rows':[award_detail(r) for r in detailed_response.get('results') or []],
            'rows':[award_detail(r) for r in award_response.get('results') or []],
            'start_years':sorted(start_years,key=lambda r:int(r['id'])), 'currencies':currencies,
            'note':'OpenAlex Award records vary by upstream source. Missing titles, amounts, dates, investigators or recipient institutions mean those fields were not supplied.'}
    return {'schema_version':'1.0','report_type':'funder','implementation_version':8,'mode':'live_aggregates','identity':identity,
            'period':period,'retrieved_at':now(),'population':{'eligible_works':n},'coverage':coverage,'groups':groups,
            'open_access':access,'citations':citations,'awards':awards,'institution_years':institution_years,'global_context':global_context,'queries':list(getattr(api,'requests',[])),
            'note':'OpenAlex exposes two funding traces. Direct Award records can link a grant to a funder and, when supplied, a lead investigator, recipient institution, and resulting publications. Work-level funding acknowledgements establish a recorded association between a Work and a funder or Award, but do not assign recipient, investigator, or administering roles to the Work’s authors or affiliations. Funding acknowledgements are incomplete, and both traces have coverage gaps.'}


def publisher_overview(api, publisher, start, end, progress=lambda message:None):
    token=publisher.removeprefix('https://openalex.org/').upper()
    if not re.fullmatch(r'P\d+',token): raise ValueError('Confirm a publisher from the search results first.')
    identity=api.get('publishers/'+token); publisher_id=identity.get('id')
    filters,period=dated_filter(f'primary_location.source.publisher_lineage:{publisher_id}',start,end); query={'filter':filters,'corpus':'core'}
    progress('Counting works published in this lineage'); n=get_count(api,query); groups={}
    for key,field in [('annual','publication_year'),('types','type'),('subjects','primary_topic.field.id'),
                      ('sdgs','sustainable_development_goals.id'),('sources','primary_location.source.id'),
                      ('institutions','authorships.institutions.id')]:
        progress('Reading '+key); rows=get_groups(api,query,field)
        denominator=sum(r['count'] for r in rows if r['id']!='unknown') if key=='subjects' else n
        groups[key]=shares([r for r in rows if r['id']!='unknown'],denominator,'classified_works' if key=='subjects' else 'eligible_works')
    groups['annual']=sorted([dict(r,complete_year=int(r['id'])<date.today().year) for r in groups['annual'] if re.fullmatch(r'\d{4}',r['id'])],key=lambda r:int(r['id']))
    progress('Reading coverage and access')
    coverage={'doi':measure(get_count(api,query,'has_doi:true'),n),'abstract':measure(get_count(api,query,'has_abstract:true'),n)}
    return {'schema_version':'1.0','report_type':'publisher','implementation_version':3,'mode':'live_aggregates','identity':identity,
            'period':period,'retrieved_at':now(),'population':{'eligible_works':n},'coverage':coverage,'groups':groups,
            'open_access':open_access_summary(api,query,groups['annual'],n),'citations':citation_summary(api,query,groups['annual'],n),
            'queries':list(getattr(api,'requests',[])),
            'note':'This report covers core-corpus works whose primary source belongs to this OpenAlex Publisher lineage. It follows recorded publisher ancestry, so it can include imprints and subsidiaries; it is not a commercial market-share measure.'}


def author_overview(api, author, start, end, progress=lambda message:None):
    token=author.removeprefix('https://openalex.org/').upper()
    if not re.fullmatch(r'A\d+',token): raise ValueError('Confirm a researcher from the search results first.')
    identity=api.get('authors/'+token)
    author_id=identity.get('id')
    filters=[f'authorships.author.id:{author_id}']
    query={'filter':','.join(filters),'corpus':'core'}
    progress('Counting this profile’s works')
    n=get_count(api,query)
    groups={}
    for key,field in [('annual','publication_year'),('types','type'),('subjects','primary_topic.field.id'),('institutions','authorships.institutions.id'),('sdgs','sustainable_development_goals.id')]:
        progress('Reading '+key)
        rows=get_groups(api,query,field)
        if key=='institutions': rows=[r for r in rows if r['id']!='unknown']
        denominator=sum(r['count'] for r in rows if r['id']!='unknown') if key=='subjects' else n
        groups[key]=shares([r for r in rows if r['id']!='unknown'],denominator,'classified_works' if key=='subjects' else 'eligible_works')
    observed={int(row['id']):row for row in groups['annual'] if re.fullmatch(r'\d{4}',row['id'])}
    groups['annual']=[dict(observed.get(year,{'id':str(year),'label':str(year),'count':0,'denominator':n,'percentage':0}),complete_year=year<date.today().year) for year in range(min(observed),max(observed)+1)] if observed else []
    open_access=open_access_summary(api,query,groups['annual'],n)
    citations=citation_summary(api,query,groups['annual'],n)
    progress('Reading field change')
    top_fields=groups['subjects'][:6]
    field_by_year={r['id']:filtered_groups(api,query,'publication_year','primary_topic.field.id:'+r['id']) for r in top_fields}
    field_trend=[]
    for annual in groups['annual']:
        rows=[]
        for field in top_fields:
            count=next((r['count'] for r in field_by_year[field['id']] if r['id']==annual['id']),0)
            rows.append({'id':field['id'],'label':field['label'],**measure(count,annual['count'],'annual_works')})
        field_trend.append({'year':annual['id'],'total':annual['count'],'rows':sorted(rows,key=lambda r:(-r['count'],r['label']))})
    progress('Reading SDG change')
    top_sdgs=groups['sdgs'][:6]
    sdg_by_year={r['id']:filtered_groups(api,query,'publication_year','sustainable_development_goals.id:'+r['id']) for r in top_sdgs}
    sdg_trend=[]
    for annual in groups['annual']:
        rows=[]
        for sdg in top_sdgs:
            count=next((r['count'] for r in sdg_by_year[sdg['id']] if r['id']==annual['id']),0)
            rows.append({'id':sdg['id'],'label':sdg['label'],**measure(count,annual['count'],'annual_works')})
        sdg_trend.append({'year':annual['id'],'total':annual['count'],'rows':sorted(rows,key=lambda r:(-r['count'],r['label']))})
    progress('Reading work-type change')
    top_types=groups['types'][:6]
    type_by_year={r['id']:filtered_groups(api,query,'publication_year','type:'+r['id']) for r in top_types}
    work_type_trend=[]
    for annual in groups['annual']:
        rows=[]
        for work_type in top_types:
            count=next((r['count'] for r in type_by_year[work_type['id']] if r['id']==annual['id']),0)
            rows.append({'id':work_type['id'],'label':work_type['label'],**measure(count,annual['count'],'annual_works')})
        work_type_trend.append({'year':annual['id'],'total':annual['count'],'rows':sorted(rows,key=lambda r:(-r['count'],r['label']))})
    doi=measure(get_count(api,query,'has_doi:true'),n)
    progress('Inspecting author-name evidence')
    identity_evidence=author_name_evidence(api,query,author_id,identity.get('full_name'),identity.get('orcid'),n)
    work_evidence=identity_evidence.pop('_work_evidence',[])
    identity_resolution=resolve_author_identity(author_id,identity.get('display_name'),identity.get('full_name'),work_evidence)
    identity_resolution['merge_candidates']=find_merge_candidates(api,identity,identity_evidence)
    award_ids=[r['id'] for r in identity_evidence['awards'][:50] if re.fullmatch(r'https://openalex.org/G\d+',r['id'])]
    award_response=api.get('awards',{'filter':'id:'+'|'.join(award_ids),'per_page':50,'select':AWARD_SELECT}) if award_ids else {'results':[]}
    details={r.get('id'):award_detail(r) for r in award_response.get('results') or []}
    identity_evidence['awards']=[dict(r,detail=details.get(r['id'])) for r in identity_evidence['awards']]
    return {'schema_version':'1.0','report_type':'researcher','implementation_version':12,'mode':'live_aggregates',
            'identity':{'id':author_id,'display_name':identity.get('display_name') or author_id,'full_name':identity.get('full_name'),
                        'raw_author_names':identity.get('raw_author_names') or [],'orcid':identity.get('orcid'),
                        'works_count':identity.get('works_count'),'cited_by_count':identity.get('cited_by_count'),
                        'affiliations':identity.get('affiliations') or [],
                        'last_known_institutions':identity.get('last_known_institutions') or []},
            'period':None,'retrieved_at':now(),'population':{'eligible_works':n},
            'coverage':{'doi':doi},'groups':groups,'field_trend':field_trend,'sdg_trend':sdg_trend,'work_type_trend':work_type_trend,'open_access':open_access,'citations':citations,'identity_evidence':identity_evidence,'identity_resolution':identity_resolution,
            'note':'This career view includes every core-corpus work linked to the selected OpenAlex Author profile, with no publication-date restriction. OpenAlex documents merging and splitting as known failure modes of its algorithmic author resolution. Compare the work-level names, ORCID assertions, and affiliation history before treating the profile as one person.',
            'queries':list(getattr(api,'requests',[]))}


def author_name_evidence(api, query, author_id, full_name, profile_orcid, expected):
    names=Counter(); works_by_name={}; coauthors=Counter(); coauthor_labels={}; coauthor_works={}; awards=Counter(); award_labels={}; award_works={}; institution_labels={}; institution_works={}; raw_orcids=Counter(); work_evidence=[]; inspected=0; exact_orcid_works=0; cursor='*'
    while cursor and inspected < 10000:
        response=api.get('works',dict(query,per_page=100,cursor=cursor,select='id,display_name,publication_year,type,doi,authorships,awards,primary_topic,primary_location'))
        for work in response.get('results') or []:
            target_names=set(); target_orcids=set(); target_institutions=set(); seen=set(); matched_orcid=False
            detail={'id':work.get('id'),'display_name':work.get('display_name'),'publication_year':work.get('publication_year'),'type':work.get('type')}
            for authorship in work.get('authorships') or []:
                author=authorship.get('author') or {}; identifier=author.get('id')
                if identifier==author_id:
                    raw=(authorship.get('raw_author_name') or '').strip()
                    if raw: target_names.add(raw)
                    raw_orcid=authorship.get('raw_orcid')
                    if raw_orcid:
                        raw_orcid=raw_orcid.rstrip('/').rsplit('/',1)[-1].upper();raw_orcids[raw_orcid]+=1;target_orcids.add(raw_orcid)
                    for institution in authorship.get('institutions') or []:
                        if institution.get('id'):
                            target_institutions.add(institution['id']);institution_labels[institution['id']]=institution.get('display_name') or institution['id'];institution_works.setdefault(institution['id'],{})[detail['id']]=detail
                    if profile_orcid and raw_orcid and profile_orcid.rstrip('/').rsplit('/',1)[-1].upper()==raw_orcid.rstrip('/').rsplit('/',1)[-1].upper(): matched_orcid=True
                elif identifier and identifier not in seen:
                    seen.add(identifier);coauthors[identifier]+=1;coauthor_labels[identifier]=author.get('display_name') or identifier;coauthor_works.setdefault(identifier,{})[detail['id']]=detail
            topic=(work.get('primary_topic') or {}).get('field') or {}
            source=((work.get('primary_location') or {}).get('source') or {})
            work_evidence.append({**detail,'type':work.get('type'),'doi':work.get('doi'),'raw_names':sorted(target_names),'raw_orcids':sorted(target_orcids),'institution_ids':sorted(target_institutions),'coauthor_ids':sorted(seen),'field_id':topic.get('id'),'source_id':source.get('id')})
            for raw in target_names:
                names[raw]+=1;works_by_name.setdefault(raw,[]).append(detail)
            if matched_orcid: exact_orcid_works+=1
            for award in work.get('awards') or []:
                identifier=award.get('id') or award.get('doi') or award.get('funder_award_id')
                if identifier: awards[identifier]+=1;award_labels[identifier]=award.get('display_name') or award.get('funder_award_id') or identifier;award_works.setdefault(identifier,{})[detail['id']]=detail
            inspected+=1
        cursor=(response.get('meta') or {}).get('next_cursor')
    first=(full_name or '').strip().split(' ',1)[0].lower()
    initial=first[:1]
    def compatible(raw):
        words=re.findall(r"[A-Za-z]+",raw.lower())
        return bool(initial and words and (words[0].startswith(initial) or (len(words)>1 and words[-1].startswith(initial))))
    rows=[{'label':name,'count':count,'compatible_with_full_name':compatible(name),'works':works_by_name.get(name,[])} for name,count in names.most_common()]
    compatible_works={work['id']:work for row in rows if row['compatible_with_full_name'] for work in row['works'] if work.get('id')}
    return {'inspected_works':inspected,'expected_works':expected,'complete':inspected==expected,
            'name_variants':rows,'full_name_compatible_works':len(compatible_works),'candidate_works':list(compatible_works.values()),
            'works_with_exact_raw_orcid':exact_orcid_works,
            'raw_orcids':[{'id':identifier,'count':count} for identifier,count in raw_orcids.most_common()],
            'coauthors':[{'id':identifier,'label':coauthor_labels[identifier],'count':count,'works':list(coauthor_works.get(identifier,{}).values())} for identifier,count in coauthors.most_common(20)],
            'affiliations':[{'id':identifier,'label':institution_labels[identifier],'count':len(rows),'works':list(rows.values())} for identifier,rows in sorted(institution_works.items(),key=lambda item:-len(item[1]))],
            'awards':[{'id':identifier,'label':award_labels[identifier],'count':count,'works':list(award_works.get(identifier,{}).values())} for identifier,count in awards.most_common()],
            '_work_evidence':work_evidence,
            'note':'Name compatibility uses only the first initial from the profile full name. It is a candidate split for inspection, not a new author identity.'}


NICKNAME_GROUPS=({'william','bill','billy','will','liam'},{'robert','bob','bobby','rob'},{'richard','rick','dick','rich'},{'elizabeth','liz','beth','betty'},{'margaret','meg','maggie','peggy'},{'katherine','catherine','kate','kathy'},{'james','jim','jimmy'},{'john','jack'},{'edward','ed','ted'},{'charles','chuck','charlie'})

def _name_tokens(value):
    folded=unicodedata.normalize('NFKD',value or '').encode('ascii','ignore').decode().lower()
    return re.findall(r'[a-z]+',folded)

def _given_equivalent(left,right):
    if not left or not right:return True
    if left==right or left[:1]==right[:1] and (len(left)==1 or len(right)==1):return True
    return any(left in group and right in group for group in NICKNAME_GROUPS)

def _name_compatible(left,right):
    """Conservative match allowing order changes and compound-surname drift."""
    a=_name_tokens(left);b=_name_tokens(right)
    if not a or not b:return True
    if set(a)==set(b):return True
    # Publications may move the first of two family names into the middle-name position.
    # Single-letter initials are too weak for token-overlap matching: D. J. Webb
    # and Andrew J. Webb must not join merely because they share "J" and "Webb".
    common={token for token in set(a)&set(b) if len(token)>1}
    if len(common)>=2:return True
    return (_given_equivalent(a[0],b[0]) and (a[-1]==b[-1] or a[-1] in b or b[-1] in a)) or (_given_equivalent(a[-1],b[-1]) and (a[0]==b[0] or a[0] in b or b[0] in a))

def find_merge_candidates(api,identity,evidence):
    """Conservative nearby-profile search; candidates need two independent overlaps."""
    author_id=identity.get('id');name=identity.get('display_name') or identity.get('full_name')
    if not name:return []
    main_institutions={row.get('institution',{}).get('id') for row in identity.get('affiliations') or []}
    main_fields={row.get('field',{}).get('id') for row in identity.get('topics') or []}
    main_coauthors={row['id'] for row in evidence.get('coauthors') or []}
    rows=api.get('authors',{'search':name,'per_page':10}).get('results') or []
    output=[]
    for candidate in rows:
        if candidate.get('id')==author_id or not _name_compatible(name,candidate.get('display_name') or candidate.get('full_name')):continue
        affiliations={row.get('institution',{}).get('id') for row in candidate.get('affiliations') or []}
        fields={row.get('field',{}).get('id') for row in candidate.get('topics') or []}
        shared_institutions=sorted((main_institutions&affiliations)-{None});shared_fields=sorted((main_fields&fields)-{None});shared_coauthors=[]
        if shared_institutions or shared_fields:
            response=api.get('works',{'filter':'authorships.author.id:'+candidate['id'],'per_page':100,'select':'id,authorships'})
            other={auth.get('author',{}).get('id') for work in response.get('results') or [] for auth in work.get('authorships') or []}
            shared_coauthors=sorted((main_coauthors&other)-{None})
        signals=sum(bool(x) for x in (shared_institutions,shared_fields,shared_coauthors))
        if signals>=2:
            output.append({'id':candidate['id'],'display_name':candidate.get('display_name'),'works_count':candidate.get('works_count'),'orcid':candidate.get('orcid'),'shared_institution_ids':shared_institutions,'shared_field_ids':shared_fields,'shared_coauthor_ids':shared_coauthors,'overlap_signal_count':signals,'status':'review_merge'})
    return sorted(output,key=lambda row:(-row['overlap_signal_count'],-len(row['shared_coauthor_ids']),row['works_count'] or 0))[:5]

def resolve_author_identity(author_id,display_name,full_name,works):
    """First-pass deterministic triage; it deliberately makes no probability claim."""
    strong_types={'article','preprint','review','book-chapter','proceedings-article'}
    def eligible(work):
        if work.get('type') in strong_types:return True
        signals=sum(bool(value) for value in (work.get('doi'),work.get('field_id'),work.get('source_id'),work.get('raw_orcids'),work.get('institution_ids'),len(work.get('coauthor_ids') or [])>=2))
        return bool(work.get('publication_year')) and signals>=2
    excluded=[work for work in works if not eligible(work)]
    works=[work for work in works if eligible(work)]
    dated=sorted((w for w in works if isinstance(w.get('publication_year'),int)),key=lambda w:w['publication_year'])
    years=[w['publication_year'] for w in dated]
    span=(years[-1]-years[0]) if years else None
    outliers=[]
    for index,work in enumerate(dated):
        distances=[]
        if index:distances.append(work['publication_year']-dated[index-1]['publication_year'])
        if index+1<len(dated):distances.append(dated[index+1]['publication_year']-work['publication_year'])
        if distances and min(distances)>10:outliers.append(work)
    orcid_groups={}
    for work in works:
        for value in work.get('raw_orcids') or []:orcid_groups.setdefault(value,[]).append(work)
    substantial_orcids={key:value for key,value in orcid_groups.items() if len(value)>=2}
    name_groups=[]
    for work in works:
        raw=(work.get('raw_names') or [''])[0]
        if not raw:continue
        for group in name_groups:
            if _name_compatible(raw,group['label']):group['works'].append(work);break
        else:name_groups.append({'label':raw,'works':[work]})
    name_groups=[group for group in name_groups if len(group['works'])>=5]
    partition=[];triggers=[]
    def partition_row(index,label,anchor,rows):
        coauthors=Counter(identifier for work in rows for identifier in work.get('coauthor_ids') or [])
        institutions=Counter(identifier for work in rows for identifier in work.get('institution_ids') or [])
        fields=Counter(work.get('field_id') for work in rows if work.get('field_id'))
        years=Counter(work.get('publication_year') for work in rows if isinstance(work.get('publication_year'),int))
        return {'id':f'local-{author_id.rsplit("/",1)[-1]}-{index+1}','label':label,'anchor':anchor,
                'work_ids':[work['id'] for work in rows],
                'coauthor_ids':[key for key,_ in coauthors.most_common(10)],
                'institution_ids':[key for key,_ in institutions.most_common(10)],
                'field_ids':[key for key,_ in fields.most_common(8)],
                'publication_years':[{'year':year,'count':count} for year,count in sorted(years.items())]}
    if len(substantial_orcids)>1:
        triggers.append({'type':'orcid_conflict','strength':'strong','description':f'{len(substantial_orcids)} distinct ORCID iDs each anchor at least two works.'})
        partition=[partition_row(i,key,'orcid',rows) for i,(key,rows) in enumerate(sorted(substantial_orcids.items()))]
    elif len(name_groups)>1:
        triggers.append({'type':'name_separation','strength':'moderate','description':f'{len(name_groups)} incompatible printed-name groups each anchor at least five works.'})
        partition=[partition_row(i,group['label'],'printed_name',group['works']) for i,group in enumerate(sorted(name_groups,key=lambda x:-len(x['works'])))]
    if outliers:triggers.append({'type':'isolated_year','strength':'moderate','description':f'{len(outliers)} works are more than 10 years from the nearest dated work.'})
    if span is not None and span>70:triggers.append({'type':'career_span','strength':'strong','description':f'The recorded publication span is {span} years.'})
    elif span is not None and span>50:triggers.append({'type':'career_span','strength':'review','description':f'The recorded publication span is {span} years; early initial-only records need extra scrutiny.'})
    status='recommend_partition' if partition and any(t['strength']=='strong' for t in triggers) else 'review_partition' if partition else 'review_outliers' if outliers else 'keep_together'
    assigned={work_id for group in partition for work_id in group['work_ids']}
    unassigned=[{'id':w['id'],'display_name':w.get('display_name'),'publication_year':w.get('publication_year')} for w in works if w.get('id') not in assigned] if partition else []
    return {'method':'deterministic-v1','status':status,'score_kind':'evidence_not_probability','work_count':len(works),'source_work_count':len(works)+len(excluded),'career':{'first_year':years[0] if years else None,'last_year':years[-1] if years else None,'span_years':span,'over_50_years':bool(span and span>50),'over_70_years':bool(span and span>70)},'outlier_works':[{'id':w['id'],'display_name':w.get('display_name'),'publication_year':w.get('publication_year'),'reason':'more_than_10_years_from_nearest_work'} for w in outliers],'excluded_works':[{'id':w['id'],'display_name':w.get('display_name'),'publication_year':w.get('publication_year'),'reason':'weak_work_type_and_metadata'} for w in excluded],'proposed_identities':partition,'unassigned_works':unassigned,'evidence':triggers,'rules':{'isolated_year_gap':10,'long_career_review':50,'long_career_flag':70,'minimum_name_cluster':5,'minimum_orcid_cluster':2,'strong_work_types':sorted(strong_types),'other_work_minimum_metadata_signals':2},'note':'Articles, preprints, reviews, book chapters, and proceedings articles are included directly. Other types require a year and at least two strong metadata signals. Career length alone never creates a split.'}


def make_spec(institution, start, end):
    selected = selector(institution)
    if selected['id_namespace'] != 'openalex': raise ValueError('Confirm an institution from the search results first.')
    if end - start > 49: raise ValueError('Choose a period of at most 50 years for this overview.')
    return specification(selected, 'https://openalex.org/' + selected['id'], start, end)


def get_count(api, query, extra=''):
    q = dict(query, per_page=1, select='id')
    if extra: q['filter'] += ',' + extra
    result = api.get('works', q)
    count = result.get('meta', {}).get('count')
    if not isinstance(count, int) or count < 0: raise APIError('OpenAlex returned an invalid count.')
    return count


def get_groups(api, query, field):
    response = api.get('works', dict(query, group_by=field + ':include_unknown', per_page=100))
    rows = response.get('group_by')
    if not isinstance(rows, list): raise APIError('OpenAlex returned no grouped counts.')
    output = []
    for row in rows:
        if not isinstance(row.get('count'), int) or row['count'] < 0: raise APIError('Invalid grouped count.')
        key = str(row['key'])
        if field == 'type' and '/types/' in key:
            key = key.rsplit('/',1)[-1]
        # OpenAlex can qualify its unknown sentinel as an entity URL.
        missing = key.rsplit('/', 1)[-1] in ('unknown', 'null', 'None', '-111')
        output.append({'id':'unknown' if missing else key, 'label':'Unknown / missing' if missing else str(row.get('key_display_name') or key), 'count':row['count']})
    return output


def filtered_groups(api, query, field, extra):
    filtered = dict(query)
    filtered['filter'] += ',' + extra
    return get_groups(api, filtered, field)


def shares(rows, denominator, population='eligible_works'):
    return [{**row, **measure(row['count'], denominator, population)} for row in rows]


def institution_locations(api, rows):
    ids = [row['id'].rsplit('/', 1)[-1] for row in rows if re.fullmatch(r'https://openalex.org/I\d+', row['id'])]
    if not ids:
        return {}
    response = api.get('institutions', {'filter':'openalex:' + '|'.join(ids[:100]), 'per_page':100,
                                        'select':'id,display_name,country_code,type,ror'})
    return {row['id']:row for row in response.get('results', []) if row.get('id')}


def subject_hierarchy(api, subjects):
    definitions=api.get('fields',{'per_page':100}).get('results',[])
    domains={row.get('id'):row.get('domain') or {} for row in definitions}
    output={}
    for row in subjects:
        domain=domains.get(row['id'],{})
        if domain.get('id'):
            output.setdefault(domain['id'],{'id':domain['id'],'label':domain.get('display_name') or domain['id'],'fields':[]})['fields'].append(row)
    for group in output.values(): group['fields'].sort(key=lambda r:-r['count'])
    return output


def change_description(first, last):
    if first == 0:
        return {'absolute':last-first, 'percentage':None, 'direction':'not_comparable'}
    change = (last-first) * 100 / first
    direction = 'higher' if change > 0 else 'lower' if change < 0 else 'unchanged'
    return {'absolute':last-first, 'percentage':round(abs(change), 1), 'direction':direction}


def diagnostics(api, query, groups, n, classified):
    unclassified = n-classified
    missing_subject_year = filtered_groups(api, query, 'publication_year', 'primary_topic.field.id:null')
    missing_subject_types = filtered_groups(api, query, 'type', 'primary_topic.field.id:null')
    missing_subject_sources = filtered_groups(api, query, 'primary_location.source.id', 'primary_topic.field.id:null')
    abstract_year = filtered_groups(api, query, 'publication_year', 'has_abstract:true')
    abstract_types = filtered_groups(api, query, 'type', 'has_abstract:true')
    doi_types = filtered_groups(api, query, 'type', 'has_doi:true')
    source_year = filtered_groups(api, query, 'publication_year', 'primary_location.source.id:!null')
    source_types = filtered_groups(api, query, 'type', 'primary_location.source.id:!null')
    abstract_fields = filtered_groups(api, query, 'primary_topic.field.id', 'has_abstract:true')
    abstract_sources = filtered_groups(api, query, 'primary_location.source.id', 'has_abstract:true')
    abstract_publishers = filtered_groups(api, query, 'primary_location.source.host_organization', 'has_abstract:true')

    def annual(rows, denominator_rows, population):
        values = {r['id']:r['count'] for r in rows}
        return [{'id':total['id'],'label':total['label'],
                 **measure(values.get(total['id'],0),total['count'],population)} for total in denominator_rows]

    def rates(numerators, denominators, population):
        nums={r['id']:r['count'] for r in numerators}
        result=[]
        for total in denominators:
            if total['id']=='unknown':
                continue
            result.append({'id':total['id'],'label':total['label'],
                           **measure(nums.get(total['id'],0),total['count'],population)})
        return sorted(result,key=lambda r:(r['percentage'] is None, r['percentage'] or 0, -r['denominator'], r['label']))

    publisher_totals=get_groups(api,query,'primary_location.source.host_organization')
    publisher_rates=[r for r in rates(abstract_publishers,publisher_totals,'publisher_hosted_works')
                     if re.fullmatch(r'https://openalex.org/P\d+',r['id'])]
    return {
        'unclassified_subject':{
            'count':measure(unclassified,n),
            'by_year':annual(missing_subject_year,groups['annual'],'annual_works'),
            'by_work_type':shares(missing_subject_types,unclassified,'unclassified_works'),
            'by_primary_source':shares(missing_subject_sources,unclassified,'unclassified_works'),
            'note':'Work types and primary sources with the largest numbers of unclassified works. OpenAlex does not record a reason for each missing Field.'},
        'abstracts':{
            'by_year':annual(abstract_year,groups['annual'],'annual_works'),
            'by_work_type':rates(abstract_types,groups['types'],'work_type_works'),
            'lowest_coverage_fields':rates(abstract_fields,groups['subjects'],'field_works')[:5],
            'lowest_coverage_sources':[r for r in rates(abstract_sources,groups['sources'],'source_works') if r['denominator'] >= 100][:5],
            'lowest_coverage_publishers':[r for r in publisher_rates if r['denominator'] >= 100][:5],
            'minimum_group_size':100,
            'note':'Lowest abstract coverage among returned Fields, sources, and direct publishers with at least 100 works. Associations are descriptive; they do not explain missing abstracts.'},
        'doi':{
            'by_work_type':rates(doi_types,groups['types'],'work_type_works'),
            'note':'DOI coverage by recorded work type. A missing DOI can be expected for some output types, so the overall percentage should not be interpreted without this breakdown.'},
        'primary_source':{
            'by_year':annual(source_year,groups['annual'],'annual_works'),
            'by_work_type':rates(source_types,groups['types'],'work_type_works'),
            'note':'Primary-source coverage by year and work type. This locates missing source links but does not explain why they are absent.'}}


def coverage_assessment(coverage):
    names={'primary_subject':'Field classification','doi':'DOI coverage','abstract':'Abstract coverage','primary_source':'Main source coverage'}
    metrics=[]
    for key in ('primary_subject','doi','abstract','primary_source'):
        metrics.append({'key':key,'name':names[key],**coverage[key]})
    strongest=max(metrics,key=lambda r:r['percentage'])
    weakest=min(metrics,key=lambda r:r['percentage'])
    return {'metrics':metrics,
            'strongest':strongest,'weakest':weakest,
            'line':f"Recorded metadata ranges from {weakest['name'].lower()} at {weakest['percentage']:.1f}% to {strongest['name'].lower()} at {strongest['percentage']:.1f}%."}


def open_access_summary(api, query, annual, n):
    statuses=get_groups(api,query,'open_access.oa_status')
    known=[row for row in statuses if row['id']!='unknown']
    by_status={row['id']:filtered_groups(api,query,'publication_year','open_access.oa_status:'+row['id']) for row in known}
    trend=[]
    for year in annual:
        rows=[]
        for status in known:
            count=next((row['count'] for row in by_status[status['id']] if row['id']==year['id']),0)
            rows.append({'id':status['id'],'label':status['label'],**measure(count,year['count'],'annual_works')})
        trend.append({'year':year['id'],'total':year['count'],'rows':rows})
    return {'statuses':shares(statuses,n,'eligible_works'),'trend':trend,
            'definition':'OpenAlex marks a work open access when it finds a free-to-read full-text copy that requires neither payment nor login.'}


def citation_summary(api, query, annual, n):
    """Saved citation indicators; no institutional ranking or causal interpretation."""
    cited=get_count(api,query,'cited_by_count:>0')
    top_ten=get_count(api,query,'citation_normalized_percentile.is_in_top_10_percent:true')
    top_one=get_count(api,query,'citation_normalized_percentile.is_in_top_1_percent:true')
    cited_year=filtered_groups(api,query,'publication_year','cited_by_count:>0')
    top_ten_year=filtered_groups(api,query,'publication_year','citation_normalized_percentile.is_in_top_10_percent:true')
    cited_values={r['id']:r['count'] for r in cited_year}
    top_values={r['id']:r['count'] for r in top_ten_year}
    return {
        'cited':measure(cited,n,'eligible_works'),
        'top_10_percent':measure(top_ten,n,'eligible_works'),'top_1_percent':measure(top_one,n,'eligible_works'),
        'by_publication_year':[{'year':row['id'],'total':row['count'],'cited':measure(cited_values.get(row['id'],0),row['count'],'annual_works'),'top_10_percent':measure(top_values.get(row['id'],0),row['count'],'annual_works')} for row in annual],
        'note':'Citation counts are successful reference matches in OpenAlex and change as records are added. OpenAlex normalized citation percentiles compare each Work with Works of the same publication year, work type, and subfield. The top-10% and top-1% flags are changing database indicators, not quality rankings or evidence that the viewed entity caused the citations. OpenAlex does not expose a reliable aggregate FWCI coverage count, so this view does not invent an institutional average.'}


def evidence_signal_summary(api, query, work_types, n):
    """Presence of analysis inputs and funding links, overall and by Work type."""
    definitions = (
        ('references', 'referenced_works_count:>0'),
        ('funder', 'funders.id:!null'),
        ('award', 'awards.id:!null'),
        ('grant_number', 'awards.funder_award_id:!null'),
    )
    totals = {row['id']: row['count'] for row in work_types if row['id'] != 'unknown'}
    result = {}
    for key, filter_value in definitions:
        rows = filtered_groups(api, query, 'type', filter_value)
        counts = {row['id']: row['count'] for row in rows if row['id'] != 'unknown'}
        result[key] = {
            'overall': measure(sum(counts.values()), n, 'eligible_works'),
            'by_work_type': [
                {'id': work_type, **measure(counts.get(work_type, 0), totals.get(work_type, 0), 'work_type_works')}
                for work_type in ('article', 'preprint')
            ],
        }
    result['note'] = ('Reference links are successful matches to other OpenAlex Works. Funding fields are recorded evidence, not the share of Works that were funded. '
                      'OpenAlex does not expose general acknowledgement-text presence separately from identified funders and Awards.')
    return result


def deterministic_briefing(identity, groups, population, coverage, detail, benchmark=None):
    n=population['eligible_works']
    types=[r for r in groups['types'] if r['id']!='unknown']
    complete=[r for r in groups['annual'] if r['complete_year']]
    annual=complete or groups['annual']
    first,last=annual[0],annual[-1]
    change=change_description(first['count'],last['count'])
    subjects=groups['subjects'][:3]
    period=f"{groups['annual'][0]['label']}–{groups['annual'][-1]['label']}"
    growth='changed'
    if change['percentage'] is not None:
        growth='grown' if change['direction']=='higher' else 'fallen' if change['direction']=='lower' else 'not changed'
    comparison=''
    if benchmark and benchmark.get('rank'):
        comparison=f" By work count, it ranks {benchmark['rank']}{benchmark['rank_suffix']} among the UK universities that appear in OpenAlex’s 100 highest-output institutions globally for the same period."
    sentences=[
        {'text':f"OpenAlex covers {n:,} works for {identity['display_name']} ({period})."+comparison+f" Articles account for {next((r['percentage'] for r in types if r['id']=='article'),0):.1f}%, preprints {next((r['percentage'] for r in types if r['id']=='preprint'),0):.1f}%, and book chapters {next((r['percentage'] for r in types if r['id']=='book-chapter'),0):.1f}%.",'fields':['population.eligible_works','groups.types','benchmark']},
        {'text':f"Output has {growth} {round(change['percentage'] or 0):.0f}% since {first['label']}, reaching {last['count']:,} works in {last['label']}.",'fields':['groups.annual']},
        {'text':"The three largest broad fields are " + ', '.join(f"{r['label']} ({r['percentage']:.1f}%)" for r in subjects) + ".",'fields':['groups.subjects']},
        {'text':f"Abstract coverage is {coverage['abstract']['percentage']:.1f}%. Missing abstracts do not invalidate records, but they make text and semantic analysis less representative; inspect where the gap sits before using abstracts.",'fields':['coverage.abstract','diagnostics.abstracts.by_work_type']},
    ]
    return {'kind':'deterministic','sentences':sentences,'rules':''}


def overview(api, institution, start, end, progress=lambda message:None):
    spec = make_spec(institution, start, end)
    progress('Confirming the institution')
    identity = api.resolve(spec['selector'])
    query = api.query(spec)
    progress('Counting publications')
    n = get_count(api, query)
    groups = {}
    for key, field in GROUPS.items():
        progress('Reading ' + {'annual':'publications by year', 'subjects':'subject composition', 'institutions':'institution collaborations'}.get(key, key))
        groups[key] = get_groups(api, query, field)
    unknown = lambda key: key in ('unknown','null','None','-111')
    classified_rows = [r for r in groups['subjects'] if not unknown(r['id'])]
    classified = sum(r['count'] for r in classified_rows)
    if classified > n: raise APIError('Subject counts do not reconcile with the population. Retry after the source has stabilized.')
    warnings = [
        'This overview uses whole-corpus API aggregates, not a downloaded set of publications. Publication lists are fetched separately when opened.',
        'The live index can change between queries. Saved queries and retrieval dates describe this overview; full record export requires the CLI.',
        'The institution filter uses the selected OpenAlex ID. Separate records for related organisations are not added to this report.',
        'Shared-work counts describe co-occurrence, not partnership strength or impact. Each institution or country is counted once per work.',
        'Blank metadata fields mean OpenAlex has no value recorded. Detailed authorship-resolution coverage requires a full record download.',
        'Compare these OpenAlex counts with your institutional records if you need to assess completeness.',
    ]
    if sum(r['count'] for r in groups['annual']) != n:
        warnings.append('Annual counts differ from the total count. The source may have changed between queries.')
    for key in groups:
        denominator = classified if key == 'subjects' else n
        rows = classified_rows if key == 'subjects' else groups[key]
        groups[key] = [{**r, **measure(r['count'], denominator, 'classified_works' if key == 'subjects' else 'eligible_works')} for r in rows]
    progress('Reading the subject hierarchy')
    groups['domain_fields']=subject_hierarchy(api,groups['subjects'])
    annual_by_year = {r['id']:r for r in groups['annual']}
    groups['annual'] = [{'id':str(y),'label':str(y), **measure(annual_by_year.get(str(y),{}).get('count',0),n), 'complete_year':y < date.today().year} for y in range(start,end+1)]
    progress('Reading subfields and topics')
    groups['subfields']=shares([r for r in get_groups(api,query,'primary_topic.subfield.id') if not unknown(r['id'])],classified,'classified_works')
    groups['topics']=shares([r for r in get_groups(api,query,'primary_topic.id') if not unknown(r['id'])],classified,'classified_works')
    groups['sdgs']=shares([r for r in get_groups(api,query,'sustainable_development_goals.id') if not unknown(r['id'])],n,'eligible_works')
    sdg_tagged=get_count(api,query,'sustainable_development_goals.id:!null')
    groups['sdg_summary']={'tagged_works':measure(sdg_tagged,n,'eligible_works'),
                           'tag_assignments':sum(r['count'] for r in groups['sdgs']),
                           'average_tags_per_tagged_work':sum(r['count'] for r in groups['sdgs'])/sdg_tagged if sdg_tagged else None}
    groups['institutions'] = [r for r in groups['institutions'] if r['id'] != identity['id'] and not unknown(r['id'])]
    groups['countries'] = [r for r in groups['countries'] if not unknown(r['id'])]
    progress('Checking collaboration locations')
    locations = institution_locations(api, groups['institutions'])
    home = identity.get('country_code')
    groups['institutions'] = [{**r,
        'country_code':locations.get(r['id'],{}).get('country_code'),
        'institution_type':locations.get(r['id'],{}).get('type'),
        'collaboration_scope':('domestic' if home and locations.get(r['id'],{}).get('country_code') == home
                               else 'international' if locations.get(r['id'],{}).get('country_code')
                               else 'unknown')} for r in groups['institutions']]
    coverage = {'primary_subject':measure(classified,n)}
    counts = {}
    for label, field in [('doi','has_doi:true'),('abstract','has_abstract:true'),('retracted','is_retracted:true')]:
        progress('Checking ' + label.replace('_',' ') + ' coverage')
        counts[label] = get_count(api,query,field)
    coverage.update({k:measure(counts[k],n) for k in ('doi','abstract')})
    source_known = get_count(api,query,'primary_location.source.id:!null')
    coverage['primary_source'] = measure(source_known,n)
    progress('Reading open access status')
    open_access=open_access_summary(api,query,groups['annual'],n)
    progress('Reading citation indicators')
    citations=citation_summary(api,query,groups['annual'],n)
    progress('Reading reference and funding evidence signals')
    evidence_signals=evidence_signal_summary(api,query,groups['types'],n)
    if end == date.today().year: warnings.append('The current year is incomplete and should not be compared with complete years.')
    progress('Reading publication sources and publishers')
    venues = venue_view(api,spec)
    progress('Checking metadata patterns')
    detail = diagnostics(api,query,groups,n,classified)
    progress('Reading funding coverage')
    funded = get_count(api,query,'funders.id:!null')
    funding_rows = get_groups(api,query,'funders.id')
    funding = {'coverage':measure(funded,n,'eligible_works'),
               'top_funders':shares([r for r in funding_rows if not unknown(r['id'])],n,'eligible_works'),
               'note':'Funders are organisations linked to works by OpenAlex. Counts overlap when one work names several funders; an empty value means no funder is recorded, not necessarily that the work had no funding.'}
    progress('Reading work-type change')
    top_types=[r for r in groups['types'] if not unknown(r['id'])][:6]
    type_by_year={r['id']:filtered_groups(api,query,'publication_year','type:'+r['id']) for r in top_types}
    work_type_trend=[]
    for annual in groups['annual']:
        rows=[]
        for t in top_types:
            count=next((r['count'] for r in type_by_year[t['id']] if r['id']==annual['id']),0)
            rows.append({'id':t['id'],'label':t['label'],**measure(count,annual['count'],'annual_works')})
        work_type_trend.append({'year':annual['id'],'total':annual['count'],'rows':sorted(rows,key=lambda r:(-r['count'],r['label']))})
    progress('Reading field change')
    top_fields=groups['subjects'][:6]
    field_by_year={r['id']:filtered_groups(api,query,'publication_year','primary_topic.field.id:'+r['id']) for r in top_fields}
    field_trend=[]
    for annual in groups['annual']:
        rows=[]
        for field in top_fields:
            count=next((r['count'] for r in field_by_year[field['id']] if r['id']==annual['id']),0)
            rows.append({'id':field['id'],'label':field['label'],**measure(count,annual['count'],'annual_works')})
        field_trend.append({'year':annual['id'],'total':annual['count'],'rows':sorted(rows,key=lambda r:(-r['count'],r['label']))})
    benchmark=None
    if identity.get('country_code') == 'GB' and identity.get('type') == 'education':
        progress('Comparing UK university scale')
        comparison_query={'filter':f'from_publication_date:{start}-01-01,to_publication_date:{end}-12-31','corpus':'core'}
        comparison_rows=get_groups(api,comparison_query,'authorships.institutions.id')
        comparison_locations=institution_locations(api,comparison_rows)
        peers=[r for r in comparison_rows if comparison_locations.get(r['id'],{}).get('country_code')=='GB' and comparison_locations.get(r['id'],{}).get('type')=='education']
        rank=next((i+1 for i,r in enumerate(peers) if r['id']==identity['id']),None)
        suffix='th' if rank and 10 < rank % 100 < 14 else {1:'st',2:'nd',3:'rd'}.get((rank or 0)%10,'th')
        benchmark={'scope':'UK education institutions appearing among the 100 institutions with the highest work counts globally','rank':rank,'rank_suffix':suffix,
                   'peers':peers,'note':'Whole-work-count comparison for the same years and core corpus. Limited to UK education institutions appearing among OpenAlex’s 100 highest-output institutions globally; this bounded set keeps the aggregate query practical, so use it as a scale check rather than a complete UK league table.'}
    # Institution affiliation and researcher evidence is loaded live in its own
    # bounded views. It is intentionally not inferred from a random Work sample.
    affiliations = {'mode':'live_audit','requested_sample_size':0,'sampled_works':0,'seeds':[],
                    'mapped_work_coverage':measure(0,0,'sampled_works'),
                    'target_authorships_without_mapped_string':0,'observed_target_authorships':0,
                    'rows':[],'core_names':[],'sub_affiliations':[],
                    'researchers':{'unique_count':0,'with_orcid':0,'profiles_with_multiple_raw_orcids':0,
                                   'raw_orcids_on_multiple_profiles':0,'by_year':[],'top':[],'denominator':'live_audit'},
                    'other_institutions':[],
                    'note':'Researcher and affiliation evidence is loaded live from ranked OpenAlex Author and raw-affiliation-string queries; no random Work sample is used.'}
    population={'eligible_works':n,'classified_works':classified,'unclassified_works':n-classified}
    briefing=deterministic_briefing(identity,groups,population,coverage,detail,benchmark)
    assessment=coverage_assessment(coverage)
    return {'schema_version':'1.0','overview_specification':'pharos-coverage-overview-v9','mode':'live_aggregates','implementation_version':16,
        'identity':identity,
        'associated_institutions':[{'id':row.get('id'),'display_name':row.get('display_name'),'relationship':row.get('relationship')}
                                   for row in identity.get('associated_institutions') or [] if row.get('id')],
        'corpus':spec,'corpus_specification_hash':digest(spec),'retrieved_at':now(),
        'population':population,'groups':groups,'coverage':coverage,'coverage_assessment':assessment,'diagnostics':detail,'briefing':briefing,
        'funding':funding,'open_access':open_access,'citations':citations,'evidence_signals':evidence_signals,'work_type_trend':work_type_trend,'field_trend':field_trend,'benchmark':benchmark,
        'venues':venues,'affiliations':affiliations,'retracted_works':measure(counts['retracted'],n),
        'warnings':warnings,'queries':list(getattr(api,'requests',[])),
        'full_download_estimate':estimate(n,RATE_CARD,bool(api.key)),
        'group_limits':{'institutions':100,'countries':100,'sources':100},
        'notes':{'subjects':'Primary OpenAlex Fields. Shares use classified publications only.',
                 'institutions':'Leading institutions recorded on the same works; target excluded. Domestic and international labels use the institution country recorded by OpenAlex. Whole counts overlap.',
                 'countries':'Leading countries recorded on the same works, including the home country. Whole counts overlap.',
                 'sources':'Leading primary publication sources; alternative locations are excluded.'}}


def publications(api, institution, start, end, kind='', value='', page=1, work_type=''):
    author=bool(re.fullmatch(r'(?:https://openalex.org/)?A\d+',institution,re.I))
    if author:
        author_id='https://openalex.org/'+institution.removeprefix('https://openalex.org/').upper()
        query={'filter':'authorships.author.id:'+author_id,'corpus':'core'}
    else:
        spec = make_spec(institution,start,end)
        query = api.query(spec)
    if not 1 <= page <= 500: raise ValueError('Publication lists are limited to 10,000 records. Use the CLI to export the full corpus.')
    if kind:
        if kind not in DRILL_FILTERS: raise ValueError('Unknown publication filter.')
        patterns = {'year':r'\d{4}', 'subject':r'https://openalex.org/fields/\d+', 'institution':r'https://openalex.org/I\d+',
                    'source':r'https://openalex.org/S\d+', 'country':r'[A-Za-z]{2}', 'type':r'[a-z][a-z-]{0,60}', 'publisher':r'https://openalex.org/P[0-9]+',
                    'author':r'https://openalex.org/A\d+', 'doi':r'(?:true|false)', 'abstract':r'(?:true|false)',
                    'oa':r'(?:diamond|gold|green|hybrid|bronze|closed)', 'sdg':r'https://openalex.org/sdgs/\d+',
                    'cited':r'true','uncited':r'true','top10':r'true','top1':r'true'}
        if value != 'unknown' and not re.fullmatch(patterns[kind],value): raise ValueError('Invalid publication filter value.')
        # Unknown groups correspond to the API null filter, not the literal string "unknown".
        if kind=='cited': query['filter'] += ',cited_by_count:>0'
        elif kind=='uncited': query['filter'] += ',cited_by_count:0'
        else: query['filter'] += ',' + DRILL_FILTERS[kind] + ':' + ('null' if value == 'unknown' else value)
    if work_type:
        if not re.fullmatch(r'[a-z][a-z-]{0,60}',work_type): raise ValueError('Invalid work type.')
        query['filter'] += ',type:' + ('null' if work_type == 'unknown' else work_type)
    response = api.get('works',dict(query,per_page=20,page=page,sort='publication_date:desc',
        select='id,display_name,doi,publication_year,publication_date,type,primary_location'))
    return {'count':response['meta']['count'],'results':response['results'],'page':page,'per_page':20,
            'retrieved_at':now(),'query':query,'warning':'Live results may differ from the saved overview if OpenAlex has changed.'}


def composition(api, institution, start, end, year, kind):
    spec = make_spec(institution,start,end)
    if not start <= year <= end: raise ValueError('The selected year is outside this report.')
    fields = {'type':'type','subject':'primary_topic.field.id'}
    if kind not in fields: raise ValueError('Unknown composition breakdown.')
    query = api.query(spec)
    query['filter'] += ',publication_year:' + str(year)
    rows = get_groups(api,query,fields[kind])
    total = sum(r['count'] for r in rows)
    return {'year':year,'kind':kind,'total':total,'rows':shares(rows,total,'annual_works')}


def funding_details(api, institution, start, end):
    """Work-linked award coverage; absence is unknown, never evidence of no award."""
    spec=make_spec(institution,start,end)
    query=api.query(spec)
    total=get_count(api,query)
    count=get_count(api,query,'awards.id:!null')
    institution_awards=api.get('awards',{'filter':'institution_awarded.id:'+spec['resolved_openalex_id'],
                                         'sort':'funded_outputs_count:desc','per_page':10,'select':AWARD_SELECT})
    enriched=[award_detail(detail) for detail in institution_awards.get('results') or []]
    return {'coverage':measure(count,total,'eligible_works'),
            'institution_awards_count':(institution_awards.get('meta') or {}).get('count',len(enriched)),
            'top_awards':enriched,
            'note':'This excludes programme names inferred only from co-authored works. OpenAlex links institutions to only a small share of Award records, so treat this list as a sample rather than a total.'}


def award_detail(detail):
    """Portable subset of an OpenAlex Award record for report views."""
    lead=detail.get('lead_investigator') or {}
    lead_name=' '.join(filter(None,[lead.get('given_name'),lead.get('family_name')]))
    institutions=[r.get('display_name') or r.get('name') or r.get('id') for r in detail.get('institution_awarded') or []]
    return {'id':detail.get('id'),'label':detail.get('display_name') or detail.get('funder_award_id') or 'Untitled award',
            'description':detail.get('description'),'has_description':bool(detail.get('description')),'count':detail.get('funded_outputs_count') or 0,
            'funder':(detail.get('funder') or {}).get('display_name'),'lead_investigator':lead_name or None,
            'institutions':[name for name in institutions if name],'start_year':detail.get('start_year'),'end_year':detail.get('end_year'),
            'funder_award_id':detail.get('funder_award_id'),'amount':detail.get('amount'),'currency':detail.get('currency'),
            'funding_type':detail.get('funding_type'),'funder_scheme':detail.get('funder_scheme'),
            'landing_page_url':detail.get('landing_page_url'),'provenance':detail.get('provenance')}


def researcher_details(api, institution, start, end):
    spec=make_spec(institution,start,end)
    target=spec['resolved_openalex_id']
    current_year=date.today().year
    through=min(end,current_year)
    window_start=max(start,through-2)
    profiles=[]
    # Start with prolific profiles, then rank locally on the recent window. Five
    # bounded pages are enough for a recognisability check without claiming a roster.
    for page in range(1,6):
        batch=api.get('authors',{'filter':'last_known_institutions.id:'+target,'per_page':100,'page':page,
                                 'sort':'works_count:desc','select':'id,display_name,orcid,affiliations,counts_by_year,last_known_institutions'}).get('results',[])
        profiles.extend(batch)
        if len(batch)<100: break
    rows=[]
    for profile in profiles:
        years=[]
        for affiliation in profile.get('affiliations') or []:
            if (affiliation.get('institution') or {}).get('id')==target:
                years=[year for year in affiliation.get('years') or [] if isinstance(year,int)]
                break
        recent_affiliation_years=[year for year in years if window_start<=year<=through]
        if recent_affiliation_years:
            count=sum(r.get('works_count') or 0 for r in profile.get('counts_by_year') or [] if window_start <= (r.get('year') or 0) <= through)
            rows.append({'id':profile['id'],'label':profile.get('display_name') or profile['id'],'orcid':profile.get('orcid'),
                         'recent_works':count,'latest_affiliation_year':max(recent_affiliation_years)})
    rows.sort(key=lambda r:(-r['recent_works'],r['label'].casefold()))
    return {'researchers':rows[:100],'profiles_scanned':len(profiles),'from_year':window_start,'through_year':through,
            'through_year_is_partial':through==current_year,'returned_limit':100,
            'note':'Researchers whose latest known OpenAlex institution is this institution and whose affiliation history records it in the latest three years within the report period, ranked by all works on their OpenAlex profile during those years. The current calendar year is included when selected and is explicitly treated as partial. Recent-work counts are not limited to works carrying this affiliation. This is a recognisability check, not a staff roster or performance ranking.'}


def affiliation_audit(api, institution, name='', country=''):
    """Ranked raw-string mappings and name-based candidates; no work sampling."""
    token=make_spec(institution,date.today().year-1,date.today().year-1)['resolved_openalex_id'].rsplit('/',1)[-1]
    def clean(row):
        return {'label':row.get('raw_affiliation_string') or '', 'works_count':row.get('works_count') or 0,
                'institution_ids':row.get('institution_ids_final') or [],'overrides':row.get('institution_ids_override') or [],
                'countries':row.get('countries') or []}
    matched_response=api.get('raw-affiliation-strings',{'matched-institutions':token})
    matched=[clean(row) for row in matched_response.get('results') or [] if row.get('raw_affiliation_string')]
    matched.sort(key=lambda row:(-row['works_count'],row['label'].casefold()))
    possible=[]
    if name.strip():
        candidate_response=api.get('raw-affiliation-strings',{'q':name.strip(),'unmatched-institutions':token})
        aliases=[re.sub(r'\W+',' ',name.casefold()).strip()]
        university=re.fullmatch(r'university of (.+)',aliases[0])
        if university: aliases.append(university.group(1)+' university')
        candidates=[clean(row) for row in candidate_response.get('results') or [] if row.get('raw_affiliation_string')]
        possible=[]
        for row in candidates:
            normalized=re.sub(r'\W+',' ',row['label'].casefold()).strip()
            credible_name=any(alias in normalized for alias in aliases)
            compatible_country=not country or not row['countries'] or country in row['countries']
            publisher_boilerplate='university press' in normalized
            if credible_name and compatible_country and not publisher_boilerplate: possible.append(row)
        possible.sort(key=lambda row:(-row['works_count'],row['label'].casefold()))
    country_review=[row for row in matched if country and row['countries'] and country not in row['countries']]
    return {'matched':matched,'possible_missed':possible,'country_review':country_review,
            'matched_total':(matched_response.get('meta') or {}).get('count'), 'search_name':name,
            'note':'Matched strings are distinct published affiliation strings currently resolved to this institution, ordered by their all-time OpenAlex work count. Possible missed matches are name-search candidates, not confirmed errors. Country differences are prompts for review, not proof of a bad match.'}


def version_pairs(api, institution, start, end):
    """Works with both submitted and published locations on the same OpenAlex Work."""
    spec=make_spec(institution,start,end)
    query=api.query(spec)
    query['filter'] += ',locations.version:submittedVersion,locations.version:publishedVersion'
    response=api.get('works',dict(query,per_page=20,sort='publication_date:desc',
        select='id,display_name,doi,publication_year,publication_date,type,primary_location,locations'))
    return {'count':(response.get('meta') or {}).get('count',0),'results':response.get('results') or [],
            'retrieved_at':now(),'query':query,
            'note':'Both filters apply to locations on the same OpenAlex Work. Version labels describe hosted copies, not a title-based link between separate Work records.'}


def access_topics(api, institution, start, end):
    """Live OA, subject-granularity and sampled ORCID perspectives."""
    spec=make_spec(institution,start,end)
    query=api.query(spec)
    total=get_count(api,query)
    oa=shares(get_groups(api,query,'open_access.oa_status'),total,'eligible_works')
    subfield_rows=get_groups(api,query,'primary_topic.subfield.id')
    topic_rows=get_groups(api,query,'primary_topic.id')
    subfield_known=get_count(api,query,'primary_topic.subfield.id:!null')
    topic_known=get_count(api,query,'primary_topic.id:!null')
    target=spec['resolved_openalex_id']
    sampled={}
    for seed in (61,62):
        response=api.get('works',dict(query,sample=100,seed=seed,per_page=100,select='id,authorships'))
        sampled.update({work['id']:work for work in response.get('results') or [] if work.get('id')})
    authorships=with_orcid=0
    for work in sampled.values():
        for authorship in work.get('authorships') or []:
            if any(row.get('id')==target for row in authorship.get('institutions') or []):
                authorships+=1
                if (authorship.get('author') or {}).get('orcid'): with_orcid+=1
    identity=api.get('institutions/'+target.rsplit('/',1)[-1],{'select':'id,display_name,associated_institutions'})
    related=[]
    for row in identity.get('associated_institutions') or []:
        related.append({k:row.get(k) for k in ('id','display_name','relationship')})
    return {'retrieved_at':now(),'state':'live','eligible_works':total,'open_access':oa,
            'subfields':shares([r for r in subfield_rows if r['id']!='unknown'],subfield_known,'classified_works'),
            'topics':shares([r for r in topic_rows if r['id']!='unknown'],topic_known,'classified_works'),
            'subject_denominators':{'subfields':subfield_known,'topics':topic_known},
            'orcid_sample':{**measure(with_orcid,authorships,'sampled_target_authorships'),'sampled_works':len(sampled),'seeds':[61,62]},
            'associated_institutions':related,
            'notes':{'open_access':'OpenAlex defines OA as a free-to-read full-text copy available without payment or login.',
                     'subjects':'Only the 100 largest groups are returned. Shares exclude works without a primary topic.',
                     'orcid':'Resolved author ORCIDs among authorships linked to this institution in a reproducible 200-work sample; this is not whole-corpus coverage.',
                     'associations':'Parent, child, and related links recorded on the selected OpenAlex Institution.'}}


def researcher_profile(api, institution, author):
    if not re.fullmatch(r'https://openalex.org/A[1-9][0-9]*',author): raise ValueError('Invalid author ID.')
    if not re.fullmatch(r'I[1-9][0-9]*',institution): raise ValueError('Invalid institution ID.')
    target_institution='https://openalex.org/'+institution
    author_id=author.rsplit('/',1)[-1]
    profile=api.get('authors/'+author_id)
    base={'filter':'authorships.author.id:'+author,'corpus':'all'}
    first=api.get('works',dict(base,per_page=1,sort='publication_date:asc',select='id,display_name,publication_year'))
    at_institution=api.get('works',{'filter':f'authorships.author.id:{author},authorships.institutions.id:{institution}',
                                   'corpus':'all','per_page':100,'sort':'publication_date:asc','select':'id,display_name,publication_year,authorships'})
    exact_first=None
    for work in at_institution.get('results') or []:
        target_authorship=next((a for a in work.get('authorships') or [] if (a.get('author') or {}).get('id')==author),None)
        if target_authorship and any(i.get('id')==target_institution for i in target_authorship.get('institutions') or []):
            exact_first={k:work.get(k) for k in ('id','display_name','publication_year')}
            break
    award_rows=[r for r in get_groups(api,base,'awards.id') if r['id']!='unknown']
    return {'id':author,'display_name':profile.get('display_name') or author_id,'orcid':(profile.get('ids') or {}).get('orcid'),
            'works_count':profile.get('works_count'),'first_publication':(first.get('results') or [None])[0],
            'first_at_institution':exact_first,
            'award_count':len(award_rows),'award_count_is_lower_bound':len(award_rows)>=100,
            'note':'Award counts reflect Awards linked to this researcher’s works, not confirmed investigator roles.'}


def venue_view(api, spec, work_type=''):
    query = api.query(spec)
    if work_type:
        if not re.fullmatch(r'[a-z][a-z-]{0,60}', work_type): raise ValueError('Invalid work type.')
        query['filter'] += ',type:' + ('null' if work_type == 'unknown' else work_type)
    total = get_count(api, query)
    sources = get_groups(api, query, 'primary_location.source.id')
    hosts = get_groups(api, query, 'primary_location.source.host_organization')
    publishers = [r for r in hosts if re.fullmatch(r'https://openalex.org/P[0-9]+', r['id'])]
    return {'work_type':work_type,'eligible_works':total,
            'sources':[{**r, **measure(r['count'],total,'selected_work_type_works')} for r in sources],
            'publishers':[{**r, **measure(r['count'],total,'selected_work_type_works')} for r in publishers],
            'source_coverage':measure(get_count(api,query,'primary_location.source.id:!null'),total,'selected_work_type_works'),
            'host_coverage':measure(get_count(api,query,'primary_location.source.host_organization:!null'),total,'selected_work_type_works'),
            'query':query,'retrieved_at':now(),
            'note':'Leading primary sources and direct publisher hosts. Publisher parents are not combined. Institutional repository hosts are not publishers. Shares use the selected work-type population; source-host coverage includes institutional hosts.'}


def affiliation_sample(api, spec, display_name=None):
    """Exact per-string institution mappings only; do not borrow coauthor affiliations."""
    query = api.query(spec)
    works=[]
    for seed in range(42,48):
        response = api.get('works',dict(query,sample=100,seed=seed,per_page=100,
                                        select='id,display_name,publication_year,authorships'))
        works.extend(response.get('results',[]))
    return summarize_affiliations(works,spec['resolved_openalex_id'],display_name)


def summarize_affiliations(works, institution, display_name=None):
    unique = {w['id']:w for w in works}
    strings, other_institutions, mapped_works, unmapped_authorships, target_authorships = {},{},set(),0,0
    researchers, researchers_by_year = {},{}
    raw_orcids_by_profile, profiles_by_raw_orcid = {},{}
    for work in unique.values():
        seen=set()
        for author in work.get('authorships') or []:
            target = any(i.get('id') == institution for i in author.get('institutions') or []) or any(institution in (a.get('institution_ids') or []) for a in author.get('affiliations') or [])
            if target:
                target_authorships += 1
                author_record=author.get('author') or {}
                author_id=author_record.get('id')
                if author_id:
                    researcher=researchers.setdefault(author_id,{'id':author_id,'label':author_record.get('display_name') or author_id,'orcid':author_record.get('orcid'),'works':set()})
                    researcher['works'].add(work['id'])
                    year=work.get('publication_year')
                    if year: researchers_by_year.setdefault(year,set()).add(author_id)
                    raw_orcid=author.get('raw_orcid')
                    if raw_orcid:
                        raw_orcids_by_profile.setdefault(author_id,set()).add(raw_orcid)
                        profiles_by_raw_orcid.setdefault(raw_orcid,set()).add(author_id)
                for inst in author.get('institutions') or []:
                    iid=inst.get('id')
                    if iid and iid != institution:
                        row=other_institutions.setdefault(iid,{'id':iid,'label':inst.get('display_name') or iid,'ror':inst.get('ror'),'works':set()})
                        row['works'].add(work['id'])
            mapped = False
            for affiliation in author.get('affiliations') or []:
                text = affiliation.get('raw_affiliation_string')
                if institution in (affiliation.get('institution_ids') or []) and isinstance(text,str) and text.strip():
                    seen.add(text)
                    mapped=True
            if target and not mapped: unmapped_authorships += 1
        if seen: mapped_works.add(work['id'])
        for text in seen:
            strings.setdefault(text,[]).append({k:work.get(k) for k in ('id','display_name','publication_year')})
    n=len(unique)
    related=[{k:v for k,v in row.items() if k!='works'}|measure(len(row['works']),n,'sampled_works')
             for row in other_institutions.values()]
    related.sort(key=lambda r:(-r['count'],r['label']))
    aliases=[]
    if display_name:
        aliases.append(display_name)
        match=re.fullmatch(r'University of (.+)',display_name,re.I)
        if match: aliases.append(match.group(1)+' University')
    alias_pattern=re.compile('|'.join(re.escape(a) for a in sorted(aliases,key=len,reverse=True)),re.I) if aliases else None
    core, sub = {},{}
    location_words={'uk','united kingdom','england','scotland','wales','northern ireland'}
    for raw, rows in strings.items():
        matched=alias_pattern.search(raw) if alias_pattern else None
        if matched:
            observed=matched.group(0).strip()
            core.setdefault(observed,[]).extend(rows)
            prefix=raw[:matched.start()].strip(' ,;.-')
            parts=[p.strip() for p in prefix.split(';') if p.strip()]
            candidate=', '.join(parts).strip(' ,;.-')
            if candidate and candidate.casefold() not in location_words:
                sub.setdefault(candidate,[]).extend(rows)
        elif not aliases:
            sub.setdefault(raw,[]).extend(rows)
    def evidence_rows(values):
        output=[]
        for label, rows in values.items():
            by_id={r.get('id'):r for r in rows if r.get('id')}
            output.append({'id':digest(label),'label':label,**measure(len(by_id),n,'sampled_works'),'works':list(by_id.values())})
        return sorted(output,key=lambda r:(-r['count'],r['label'].casefold()))
    researcher_rows=[]
    for row in researchers.values():
        researcher_rows.append({'id':row['id'],'label':row['label'],'orcid':row['orcid'],
                                'raw_orcid_count':len(raw_orcids_by_profile.get(row['id'],set())),
                                **measure(len(row['works']),n,'sampled_works')})
    researcher_rows.sort(key=lambda r:(-r['count'],r['label'].casefold()))
    return {'mode':'seeded_sample','requested_sample_size':600,'sampled_works':n,'seeds':list(range(42,48)),
            'mapped_work_coverage':measure(len(mapped_works),n,'sampled_works'),
            'target_authorships_without_mapped_string':unmapped_authorships,'observed_target_authorships':target_authorships,
            'rows':[{'id':digest(text),'label':text,**measure(len(rows),n,'sampled_works'),'works':rows}
                    for text,rows in sorted(strings.items(),key=lambda item:(-len(item[1]),item[0]))],
            'core_names':evidence_rows(core),'sub_affiliations':evidence_rows(sub),
            'researchers':{'unique_count':len(researchers),
                           'with_orcid':sum(bool(row.get('orcid')) for row in researchers.values()),
                           'profiles_with_multiple_raw_orcids':sum(len(values)>1 for values in raw_orcids_by_profile.values()),
                           'raw_orcids_on_multiple_profiles':sum(len(values)>1 for values in profiles_by_raw_orcid.values()),
                           'by_year':[{'id':str(year),'label':str(year),'count':len(ids)} for year,ids in sorted(researchers_by_year.items())],
                           'top':researcher_rows[:20],'denominator':'sampled_works'},
            'other_institutions':related,
            'note':'Core names and sub-affiliations are parsed from published strings explicitly mapped to the selected institution, counted once per sampled work. Sub-affiliations are text before the matched core name; they are evidence, not an inferred organisational hierarchy. The sample cannot reveal works OpenAlex failed to connect to the selected institution.'}
