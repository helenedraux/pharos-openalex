"""Human-readable exports from an immutable coverage overview, without API calls."""
import copy
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlencode
from xml.sax.saxutils import escape

from pharos.corpus import digest
from pharos.exports import csv_text

RUNTIME = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies'
HEADERS = ['Section', 'Recorded item', 'Count', 'Denominator', 'Share', 'Population', 'OpenAlex ID or key', 'Notes']


def prepare(report):
    result = copy.deepcopy(report)
    result.pop('export_snapshot_id', None)
    result['export_snapshot_id'] = digest(result)
    return result


def sections(p):
    g = p['groups']
    if p.get('report_type') in ('researcher','source','funder','publisher'):
        yield 'Works by year', g['annual'], 'Core-corpus works linked to this OpenAlex profile.'
        yield 'Primary Fields', g['subjects'], 'Shares use works with a classified primary topic.'
        if g.get('sdgs'): yield 'Predicted Sustainable Development Goals', g['sdgs'], 'Machine-learning tags; counts overlap.'
        yield 'Work types', g['types'], 'OpenAlex work-type categories.'
        if p.get('report_type')=='funder' and g.get('institutions'): yield 'Institutions on linked works', g['institutions'], 'Whole counts overlap; these are affiliations on linked works, not award recipients or investigators.'
        if p.get('report_type')=='publisher' and g.get('sources'): yield 'Leading sources', g['sources'], 'Primary sources in the recorded publisher lineage; leading returned groups, not a complete inventory.'
        if p.get('open_access'): yield 'Open access status', p['open_access']['statuses'], p['open_access']['definition']
        if p.get('citations'):
            c=p['citations']; yield 'Citation indicators',[{'id':'cited','label':'Cited at least once',**c['cited']},{'id':'top_10_percent','label':'OpenAlex normalized top 10% flag',**c['top_10_percent']},{'id':'top_1_percent','label':'OpenAlex normalized top 1% flag',**c['top_1_percent']}],c['note']
        yield 'Metadata coverage',[{'id':k,'label':k.replace('_',' '),**v} for k,v in p['coverage'].items()],'Recorded metadata on linked works.'
        return
    venue = p.get('selected_venue_view') or p['venues']
    kind = venue.get('work_type') or 'all work types'
    yield 'Publications by year', g['annual'], 'Eligible works; incomplete current year is flagged in the source.'
    yield 'Primary Fields', g['subjects'], 'Shares use classified works only. Unclassified works are excluded.'
    if g.get('subfields'): yield 'Primary Subfields', g['subfields'], 'Shares use works with a classified primary Field.'
    if g.get('topics'): yield 'Primary Topics', g['topics'], 'Leading primary Topics returned by OpenAlex.'
    if g.get('sdgs'): yield 'Predicted Sustainable Development Goals', g['sdgs'], 'Machine-learning tags above OpenAlex’s 0.4 threshold. Counts overlap because a work can carry several goals.'
    yield 'Work types', g['types'], 'Raw OpenAlex categories. Shares use eligible works.'
    if p.get('open_access'): yield 'Open access status', p['open_access']['statuses'], p['open_access']['definition']
    if p.get('citations'):
        c=p['citations']
        yield 'Citation indicators', [
            {'id':'cited','label':'Cited at least once',**c['cited']},
            {'id':'top_10_percent','label':'OpenAlex normalized top 10% flag',**c['top_10_percent']},
            {'id':'top_1_percent','label':'OpenAlex normalized top 1% flag',**c['top_1_percent']}], c['note']
        yield 'Cited works by publication year', [dict(row['cited'],id=row['year'],label=row['year']) for row in c['by_publication_year']], c['note']
    yield 'Collaboration: institutions', g['institutions'], 'Institutions recorded on the same works. Whole counts overlap; target excluded. Geography uses OpenAlex institution records.'
    yield 'Collaboration: countries', g['countries'], 'Countries recorded on the same works. Includes home country. Whole counts overlap.'
    yield 'Main sources', venue['sources'], f'{kind}. Sources attached to OpenAlex primary locations; alternative locations excluded.'
    yield 'Direct publishers', venue['publishers'], f'{kind}. Leading direct publisher hosts; parents not combined; institutional hosts excluded.'
    yield 'Metadata coverage', [{'id':k, 'label':k.replace('_',' '), **v} for k,v in p['coverage'].items()], 'Missing metadata is unknown, not negative evidence.'
    yield 'Source coverage', [{'id':'source', 'label':'Main source recorded', **venue['source_coverage']}, {'id':'host', 'label':'Source host recorded', **venue['host_coverage']}], f'{kind}. Host coverage includes institutional and publisher hosts.'
    if p.get('affiliations',{}).get('rows'):
        yield 'Published affiliation names: sample', p['affiliations']['rows'], p['affiliations']['note']
    if p.get('diagnostics'):
        d=p['diagnostics']
        yield 'Missing primary Field: by year', d['unclassified_subject']['by_year'], d['unclassified_subject']['note']
        yield 'Missing primary Field: work types', d['unclassified_subject']['by_work_type'], d['unclassified_subject']['note']
        yield 'Abstract recording: by year', d['abstracts']['by_year'], d['abstracts']['note']
        yield 'Abstract recording: by work type', d['abstracts']['by_work_type'], d['abstracts']['note']
        yield 'Abstract recording: lowest-coverage Fields', d['abstracts']['lowest_coverage_fields'], d['abstracts']['note']
        yield 'DOI coverage: by work type', d['doi']['by_work_type'], d['doi']['note']
        yield 'Primary-source coverage: by year', d['primary_source']['by_year'], d['primary_source']['note']
        yield 'Primary-source coverage: by work type', d['primary_source']['by_work_type'], d['primary_source']['note']


def metadata(p):
    if p.get('report_type') in ('researcher','source','funder','publisher'):
        identity=p['identity']; kind={'researcher':'Researcher','source':'Source','funder':'Funder','publisher':'Publisher'}[p['report_type']]
        rows=[[kind,identity['display_name']],['OpenAlex ID',identity['id']],['Retrieved',p['retrieved_at']],['Core works',p['population']['eligible_works']],['Export snapshot ID',p['export_snapshot_id']]]
        if p['report_type']=='researcher':
            period=p.get('period'); label=(period['from'][:4]+'–'+period['to'][:4]) if period else 'All career'
            rows.extend([['ORCID',identity.get('orcid') or 'Unknown'],['Period',label]])
        else:
            period=p.get('period'); label=(str(period['from'])[:4]+'–'+str(period['to'])[:4]) if period else 'Legacy all-years snapshot'
            if p['report_type']=='source': rows.extend([['Source type',identity.get('type') or 'Unknown'],['ISSN-L',identity.get('issn_l') or 'Unknown'],['Host organisation',identity.get('host_organization_name') or 'Unknown'],['Period',label]])
            elif p['report_type']=='funder': rows.extend([['Country',identity.get('country_code') or 'Unknown'],['Crossref Funder ID',(identity.get('ids') or {}).get('crossref') or 'Unknown'],['Period',label]])
            else: rows.extend([['Countries',', '.join(identity.get('country_codes') or []) or 'Unknown'],['Hierarchy level',identity.get('hierarchy_level')],['Period',label]])
        return rows
    venue = p.get('selected_venue_view') or p['venues']
    return [
        ['Institution', p['identity']['display_name']], ['OpenAlex ID', p['identity']['id']],
        ['ROR', p['identity'].get('ror') or 'Unknown'], ['Period from', p['corpus']['period']['from']],
        ['Period through', p['corpus']['period']['to']], ['Overview retrieved', p['retrieved_at']],
        ['Eligible works', p['population']['eligible_works']], ['Classified works', p['population']['classified_works']],
        ['Unclassified works', p['population']['unclassified_works']], ['Retractions retained', p['retracted_works']['count']],
        ['Source-view work type', venue.get('work_type') or 'All work types'], ['Source-view retrieved', venue['retrieved_at']],
        ['Report specification', p['overview_specification']], ['Corpus hash', p['corpus_specification_hash']],
        ['Export snapshot ID', p['export_snapshot_id']], ['Scope', 'Direct affiliations; core corpus; all work types; retractions retained; whole counts'],
        ['Affiliation evidence', 'Loaded live as a separate ranked raw-string audit; not embedded in this saved aggregate'],
        ['Source', 'https://api.openalex.org/works'],
        ['Export content', 'Aggregate overview, not a full record-level corpus. Tables retain all returned groups; a group limit is not an exhaustive inventory.'],
    ]


def table_rows(p):
    rows = []
    for section, items, note in sections(p):
        for r in items:
            share = None if not r['denominator'] else r['count']/r['denominator']
            rows.append([section, r.get('label') or str(r['id']), r['count'], r['denominator'], share,
                         r['population'], str(r['id']), note])
    return rows


def csv_bytes(p):
    extra = ['Entity', 'Period from', 'Period through', 'Retrieved at', 'Snapshot ID']
    period=p.get('corpus',{}).get('period',{}); context = [p['identity']['display_name'],period.get('from','All years'),period.get('to','All years'),p['retrieved_at'],p['export_snapshot_id']]
    rows = [r + context for r in table_rows(p)]
    for label, value in metadata(p):
        rows.append(['Provenance',label,None,None,None,'','',value] + context)
    for warning in p.get('warnings',[p.get('note','')]):
        rows.append(['Method','Limitation',None,None,None,'','',warning] + context)
    # UTF-8 BOM makes non-ASCII institution names readable in Excel's CSV import.
    return ('\ufeff' + csv_text(HEADERS+extra,rows)).encode('utf-8')


def xlsx_payload(p):
    queries = []
    for q in p.get('queries',[]):
        queries.append([q['retrieved_at'], 'https://api.openalex.org/'+q['path']+'?'+urlencode(q['params']),q['response_hash']])
    return {'metadata':metadata(p), 'headers':HEADERS, 'rows':table_rows(p), 'queries':queries,
            'warnings':p.get('warnings',[p.get('note','')])+([p['affiliations']['note']] if p.get('affiliations') else []),
            'affiliation_works':[[r['label'],w['id'],w.get('display_name') or 'Untitled',w.get('publication_year')] for r in p.get('affiliations',{}).get('rows',[]) for w in r.get('works',[])]}


def build_xlsx(p, target, previews=None):
    modules = Path(os.environ.get('PHAROS_EXPORT_NODE_MODULES',str(RUNTIME/'node/node_modules')))
    node = os.environ.get('PHAROS_EXPORT_NODE',str(RUNTIME/'node/bin/node'))
    if not (modules/'@oai/artifact-tool').is_dir() or not Path(node).is_file():
        raise ValueError('Excel export needs the Artifact Tool runtime. Configure PHAROS_EXPORT_NODE and PHAROS_EXPORT_NODE_MODULES; CSV remains available.')
    with tempfile.TemporaryDirectory(prefix='pharos-xlsx-') as tmp:
        folder=Path(tmp)
        (folder/'node_modules').symlink_to(modules,target_is_directory=True)
        shutil.copyfile(Path(__file__).with_name('xlsx_export.mjs'),folder/'build.mjs')
        (folder/'input.json').write_text(json.dumps(xlsx_payload(p)),encoding='utf-8')
        args=[node,str(folder/'build.mjs'),str(folder/'input.json'),str(Path(target).resolve())]
        if previews: args.append(str(Path(previews).resolve()))
        env={k:v for k,v in os.environ.items() if k != 'OPENALEX_API_KEY'}
        completed=subprocess.run(args,capture_output=True,timeout=120,env=env)
        if completed.returncode:
            raise ValueError('Excel export could not be generated. CSV and JSON remain available; check the local export runtime.')


def build_entity_pdf(p, target):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.pagesizes import A4
    styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name='PharosEntityTitle',fontName='Helvetica-Bold',fontSize=24,leading=29,textColor=colors.HexColor('#17233a'),spaceAfter=14)); styles.add(ParagraphStyle(name='PharosEntityHeading',fontName='Helvetica-Bold',fontSize=15,leading=19,textColor=colors.HexColor('#17233a'),spaceBefore=15,spaceAfter=8))
    para=lambda value,style='BodyText':Paragraph(escape(str(value)),styles[style]); story=[para('PHAROS / OPENALEX '+p['report_type'].upper()+' REPORT','BodyText'),para(p['identity']['display_name'],'PharosEntityTitle'),para(p.get('note','')),Spacer(1,10)]
    meta=Table([[para(k),para(v)] for k,v in metadata(p)],colWidths=[140,350]);meta.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.25,colors.HexColor('#c7ccd1')),('PADDING',(0,0),(-1,-1),6)]));story.append(meta)
    for name,items,note in sections(p):
        story.extend([para(name,'PharosEntityHeading'),para(note)])
        rows=[[para(r.get('label',r.get('id'))),f"{r['count']:,}",f"{r['denominator']:,}",f"{r['percentage']:.1f}%"] for r in items[:20]]
        if rows:
            table=Table([[para('Item'),para('Count'),para('Denominator'),para('Share')]]+rows,colWidths=[270,70,90,60],repeatRows=1);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef0f1')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.25,colors.HexColor('#c7ccd1')),('PADDING',(0,0),(-1,-1),5)]));story.append(table)
    SimpleDocTemplate(str(target),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=42,bottomMargin=42,title='Pharos '+p['report_type']+' report',author='Pharos').build(story)


def build_pdf(p, target):
    if p.get('report_type') in ('researcher','source','funder','publisher'):
        return build_entity_pdf(p,target)
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    from reportlab.graphics.shapes import Drawing, Line, Circle, String
    from reportlab.lib.pagesizes import A4
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='PharosTitle',fontName='Helvetica-Bold',fontSize=24,leading=29,textColor=colors.HexColor('#183047'),spaceAfter=14))
    styles.add(ParagraphStyle(name='PharosHeading',fontName='Helvetica-Bold',fontSize=15,leading=19,textColor=colors.HexColor('#183047'),spaceBefore=12,spaceAfter=9))
    styles.add(ParagraphStyle(name='PharosBody',fontSize=10,leading=14,spaceAfter=8,textColor=colors.HexColor('#33495e'),splitLongWords=True))
    styles.add(ParagraphStyle(name='PharosSmall',fontSize=8,leading=11,spaceAfter=6,textColor=colors.HexColor('#526477'),splitLongWords=True))
    styles.add(ParagraphStyle(name='PharosCell',fontSize=9,leading=12,splitLongWords=True))
    def para(text,style='PharosBody'):
        # Plain source text is escaped; no source HTML is interpreted.
        return Paragraph(escape(str(text)).replace('\n','<br/>'),styles[style])
    story=[]
    def title(text): story.append(para(text,'PharosHeading'))
    def table(headers,rows,widths):
        data=[[para(x,'PharosCell') for x in headers]]+[[para('Unknown' if x is None else x,'PharosCell') for x in row] for row in rows]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eff9')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#b8c9dc')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f6f8fb')]),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        story.append(t)
    def measures(name,rows,note,limit=None,item_label='Recorded item'):
        title(name)
        story.append(para(note,'PharosSmall'))
        shown=rows[:limit] if limit else rows
        if not shown: story.append(para('No observations available.')); return
        table([item_label,'Works','Denominator','Share'],[[r.get('label',r['id']),f"{r['count']:,}",f"{r['denominator']:,}",'Unknown' if not r['denominator'] else f"{100*r['count']/r['denominator']:.2f}%"] for r in shown],[279,65,83,64])
        if limit and len(rows)>limit: story.append(para(f'Showing {limit} of {len(rows)} returned items. CSV, Excel, and JSON include all returned items.','PharosSmall'))
    story.append(para('PHAROS / COVERAGE REPORT','PharosSmall'))
    story.append(para(p['identity']['display_name'],'PharosTitle'))
    story.append(para(f"{p['corpus']['period']['from']} to {p['corpus']['period']['to']} | Retrieved {p['retrieved_at'][:10]}"))
    story.append(para('How well does OpenAlex cover your research? Use your knowledge of the institution to inspect its recorded output, subjects, sources, and affiliations.'))
    story.append(para(f"{p['population']['eligible_works']:,} eligible works. Direct institution assignment; core corpus; all work types; retractions retained."))
    story.append(para('Eligible means matching the saved institution and period filters. Counts describe OpenAlex records, not completeness against your own records. The core corpus excludes the expansion corpus.','PharosSmall'))
    if p.get('briefing'):
        coverage_rows=[(key.replace('_',' '),value['percentage']) for key,value in p['coverage'].items()]
        lowest=min(coverage_rows,key=lambda row:row[1]); highest=max(coverage_rows,key=lambda row:row[1])
        story.append(para(f'Recorded metadata ranges from {lowest[0]} at {lowest[1]:.1f}% to {highest[0]} at {highest[1]:.1f}%.'))
        title('Plain-language briefing')
        for sentence in p['briefing']['sentences']: story.append(para(sentence['text']))
        if p['briefing'].get('rules') and not p['briefing']['rules'].startswith('Fixed templates'):
            story.append(para(p['briefing']['rules'],'PharosSmall'))
    measures('Coverage at a glance',[{'id':k, 'label':k.replace('_',' '),**v} for k,v in p['coverage'].items()],'Missing metadata is unknown. Field shares later in this report use classified works only.')
    title('Publications over time')
    annual=p['groups']['annual']; drawing=Drawing(491,165)
    peak=max([r['count'] for r in annual]+[1]); width=435; left=38; bottom=30; height=105
    for fraction in (0,.5,1):
        y=bottom+height*fraction
        drawing.add(Line(left,y,480,y,strokeColor=colors.HexColor('#dce4ed')))
        drawing.add(String(0,y-3,f'{round(peak*fraction):,}',fontSize=7,fillColor=colors.HexColor('#526477')))
    points=[]
    for i,r in enumerate(annual):
        x=left+(i/max(1,len(annual)-1))*width; y=bottom+height*r['count']/peak; points.append((x,y))
        if len(annual)<=12 or i in (0,len(annual)-1): drawing.add(String(x,bottom-15,r['label'],fontSize=8,textAnchor='middle'))
        if len(annual)<=12: drawing.add(String(x,y+10,f"{r['count']:,}",fontSize=7,textAnchor='middle',fillColor=colors.HexColor('#183047')))
        drawing.add(Circle(x,y,2.5,fillColor=colors.HexColor('#1856c9'),strokeColor=colors.HexColor('#1856c9')))
    for a,b in zip(points,points[1:]): drawing.add(Line(*a,*b,strokeColor=colors.HexColor('#1856c9'),strokeWidth=1.7))
    story.append(drawing)
    story.append(para('Current-year counts are incomplete when included. Exact annual counts are in the spreadsheet and CSV.','PharosSmall'))
    story.append(PageBreak())
    measures('Subject composition',p['groups']['subjects'],f"{p['population']['classified_works']:,} classified works; {p['population']['unclassified_works']:,} unclassified. Primary OpenAlex Fields.")
    story.append(PageBreak())
    measures('Work types',p['groups']['types'],'Raw OpenAlex categories. Small nonzero shares retain two decimal places.')
    story.append(PageBreak())
    measures('Recorded collaboration: institutions',p['groups']['institutions'],'Whole counts overlap. Target excluded. Country labels use OpenAlex institution records.',10,'Institution')
    measures('Recorded collaboration: countries',p['groups']['countries'],'Whole counts overlap and include the home country.',10,'Country')
    story.append(PageBreak())
    venue=p.get('selected_venue_view') or p['venues']
    story.append(para('Source view: '+(venue.get('work_type') or 'all work types')+f". {venue['eligible_works']:,} eligible works. Retrieved {venue['retrieved_at'][:10]}."))
    measures('Primary sources',venue['sources'],'Primary sources only; alternative locations excluded.',10)
    measures('Direct publishers',venue['publishers'],'Direct publisher hosts only; publisher parents are not combined. Institutional hosts are excluded.',10)
    story.append(para(venue['note'],'PharosSmall'))
    story.append(PageBreak())
    a=p['affiliations']
    if a.get('rows'):
        measures('Published affiliation names',a['rows'],f"{a['sampled_works']} sampled works, with {a['mapped_work_coverage']['count']} containing an explicit mapped affiliation name. Exact names are preserved; departments are not inferred.",8,'Affiliation name')
    else:
        story.append(para('Affiliation evidence is provided in the live interface as a ranked raw-affiliation-string audit and is not embedded in this saved aggregate.','PharosSmall'))
    story.append(PageBreak())
    title('Scope and provenance')
    table(['Field','Saved value'],metadata(p),[138,353])
    title('Limitations')
    for warning in p['warnings']:story.append(para(warning,'PharosSmall'))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#526477'))
        canvas.drawString(52,27,'Pharos | '+p['export_snapshot_id'].split(':')[1][:16]);canvas.drawRightString(A4[0]-52,27,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(str(target),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=42,bottomMargin=47,title='Pharos coverage report',author='Pharos')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)


def export_bytes(report, fmt):
    p=prepare(report)
    if fmt=='json': return json.dumps(p,indent=2,ensure_ascii=False).encode(),'application/json'
    if fmt=='csv': return csv_bytes(p),'text/csv; charset=utf-8'
    if fmt not in ('pdf','xlsx'): raise ValueError('Choose PDF, Excel, CSV or JSON.')
    with tempfile.TemporaryDirectory(prefix='pharos-export-') as tmp:
        target=Path(tmp)/('portrait.'+fmt)
        if fmt=='xlsx': build_xlsx(p,target)
        else:
            try:
                import reportlab
            except ImportError:
                python=os.environ.get('PHAROS_EXPORT_PYTHON',str(RUNTIME/'python/bin/python3'))
                if not Path(python).is_file(): raise ValueError('PDF export needs ReportLab. Install pharos-openalex[exports] or set PHAROS_EXPORT_PYTHON.')
                source=Path(tmp)/'report.json'; source.write_text(json.dumps(p))
                env={k:v for k,v in os.environ.items() if k!='OPENALEX_API_KEY'}
                env['PYTHONPATH']=str(Path(__file__).resolve().parent.parent)
                result=subprocess.run([python,'-m','pharos.report_exports',str(source),str(target)],env=env,capture_output=True,timeout=90)
                if result.returncode: raise ValueError('PDF export could not be generated. Check the local PDF runtime.')
            else: build_pdf(p,target)
        return target.read_bytes(),'application/pdf' if fmt=='pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def build_review_pdf(record, target):
    """Build the human-readable, use-specific output of a completed review."""
    if not isinstance(record,dict) or record.get('schema_version')!='pharos-review-record-v3':
        raise ValueError('Choose a valid Pharos review record.')
    guide=record.get('guide') or {}; purpose=guide.get('purpose') or {}; report=guide.get('report') or {}
    judgements=record.get('judgements') or []; limitations=record.get('limitations') or []
    if not isinstance(judgements,list) or len(judgements)>100 or not purpose.get('label') or not report.get('identity_name'):
        raise ValueError('The review record is incomplete or too large.')
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReviewTitle',fontName='Helvetica-Bold',fontSize=25,leading=30,textColor=colors.HexColor('#111c30'),spaceAfter=12))
    styles.add(ParagraphStyle(name='ReviewHeading',fontName='Helvetica-Bold',fontSize=15,leading=19,textColor=colors.HexColor('#111c30'),spaceBefore=15,spaceAfter=7))
    styles.add(ParagraphStyle(name='ReviewBody',fontSize=10,leading=14,textColor=colors.HexColor('#354155'),spaceAfter=7))
    styles.add(ParagraphStyle(name='ReviewSmall',fontSize=8,leading=11,textColor=colors.HexColor('#596476'),spaceAfter=5))
    styles.add(ParagraphStyle(name='ReviewStatus',fontName='Helvetica-Bold',fontSize=17,leading=21,textColor=colors.HexColor('#8b5d08'),spaceAfter=8))
    para=lambda value,style='ReviewBody':Paragraph(escape(str(value if value not in (None,'') else 'Not recorded')).replace('\n','<br/>'),styles[style])
    readiness=guide.get('readiness') or {}; period=report.get('period') or {}
    period_label='–'.join(filter(None,[str(period.get('from') or period.get('start') or '')[:4],str(period.get('to') or period.get('end') or '')[:4]])) or 'All years'
    story=[para('PHAROS / REVIEW REPORT','ReviewSmall'),para(report['identity_name'],'ReviewTitle'),para('Intended use: '+purpose['label'],'ReviewHeading'),para(readiness.get('label') or 'Review status not recorded','ReviewStatus')]
    metadata_rows=[['OpenAlex object',report.get('identity_name')],['OpenAlex ID',report.get('identity_id')],['Object type',report.get('type')],['Snapshot period',period_label],['Snapshot retrieved',report.get('retrieved_at')],['Review report created',record.get('created_at')],['Intended use',purpose.get('label')]]
    meta=Table([[para(k,'ReviewSmall'),para(v,'ReviewSmall')] for k,v in metadata_rows],colWidths=[125,366]);meta.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#f3e4bf')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.25,colors.HexColor('#c9c2b4')),('PADDING',(0,0),(-1,-1),6)]));story.extend([meta,Spacer(1,9),para(readiness.get('note') or 'This result is specific to the intended use and the requirements recorded below.')])
    story.append(para('Evidence and decisions','ReviewHeading'))
    status_labels={'meets_configured_requirement':'Meets requirement','validation_needed':'Validation needed','does_not_meet_configured_requirement':'Below requirement','not_measured':'Not measured','not_applicable':'Not applicable','not_checked':'Not checked'}
    for index,item in enumerate(judgements,1):
        requirement=item.get('requirement') or {}; observed=item.get('observed') or {}; materiality=item.get('materiality') or {}
        title=item.get('title') or item.get('checklist_item_id') or f'Check {index}'
        story.extend([para(f'{index}. {title}','ReviewHeading'),para(f"{status_labels.get(item.get('status'),item.get('status') or 'Not checked')} · {materiality.get('current','importance not recorded')} importance",'ReviewSmall')])
        if observed.get('summary'): story.append(para('Saved evidence: '+observed['summary']))
        threshold=requirement.get('numeric_current'); rule=(f'At least {threshold}%.' if isinstance(threshold,(int,float)) else requirement.get('current') or 'No numeric threshold; confirmation is required.')
        story.append(para('Requirement: '+str(rule)))
        if item.get('next_step'): story.append(para('Next action: '+item['next_step']))
        if item.get('note'): story.append(para('Reviewer note: '+item['note']))
        for evidence in (item.get('external_evidence') or []):
            if isinstance(evidence,dict) and evidence.get('summary'): story.append(para('External evidence: '+evidence['summary'],'ReviewSmall'))
    if record.get('interoperability'):
        story.extend([PageBreak(),para('Interoperability checks','ReviewHeading')])
        for item in record['interoperability'][:20]: story.append(para(f"{item.get('label','Check')}: {item.get('detail','Not recorded')}"))
    story.append(para('Limitations','ReviewHeading'))
    for limitation in limitations[:30]: story.append(para('• '+str(limitation),'ReviewSmall'))
    story.append(para('This report communicates the result of a use-specific review. It should be read with the accompanying snapshot data, scope, methodology, and provenance.','ReviewSmall'))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#596476'));canvas.drawString(52,27,'Pharos review report | '+str(purpose.get('label'))[:55]);canvas.drawRightString(A4[0]-52,27,str(doc.page));canvas.restoreState()
    SimpleDocTemplate(str(target),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=42,bottomMargin=47,title=f"Pharos review report — {purpose['label']}",author='Pharos').build(story,onFirstPage=footer,onLaterPages=footer)


def review_report_bytes(record):
    with tempfile.TemporaryDirectory(prefix='pharos-review-report-') as tmp:
        target=Path(tmp)/'review-report.pdf'
        try:
            import reportlab
        except ImportError:
            python=os.environ.get('PHAROS_EXPORT_PYTHON',str(RUNTIME/'python/bin/python3'))
            if not Path(python).is_file(): raise ValueError('PDF export needs ReportLab. Install pharos-openalex[exports] or set PHAROS_EXPORT_PYTHON.')
            source=Path(tmp)/'review.json';source.write_text(json.dumps(record),encoding='utf-8')
            env={k:v for k,v in os.environ.items() if k!='OPENALEX_API_KEY'};env['PYTHONPATH']=str(Path(__file__).resolve().parent.parent)
            result=subprocess.run([python,'-m','pharos.report_exports',str(source),str(target),'review'],env=env,capture_output=True,timeout=90)
            if result.returncode: raise ValueError('The PDF review report could not be generated. Check the local PDF runtime.')
        else: build_review_pdf(record,target)
        return target.read_bytes(),'application/pdf'


if __name__=='__main__':
    data=json.loads(Path(sys.argv[1]).read_text())
    build_review_pdf(data,sys.argv[2]) if len(sys.argv)>3 and sys.argv[3]=='review' else build_pdf(data,sys.argv[2])
