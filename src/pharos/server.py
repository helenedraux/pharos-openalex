"""Local-by-default web interface with optional hosted session credentials."""
import argparse
import copy
import json
import os
import queue
import re
import shutil
import signal
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from collections import deque
from urllib.parse import urlsplit, parse_qs
from pharos.backends.openalex_api import APIError, OpenAlex
from pharos.corpus import digest
from pharos.exports import save_json
from pharos.overview import CachedAPI, affiliation_audit, candidates, author_candidates, author_overview, source_candidates, source_overview, funder_candidates, funder_overview, publisher_candidates, publisher_overview, overview, publications, composition, funding_details, researcher_details, researcher_profile, version_pairs, make_spec, venue_view
from pharos.review_guide import available_purposes, build_review_guide, questions_for_purpose
from pharos.review_assist import ReviewAssistError, assistance_status, generate_review_draft

STATIC = Path(__file__).with_name('web')

@dataclass(frozen=True)
class Deployment:
    mode: str
    bind_host: str
    port: int
    allowed_hosts: frozenset[str]
    allowed_origins: frozenset[str]

    def trusts(self, headers, method='GET'):
        """Validate browser-facing authority without consulting proxy headers."""
        if headers.get('Host') not in self.allowed_hosts:
            return False
        origin = headers.get('Origin')
        if origin is not None and origin not in self.allowed_origins:
            return False
        if self.mode == 'hosted' and method not in ('GET', 'HEAD') and origin is None:
            return False
        fetch_site=headers.get('Sec-Fetch-Site')
        if self.mode == 'hosted' and fetch_site is None:
            return False
        return (fetch_site or 'none') in ('same-origin', 'none')


@dataclass
class Session:
    identifier: str
    directory: Path
    jobs: dict
    venue_views: dict
    last_seen: float
    requests: deque
    reports_started: int = 0
    exports_started: int = 0
    exported_bytes: int = 0
    key: str | None = None


class RateLimitError(Exception): pass
class BusyError(Exception): pass
class ResourceLimitError(Exception): pass


class DeadlineAPI(OpenAlex):
    """Cached OpenAlex adapter that stops a report between bounded requests."""
    def __init__(self, delegate, deadline, max_queries=None, max_cost_usd=None, clock=time.monotonic):
        self.delegate=delegate
        self.deadline=deadline
        self.clock=clock
        self.requests=delegate.requests
        self.max_queries=max_queries
        self.max_cost_usd=max_cost_usd
        self.query_count=0
        self.reported_cost_usd=0.0

    @property
    def key(self): return self.delegate.key

    def get(self,path,params=None):
        if self.clock() >= self.deadline: raise ResourceLimitError('The report reached its hosted execution-time limit.')
        if self.max_queries is not None and self.query_count >= self.max_queries:
            raise ResourceLimitError('The report reached its hosted OpenAlex-query limit.')
        self.query_count += 1
        result=self.delegate.get(path,params)
        cost=self.requests[-1].get('reported_cost_usd') if self.requests else None
        if isinstance(cost,(int,float)) and not isinstance(cost,bool): self.reported_cost_usd += cost
        if self.max_cost_usd is not None and self.reported_cost_usd > self.max_cost_usd:
            raise ResourceLimitError('The report reached its hosted OpenAlex cost budget.')
        if self.clock() >= self.deadline: raise ResourceLimitError('The report reached its hosted execution-time limit.')
        return result


class WorkQueue:
    def __init__(self, workers, capacity):
        self.tasks=queue.Queue(maxsize=capacity)
        self.threads=[]
        for number in range(workers):
            worker=threading.Thread(target=self._run,name=f'pharos-worker-{number + 1}',daemon=True)
            worker.start()
            self.threads.append(worker)

    def _run(self):
        while True:
            task=self.tasks.get()
            try:
                if task is None: return
                task()
            finally: self.tasks.task_done()

    def submit(self, task):
        try: self.tasks.put_nowait(task)
        except queue.Full: return False
        return True

    def close(self):
        for _ in self.threads: self.tasks.put(None)
        for worker in self.threads: worker.join(timeout=5)


def _items(values):
    return frozenset(item.strip() for value in values for item in value.split(',') if item.strip())


def deployment_from_args(args):
    if not 0 <= args.port <= 65535:
        raise ValueError('Port must be between 0 and 65535.')
    if args.mode == 'local':
        if args.host != '127.0.0.1':
            raise ValueError('Local mode must bind to 127.0.0.1; use --mode hosted for another host.')
        authority=f'127.0.0.1:{args.port}'
        return Deployment('local',args.host,args.port,frozenset((authority,)),frozenset((f'http://{authority}',)))
    hosts=_items(args.allowed_host)
    origins=_items(args.allowed_origin)
    if not hosts or not origins:
        raise ValueError('Hosted mode requires --allowed-host and --allowed-origin.')
    for host in hosts:
        if '/' in host or '://' in host:
            raise ValueError('Allowed hosts must be exact Host header values, without a scheme or path.')
    for origin in origins:
        parsed=urlsplit(origin)
        if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.path not in ('','/') or parsed.query or parsed.fragment:
            raise ValueError('Allowed origins must be exact http(s) origins, without a path.')
    return Deployment('hosted',args.host,args.port,hosts,origins)


def parser():
    result=argparse.ArgumentParser(description='Open the Pharos coverage report interface.')
    result.add_argument('--mode',choices=('local','hosted'),default=os.environ.get('PHAROS_MODE','local'))
    result.add_argument('--host',default=os.environ.get('PHAROS_HOST'))
    result.add_argument('--port',type=int,default=int(os.environ.get('PORT','0') or 0) or None)
    result.add_argument('--allowed-host',action='append',default=[],help='Exact public Host value; repeat or use commas.')
    result.add_argument('--allowed-origin',action='append',default=[],help='Exact public origin; repeat or use commas.')
    result.add_argument('--data',type=Path,default=Path(os.environ.get('PHAROS_DATA','output/web')))
    result.add_argument('--session-ttl',type=int,default=int(os.environ.get('PHAROS_SESSION_TTL','3600')),help='Hosted session lifetime in seconds (default: 3600).')
    result.add_argument('--session-rate',type=int,default=int(os.environ.get('PHAROS_SESSION_RATE','60')),help='Hosted live requests per session per minute (default: 60).')
    result.add_argument('--network-concurrency',type=int,default=int(os.environ.get('PHAROS_NETWORK_CONCURRENCY','2')),help='Maximum simultaneous OpenAlex operations (default: 2).')
    result.add_argument('--queue-size',type=int,default=int(os.environ.get('PHAROS_QUEUE_SIZE','16')),help='Maximum queued report jobs (default: 16).')
    result.add_argument('--session-reports',type=int,default=int(os.environ.get('PHAROS_SESSION_REPORTS','5')),help='Hosted report starts per session (default: 5).')
    result.add_argument('--session-exports',type=int,default=int(os.environ.get('PHAROS_SESSION_EXPORTS','20')),help='Hosted exports per session (default: 20).')
    result.add_argument('--session-export-bytes',type=int,default=int(os.environ.get('PHAROS_SESSION_EXPORT_BYTES',str(128 * 1024 * 1024))),help='Hosted cumulative export bytes per session.')
    result.add_argument('--max-export-bytes',type=int,default=int(os.environ.get('PHAROS_MAX_EXPORT_BYTES',str(32 * 1024 * 1024))),help='Maximum bytes in one hosted export.')
    result.add_argument('--report-timeout',type=int,default=int(os.environ.get('PHAROS_REPORT_TIMEOUT','300')),help='Hosted report wall-time seconds (default: 300).')
    result.add_argument('--report-queries',type=int,default=int(os.environ.get('PHAROS_REPORT_QUERIES','250')),help='Hosted OpenAlex queries per report (default: 250).')
    result.add_argument('--report-cost-usd',type=float,default=float(os.environ.get('PHAROS_REPORT_COST_USD','0.50')),help='Hosted reported OpenAlex cost per report (default: 0.50 USD).')
    result.add_argument('--max-sessions',type=int,default=int(os.environ.get('PHAROS_MAX_SESSIONS','200')),help='Maximum simultaneous hosted sessions (default: 200).')
    result.add_argument('--request-timeout',type=int,default=int(os.environ.get('PHAROS_REQUEST_TIMEOUT','15')),help='Client socket timeout in seconds (default: 15).')
    return result

class Application:
    def __init__(self, directory, hosted=False, session_ttl=3600, session_rate=60, network_concurrency=2, queue_size=16, session_reports=5, session_exports=20, session_export_bytes=128 * 1024 * 1024, max_export_bytes=32 * 1024 * 1024, report_timeout=300, report_queries=250, report_cost_usd=0.50, max_sessions=200):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True,exist_ok=True)
        self.jobs = {}
        self.lock = threading.Lock()
        self.network_slots = threading.BoundedSemaphore(network_concurrency)
        self.export_lock = threading.Lock()
        self.venue_views = {}
        self.hosted = hosted
        self.session_ttl = session_ttl
        self.session_rate = session_rate
        self.session_reports = session_reports
        self.session_exports = session_exports
        self.session_export_bytes = session_export_bytes
        self.max_export_bytes = max_export_bytes
        self.report_timeout = report_timeout
        self.report_queries = report_queries
        self.report_cost_usd = report_cost_usd
        self.max_sessions = max_sessions
        self.sessions = {}
        self.work_queue = WorkQueue(network_concurrency,queue_size)
        self.key = os.environ.get('OPENALEX_API_KEY')

    def api(self,session=None):
        if self.hosted and session and session.key:
            return CachedAPI(session.directory / 'authenticated-responses',key_provider=lambda:session.key)
        return CachedAPI(self.directory / 'responses',self.key)

    def set_session_key(self,session,key):
        if not self.hosted: raise ValueError('Session keys are available only in hosted mode; use OPENALEX_API_KEY locally.')
        if not isinstance(key,str) or not 8 <= len(key) <= 512 or not key.isascii() or any(character.isspace() or not character.isprintable() for character in key):
            raise ValueError('Enter a valid OpenAlex API key.')
        session.key=key

    def rotate_session(self,session):
        """Invalidate the old browser session identifier after a credential change."""
        if not self.hosted: return session.identifier
        with self.lock:
            previous=session.identifier
            if self.sessions.get(previous) is not session:
                raise ValueError('This session has ended. Reload Pharos and try again.')
            identifier=uuid.uuid4().hex
            while identifier in self.sessions:
                identifier=uuid.uuid4().hex
            self.sessions.pop(previous)
            session.identifier=identifier
            self.sessions[identifier]=session
            return identifier

    def forget_session_key(self,session): session.key=None

    def auth_status(self,session):
        return {'has_key':bool(session.key or self.key),'key_source':'session' if session.key else 'environment' if self.key else 'none'}

    def session(self, identifier=None, now=None):
        if not self.hosted:
            return Session('local',self.directory,self.jobs,self.venue_views,time.monotonic(),deque())
        now=time.monotonic() if now is None else now
        with self.lock:
            expired=[key for key,value in self.sessions.items() if now-value.last_seen > self.session_ttl and not any(job.get('status') in ('queued','loading') for job in value.jobs.values())]
            for key in expired:
                state=self.sessions.pop(key)
                shutil.rmtree(state.directory,ignore_errors=True)
            state=self.sessions.get(identifier)
            if state is None:
                if len(self.sessions) >= self.max_sessions:
                    raise BusyError('Pharos has reached its active-session limit. Try again later.')
                identifier=uuid.uuid4().hex
                directory=self.directory / 'sessions' / identifier
                directory.mkdir(parents=True,exist_ok=False)
                state=Session(identifier,directory,{}, {},now,deque())
                self.sessions[identifier]=state
            state.last_seen=now
            return state

    def consume(self, session, now=None):
        if not self.hosted: return
        now=time.monotonic() if now is None else now
        with self.lock:
            while session.requests and now-session.requests[0] >= 60: session.requests.popleft()
            if len(session.requests) >= self.session_rate:
                raise RateLimitError('This session has reached its live-request budget. Try again in a minute.')
            session.requests.append(now)

    def live(self, session, operation):
        self.consume(session)
        if not self.network_slots.acquire(blocking=False):
            raise BusyError('Pharos is handling its maximum number of live requests. Try again shortly.')
        try: return operation()
        finally: self.network_slots.release()

    def close(self): self.work_queue.close()

    def consume_export(self,session):
        if not self.hosted: return
        with self.lock:
            if session.exports_started >= self.session_exports:
                raise ResourceLimitError('This session has reached its export-count limit.')
            session.exports_started += 1

    def account_export(self,session,size):
        if not self.hosted: return
        with self.lock:
            if size > self.max_export_bytes:
                raise ResourceLimitError('This export exceeds the hosted per-file size limit.')
            if session.exported_bytes + size > self.session_export_bytes:
                raise ResourceLimitError('This session has reached its cumulative export-size limit.')
            session.exported_bytes += size

    def target(self, institution,start,end,directory=None):
        spec = make_spec(institution,start,end)
        return (directory or self.directory) / (digest(spec).split(':')[1] + '.json')

    def start(self,institution,start,end,kind='institution',session=None):
        session=session or self.session()
        scope={'kind':kind,'id':institution,'scope':'all-core-works'}
        if kind!='author': scope['period']={'start':start,'end':end}
        target = self.target(institution,start,end,session.directory) if kind=='institution' else session.directory / (kind+'-' + digest(scope).split(':')[1] + '.json')
        with self.lock:
            for identifier,job in session.jobs.items():
                if job['target'] == str(target) and job['status'] in ('queued','loading'): return identifier
            if self.hosted and session.reports_started >= self.session_reports:
                raise ResourceLimitError('This session has reached its report-start limit.')
            if self.hosted: session.reports_started += 1
            identifier = uuid.uuid4().hex
            session.jobs[identifier] = {'status':'queued','message':'Waiting for an available report worker','target':str(target)}
        def task():
            try:
                with self.lock: session.jobs[identifier].update(status='loading',message='Preparing your coverage report')
                cached = json.loads(target.read_text()) if target.exists() else None
                expected=12 if kind=='author' else 5 if kind=='funder' else 2 if kind in ('source','publisher') else 16
                if cached and cached.get('implementation_version') == expected:
                    result = cached
                else:
                    def progress(message):
                        with self.lock: session.jobs[identifier]['message'] = message
                    self.consume(session)
                    api=self.api(session)
                    if self.hosted: api=DeadlineAPI(api,time.monotonic()+self.report_timeout,self.report_queries,self.report_cost_usd)
                    with self.network_slots: result = author_overview(api,institution,start,end,progress) if kind=='author' else source_overview(api,institution,start,end,progress) if kind=='source' else funder_overview(api,institution,start,end,progress) if kind=='funder' else publisher_overview(api,institution,start,end,progress) if kind=='publisher' else overview(api,institution,start,end,progress)
                    save_json(target,result)
                with self.lock: session.jobs[identifier].update(status='complete',result=result)
            except ResourceLimitError as exc:
                with self.lock: session.jobs[identifier].update(status='error',message=str(exc))
            except (APIError,ValueError,OSError,KeyError,TypeError,RateLimitError):
                with self.lock: session.jobs[identifier].update(status='error',message='OpenAlex is unavailable or returned incomplete data. Try again; completed queries are cached locally.')
        if not self.work_queue.submit(task):
            with self.lock:
                session.jobs.pop(identifier,None)
                if self.hosted: session.reports_started -= 1
            raise BusyError('The report queue is full. Try again shortly.')
        return identifier

    def saved(self,directory=None):
        rows=[]
        for path in (directory or self.directory).glob('*.json'):
            try:
                p=json.loads(path.read_text())
                if p.get('mode') == 'live_aggregates':
                    kind={'researcher':'author','source':'source','funder':'funder','publisher':'publisher'}.get(p.get('report_type'),'institution')
                    period=p.get('corpus',{}).get('period') or p.get('period')
                    year=lambda value:int(str(value)[:4])
                    start=year(period['from']) if period else None
                    end=year(period['to']) if period else None
                    scope={'kind':kind,'id':p['identity']['id'],'start':start,'end':end}
                    rows.append({'institution':p['identity']['id'],'kind':kind,'name':p['identity']['display_name'],'start':start,'end':end,'retrieved_at':p['retrieved_at'],'count':p['population']['eligible_works'],'scope_key':digest(scope)})
            except (OSError,ValueError,KeyError): pass
        # Equivalent ID spellings created separate files in early prototypes.
        # Collapse only the listing; retain every existing file on disk.
        unique = {}
        for row in sorted(rows,key=lambda r:r['retrieved_at'],reverse=True):
            unique.setdefault(row['scope_key'],row)
        return [{k:v for k,v in row.items() if k!='scope_key'} for row in unique.values()]

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.request.settimeout(self.server.request_timeout)
    def log_message(self,*args): pass
    def send(self,status,data,content_type='application/json',filename=None):
        body = data if isinstance(data,bytes) else json.dumps(data).encode() if content_type == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        if filename: self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        if getattr(self,'_new_session_cookie',None):
            secure='; Secure' if all(origin.startswith('https://') for origin in self.server.deployment.allowed_origins) else ''
            self.send_header('Set-Cookie',f'pharos_session={self._new_session_cookie}; Path=/; HttpOnly; SameSite=Strict{secure}')
        self.end_headers()
        self.wfile.write(body)
    def trusted(self):
        return self.server.deployment.trusts(self.headers,self.command)
    def session(self):
        cookie=self.headers.get('Cookie','')
        match=re.search(r'(?:^|;\s*)pharos_session=([0-9a-f]{32})(?:;|$)',cookie)
        requested=match.group(1) if match else None
        state=self.server.app.session(requested)
        if state.identifier != requested: self._new_session_cookie=state.identifier
        return state
    def do_GET(self):
        if urlsplit(self.path).path == '/healthz': return self.send(200,{'status':'ok'})
        if not self.trusted(): return self.send(403,{'error':'Use the configured Pharos address.'})
        path=urlsplit(self.path).path
        params=parse_qs(urlsplit(self.path).query)
        value=lambda key,default='':params.get(key,[default])[0]
        try:
            app=self.server.app
            session=self.session()
            if path in ('/','/**','/index.html','/app.js','/style.css'):
                name='index.html' if path in ('/','/**','/index.html') else path[1:]
                content_type='text/html; charset=utf-8' if name == 'index.html' else 'text/javascript; charset=utf-8' if name == 'app.js' else 'text/css; charset=utf-8'
                return self.send(200,(STATIC/name).read_bytes(),content_type)
            if path == '/api/config': return self.send(200,{'current_year':date.today().year,**app.auth_status(session),'review_assistance':assistance_status(),'accepts_session_key':app.hosted and all(origin.startswith('https://') for origin in self.server.deployment.allowed_origins),'saved':app.saved(session.directory)})
            if path == '/api/search':
                result=app.live(session,lambda: author_candidates(app.api(session),value('q')) if value('kind')=='author' else source_candidates(app.api(session),value('q')) if value('kind')=='source' else funder_candidates(app.api(session),value('q')) if value('kind')=='funder' else publisher_candidates(app.api(session),value('q')) if value('kind')=='publisher' else candidates(app.api(session),value('q')))
                return self.send(200,result)
            if path == '/api/job':
                with app.lock: job=dict(session.jobs.get(value('id'),{}))
                job.pop('target',None)
                return self.send(200,job) if job else self.send(404,{'error':'This session has ended. Open the saved report again.'})
            if path == '/api/venues':
                spec=make_spec(value('institution'),int(value('start')),int(value('end')))
                result=app.live(session,lambda: venue_view(app.api(session),spec,value('work_type')))
                view_id=digest(result)
                with app.lock: session.venue_views[view_id]=(spec['resolved_openalex_id'],spec['period'],copy.deepcopy(result))
                result['view_id']=view_id
                return self.send(200,result)
            if path == '/api/publications':
                result=app.live(session,lambda: publications(app.api(session),value('institution'),int(value('start')),int(value('end')),value('kind'),value('value'),int(value('page','1')),value('work_type')))
                return self.send(200,result)
            if path == '/api/composition':
                result=app.live(session,lambda: composition(app.api(session),value('institution'),int(value('start')),int(value('end')),int(value('year')),value('kind')))
                return self.send(200,result)
            if path == '/api/funding-details':
                result=app.live(session,lambda: funding_details(app.api(session),value('institution'),int(value('start')),int(value('end'))))
                return self.send(200,result)
            if path == '/api/researchers':
                result=app.live(session,lambda: researcher_details(app.api(session),value('institution'),int(value('start')),int(value('end'))))
                return self.send(200,result)
            if path == '/api/affiliations':
                result=app.live(session,lambda: affiliation_audit(app.api(session),value('institution'),value('name'),value('country')))
                return self.send(200,result)
            if path == '/api/researcher-profile':
                result=app.live(session,lambda: researcher_profile(app.api(session),value('institution'),value('author')))
                return self.send(200,result)
            if path == '/api/version-pairs':
                result=app.live(session,lambda: version_pairs(app.api(session),value('institution'),int(value('start')),int(value('end'))))
                return self.send(200,result)
            return self.send(404,{'error':'Not found'})
        except (ValueError,APIError) as exc: return self.send(400,{'error':str(exc)})
        except RateLimitError as exc: return self.send(429,{'error':str(exc)})
        except BusyError as exc: return self.send(503,{'error':str(exc)})
        except (OSError,KeyError,TypeError): return self.send(502,{'error':'Could not read OpenAlex data. Try again.'})
    def do_POST(self):
        if not self.trusted(): return self.send(403,{'error':'Use the configured Pharos address.'})
        if self.path not in ('/api/overview','/api/export','/api/session-key','/api/review-guide'): return self.send(404,{'error':'Not found'})
        try:
            app=self.server.app
            session=self.session()
            if self.path == '/api/session-key': app.consume(session)
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 4096: raise ValueError('Invalid request size.')
            body=json.loads(self.rfile.read(length))
            if self.path == '/api/session-key':
                if not all(origin.startswith('https://') for origin in self.server.deployment.allowed_origins):
                    raise ValueError('Session keys require an HTTPS hosted origin.')
                if body == {'action':'forget'}: app.forget_session_key(session)
                elif set(body) == {'key'}:
                    app.set_session_key(session,body['key'])
                    self._new_session_cookie=app.rotate_session(session)
                else: raise ValueError('Invalid session-key action.')
                return self.send(200,app.auth_status(session))
            if self.path == '/api/export':
                from pharos.report_exports import export_bytes
                with app.lock:
                    job=session.jobs.get(body.get('job'),{})
                    if job.get('status') != 'complete': raise ValueError('Reopen the report before exporting.')
                    report=copy.deepcopy(job['result'])
                    if body.get('venue_id'):
                        venue=session.venue_views.get(body['venue_id'])
                        if not venue or venue[0] != report['identity']['id'] or venue[1] != report['corpus']['period']:
                            raise ValueError('Reload the selected source view before exporting.')
                        report['selected_venue_view']=copy.deepcopy(venue[2])
                fmt=body.get('format')
                app.consume_export(session)
                with app.export_lock:
                    content,mime=export_bytes(report,fmt)
                    app.account_export(session,len(content))
                return self.send(200,content,mime,'pharos-coverage.'+fmt)
            if self.path == '/api/review-guide':
                with app.lock:
                    job=session.jobs.get(body.get('job'),{})
                    if job.get('status') != 'complete': raise ValueError('Reopen the report before starting a review guide.')
                    report=copy.deepcopy(job['result'])
                if body.get('action') == 'purposes':
                    return self.send(200,{'purposes':available_purposes(report.get('report_type','institution'))})
                if body.get('action') == 'questions':
                    return self.send(200,{'questions':questions_for_purpose(report.get('report_type') or 'institution',body.get('purpose'))})
                if body.get('action') == 'assist':
                    if set(body) - {'job','purpose','answers','action','item','context'}: raise ValueError('Invalid model-assistance request.')
                    guide=build_review_guide(report,body.get('purpose'),body.get('answers'))
                    item=next((row for row in guide['items'] if row['id'] == body.get('item')),None)
                    if item is None: raise ValueError('Choose a checklist item from this review guide.')
                    result=app.live(session,lambda:generate_review_draft(guide,item,body.get('context','')))
                    return self.send(200,result)
                if set(body) not in ({'job','purpose'},{'job','purpose','answers'}): raise ValueError('Choose a valid review purpose.')
                return self.send(200,build_review_guide(report,body['purpose'],body.get('answers')))
            kind=body.get('kind','institution')
            if kind not in ('institution','author','source','funder','publisher'): raise ValueError('Unknown report type.')
            identifier=self.server.app.start(body['institution'],int(body['start']),int(body['end']),kind,session)
            self.send(202,{'id':identifier})
        except ValueError as exc: self.send(400,{'error':str(exc)})
        except RateLimitError as exc: self.send(429,{'error':str(exc)})
        except BusyError as exc: self.send(503,{'error':str(exc)})
        except ResourceLimitError as exc: self.send(429,{'error':str(exc)})
        except ReviewAssistError as exc: self.send(502,{'error':str(exc)})
        except (KeyError,TypeError): self.send(400,{'error':'Confirm an institution and select valid years (up to 50 years).'})
        except Exception:
            # Suppress subprocess diagnostics and local paths in browser responses.
            message='The export could not be generated. Try CSV or JSON, or check the local export runtime.' if self.path == '/api/export' else 'The report could not be built. OpenAlex may be temporarily unavailable; try again.'
            self.send(500,{'error':message})


def main():
    args=parser().parse_args()
    args.host=args.host or ('127.0.0.1' if args.mode == 'local' else '0.0.0.0')
    args.port=args.port or (8765 if args.mode == 'local' else 7860)
    args.allowed_host=args.allowed_host or ([os.environ['PHAROS_ALLOWED_HOSTS']] if os.environ.get('PHAROS_ALLOWED_HOSTS') else [])
    args.allowed_origin=args.allowed_origin or ([os.environ['PHAROS_ALLOWED_ORIGINS']] if os.environ.get('PHAROS_ALLOWED_ORIGINS') else [])
    if args.session_ttl < 60: raise SystemExit('Session TTL must be at least 60 seconds.')
    if args.session_rate < 1 or args.network_concurrency < 1 or args.queue_size < 1:
        raise SystemExit('Session rate, network concurrency, and queue size must be positive.')
    if min(args.session_reports,args.session_exports,args.session_export_bytes,args.max_export_bytes,args.report_timeout,args.report_queries) < 1 or args.report_cost_usd <= 0:
        raise SystemExit('Hosted resource limits must be positive.')
    if args.max_sessions < 1 or args.request_timeout < 1:
        raise SystemExit('Session and request-timeout limits must be positive.')
    try: deployment=deployment_from_args(args)
    except ValueError as exc: raise SystemExit(str(exc)) from exc
    server=ThreadingHTTPServer((deployment.bind_host,deployment.port),Handler)
    server.app=Application(args.data,hosted=deployment.mode == 'hosted',session_ttl=args.session_ttl,
        session_rate=args.session_rate,network_concurrency=args.network_concurrency,queue_size=args.queue_size,
        session_reports=args.session_reports,session_exports=args.session_exports,
        session_export_bytes=args.session_export_bytes,max_export_bytes=args.max_export_bytes,
        report_timeout=args.report_timeout,report_queries=args.report_queries,report_cost_usd=args.report_cost_usd,
        max_sessions=args.max_sessions)
    server.deployment=deployment
    server.request_timeout=args.request_timeout
    def stop(_signum,_frame): threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    print(f'Pharos {deployment.mode} interface listening on {deployment.bind_host}:{server.server_port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.server_close()
        server.app.close()

if __name__ == '__main__': main()
