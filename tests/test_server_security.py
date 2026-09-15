import argparse
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, Mock, patch

from pharos.server import Application, BusyError, DeadlineAPI, Deployment, RateLimitError, ResourceLimitError, WorkQueue, deployment_from_args
from pharos.backends.openalex_api import OpenAlex


class Headers(dict):
    def get(self,key,default=None):
        return super().get(key,default)


class ServerSecurity(unittest.TestCase):
    def local(self,**changes):
        values=dict(mode='local',host='127.0.0.1',port=8765,allowed_host=[],allowed_origin=[])
        values.update(changes)
        return deployment_from_args(argparse.Namespace(**values))

    def hosted(self):
        return Deployment('hosted','0.0.0.0',7860,frozenset(('example.hf.space',)),frozenset(('https://example.hf.space',)))

    def test_local_defaults_remain_loopback_only(self):
        deployment=self.local()
        self.assertEqual((deployment.bind_host,deployment.port),('127.0.0.1',8765))
        self.assertTrue(deployment.trusts(Headers({'Host':'127.0.0.1:8765','Origin':'http://127.0.0.1:8765','Sec-Fetch-Site':'same-origin'})))
        self.assertFalse(deployment.trusts(Headers({'Host':'localhost:8765','Sec-Fetch-Site':'none'})))
        with self.assertRaises(ValueError): self.local(host='0.0.0.0')

    def test_hosted_mode_requires_fixed_allowlists(self):
        with self.assertRaises(ValueError):
            deployment_from_args(argparse.Namespace(mode='hosted',host='0.0.0.0',port=7860,allowed_host=[],allowed_origin=[]))

    def test_host_and_origin_attacks_are_rejected(self):
        deployment=self.hosted()
        valid=Headers({'Host':'example.hf.space','Origin':'https://example.hf.space','Sec-Fetch-Site':'same-origin'})
        self.assertTrue(deployment.trusts(valid,'POST'))
        for headers in (
            Headers(valid,Host='evil.example'),
            Headers(valid,Host='example.hf.space.evil.example'),
            Headers(valid,Origin='https://evil.example'),
            Headers(valid,Origin='null'),
            Headers(valid,**{'Sec-Fetch-Site':'cross-site'}),
        ):
            self.assertFalse(deployment.trusts(headers,'POST'))
        self.assertFalse(deployment.trusts(Headers({'Host':'example.hf.space','Sec-Fetch-Site':'none'}),'POST'))
        self.assertFalse(deployment.trusts(Headers({'Host':'example.hf.space','Origin':'https://example.hf.space'}),'GET'))

    def test_forwarded_headers_never_override_direct_authority(self):
        deployment=self.hosted()
        hostile=Headers({'Host':'evil.example','Origin':'https://evil.example','Sec-Fetch-Site':'cross-site',
            'X-Forwarded-Host':'example.hf.space','X-Forwarded-Proto':'https','X-Forwarded-Origin':'https://example.hf.space','Forwarded':'host=example.hf.space;proto=https'})
        self.assertFalse(deployment.trusts(hostile,'POST'))
        direct=Headers({'Host':'example.hf.space','Origin':'https://example.hf.space','Sec-Fetch-Site':'same-origin',
            'X-Forwarded-Host':'evil.example','X-Forwarded-Proto':'http','X-Forwarded-Origin':'https://evil.example','Forwarded':'host=evil.example;proto=http'})
        self.assertTrue(deployment.trusts(direct,'POST'))

    def test_hosted_sessions_isolate_jobs_views_and_report_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True)
            first=app.session(now=10)
            second=app.session(now=10)
            first.jobs['job-a']={'status':'complete'}
            first.venue_views['view-a']={'private':'state'}
            self.assertNotEqual(first.identifier,second.identifier)
            self.assertNotIn('job-a',second.jobs)
            self.assertNotIn('view-a',second.venue_views)
            self.assertEqual(app.session(first.identifier,now=11).identifier,first.identifier)
            self.assertEqual(app.target('I1',2000,2001,first.directory).parent,first.directory)

    def test_expired_hosted_session_files_are_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True,session_ttl=10)
            expired=app.session(now=10)
            marker=expired.directory/'report.json'
            marker.write_text('{}')
            app.session(now=21)
            self.assertFalse(marker.exists())
            self.assertNotIn(expired.identifier,app.sessions)

    def test_loading_session_is_not_expired_mid_job(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True,session_ttl=10)
            active=app.session(now=10)
            active.jobs['job-a']={'status':'loading'}
            app.session(now=21)
            self.assertIn(active.identifier,app.sessions)

    def test_hosted_session_count_has_a_hard_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True,max_sessions=1)
            first=app.session(now=0)
            self.assertEqual(app.session(first.identifier,now=1).identifier,first.identifier)
            with self.assertRaises(BusyError): app.session(now=1)

    def test_hosted_rate_budget_is_per_session_and_uses_a_sliding_minute(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True,session_rate=2)
            first=app.session(now=0)
            second=app.session(now=0)
            app.consume(first,now=1)
            app.consume(first,now=2)
            with self.assertRaises(RateLimitError): app.consume(first,now=3)
            app.consume(second,now=3)
            app.consume(first,now=61)

    def test_live_operations_fail_fast_when_concurrency_is_exhausted(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True,network_concurrency=1)
            session=app.session(now=0)
            app.network_slots.acquire()
            try:
                with self.assertRaises(BusyError): app.live(session,lambda: None)
            finally: app.network_slots.release()

    def test_report_queue_has_a_hard_capacity(self):
        started=threading.Event()
        release=threading.Event()
        work=WorkQueue(1,1)
        def blocking():
            started.set()
            release.wait(2)
        self.assertTrue(work.submit(blocking))
        self.assertTrue(started.wait(1))
        self.assertTrue(work.submit(Mock()))
        self.assertFalse(work.submit(Mock()))
        release.set()
        work.close()

    def test_report_start_budget_is_cumulative_per_hosted_session(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True,session_reports=1)
            session=app.session(now=0)
            session.reports_started=1
            with self.assertRaises(ResourceLimitError): app.start('I1',2000,2001,session=session)

    def test_export_count_and_byte_budgets_are_cumulative(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True,session_exports=1,max_export_bytes=8,session_export_bytes=10)
            session=app.session(now=0)
            app.consume_export(session)
            app.account_export(session,8)
            self.assertEqual(session.exported_bytes,8)
            with self.assertRaises(ResourceLimitError): app.consume_export(session)
            with self.assertRaises(ResourceLimitError): app.account_export(session,9)
            with self.assertRaises(ResourceLimitError): app.account_export(session,3)

    def test_deadline_api_stops_between_cached_api_calls(self):
        delegate=Mock(key=None,requests=[])
        delegate.get.return_value={'results':[]}
        clock=Mock(side_effect=(9,11))
        api=DeadlineAPI(delegate,10,clock=clock)
        with self.assertRaises(ResourceLimitError): api.get('works')
        delegate.get.assert_called_once_with('works',None)

    def test_report_api_enforces_query_and_reported_cost_budgets(self):
        delegate=Mock(key=None,requests=[])
        def get(path,params=None):
            delegate.requests.append({'reported_cost_usd':0.06})
            return {'results':[]}
        delegate.get.side_effect=get
        api=DeadlineAPI(delegate,100,max_queries=1,max_cost_usd=1,clock=lambda:0)
        api.get('works')
        with self.assertRaises(ResourceLimitError): api.get('works')
        costly=DeadlineAPI(delegate,100,max_queries=10,max_cost_usd=.05,clock=lambda:0)
        with self.assertRaises(ResourceLimitError): costly.get('works')

    def test_session_key_is_memory_only_redacted_from_status_and_cache(self):
        sentinel='sentinel-openalex-secret-12345'
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True)
            session=app.session(now=0)
            app.set_session_key(session,sentinel)
            self.assertEqual(app.auth_status(session),{'has_key':True,'key_source':'session'})
            self.assertNotIn(sentinel,str(app.auth_status(session)))
            api=app.api(session)
            self.assertEqual(api.key,sentinel)
            with patch('pharos.backends.openalex_api.OpenAlex.get',return_value={'meta':{},'results':[]}):
                api.get('works',{'per_page':1})
            self.assertEqual(api.directory.parent,session.directory)
            self.assertFalse((app.directory/'responses').exists())
            for path in app.directory.rglob('*'):
                if path.is_file(): self.assertNotIn(sentinel,path.read_text())
            app.forget_session_key(session)
            self.assertIsNone(session.key)
            self.assertIsNone(api.key)
            self.assertEqual(app.api(session).directory,app.directory/'responses')
            self.assertEqual(app.auth_status(session),{'has_key':False,'key_source':'none'})

    def test_session_key_validation_rejects_log_and_header_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory,hosted=True)
            session=app.session(now=0)
            for key in ('short','valid-looking-key\nInjected: yes','non-ascii-£-credential'):
                with self.assertRaises(ValueError): app.set_session_key(session,key)

    def test_forget_key_removes_authorization_from_next_transport_request(self):
        credential={'value':'sentinel-openalex-secret-12345'}
        api=OpenAlex(key_provider=lambda:credential['value'])
        responses=[]
        for _ in range(2):
            response=MagicMock()
            response.__enter__.return_value=response
            response.read.return_value=b'{"meta":{},"results":[]}'
            responses.append(response)
        api.opener.open=Mock(side_effect=responses)
        api.get('works',{'page':1})
        credential['value']=None
        api.get('works',{'page':2})
        first=api.opener.open.call_args_list[0].args[0]
        second=api.opener.open.call_args_list[1].args[0]
        self.assertEqual(first.get_header('Authorization'),'Bearer sentinel-openalex-secret-12345')
        self.assertIsNone(second.get_header('Authorization'))


if __name__ == '__main__': unittest.main()
