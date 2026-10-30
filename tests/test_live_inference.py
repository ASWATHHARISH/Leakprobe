"""Restricted inference regressions: actual tool loop, synthetic fixtures, no network."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
import json
import os
from pathlib import Path
import runpy
import socket
import tempfile
import time
from types import SimpleNamespace as S
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest
from leakprobe.investigation_evidence import InvestigationEvidence
from leakprobe.net3_tools import Net3Investigation
from leakprobe.paths import ROOT
from leakprobe.ui import ai_service, live_policy, live_access
from leakprobe.ui.alert_store import AlertStore
from leakprobe.ui.investigation_history import is_validated_report, select_investigations
from leakprobe.ui.operations import build_alert
from leakprobe.ui.protected_client import ProtectedClient, provider

admin = runpy.run_path(str(ROOT / 'deploy/live_admin.py'))
PASSWORD = 'disposable-test-access-code'
SIGNING_KEY = '12' * 32
CHANNELS = ['pressure_243_m', 'flow_229_lps']
ACCESS_HASH = live_policy.password_hash(PASSWORD, '34' * 16)


class Clock:
    def __init__(self):
        self.now = time.time()
    def __call__(self):
        return self.now


def settings(clock):
    return {'LEAKPROBE_LIVE_MODE': 'restricted', 'LEAKPROBE_LIVE_UNTIL_UTC':
            datetime.fromtimestamp(clock() + 3600, timezone.utc).isoformat(),
            'NEBIUS_API_KEY': 'not-a-real-key', 'LEAKPROBE_OPERATOR_PASSWORD_HASH': ACCESS_HASH,
            'LEAKPROBE_LIVE_ADMIN_KEY': SIGNING_KEY, 'LEAKPROBE_INPUT_USD_PER_MILLION': '2',
            'LEAKPROBE_OUTPUT_USD_PER_MILLION': '4', 'LEAKPROBE_LIVE_BUDGET_USD': '1.00',
            # Broader mocked campaigns exercise the independent budget/case limits.
            # Deployment defaults and the first activation template permit one attempt.
            'LEAKPROBE_LIVE_MAX_INVESTIGATIONS': '4'}


def report_for(session):
    evidence = InvestigationEvidence(session)
    evidence.get_observations()
    ranking = evidence.compare_hypotheses()['ranking']
    sensors = evidence.get_sensor_summary(CHANNELS)['sensors']
    def candidate(row):
        return {'pipe': row['pipe'], 'rank': row['rank'], 'fit_score': row['fit']['value'], 'fact_id': row['fit']['fact_id']}
    return {'summary': 'Review the leading candidate and verify the sensor evidence before deciding on field action.',
        'evidence': [{key: row['facts'][2][key] for key in ('fact_id', 'value', 'unit', 'channel', 'sign')} for row in sensors],
        'leading_candidate': candidate(ranking[0]),
        'alternatives': [candidate(row) for row in ranking[1:] if row['pipe'] is None or row['rank'] == 2],
        'possible_explanations': ['demand_change', 'sensor_error'],
        'uncertainty': ['fit_not_probability', 'not_field_verified', 'model_mismatch'],
        'actions': ['check_sensor_health', 'review_operating_changes', 'verify_candidate_in_field']}


def call(name, arguments):
    return S(id=name, function=S(name=name, arguments=json.dumps(arguments)))


class Fake:
    def __init__(self, report, bad=False, failure=False, no_usage=False):
        self.requests, self.report = [], report
        self.bad, self.failure, self.no_usage = bad, failure, no_usage
        self.chat = S(completions=S(create=self.create))
    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        if self.failure:
            raise RuntimeError('Sensitive provider exception: not-a-real-key')
        name = 'get_sensor_summary' if len(self.requests) == 1 else 'submit_employee_report'
        arguments = {'channels': CHANNELS} if len(self.requests) == 1 else copy.deepcopy(self.report)
        if self.bad and name == 'submit_employee_report':
            arguments['evidence'][1]['sign'] = 'negative'
        return S(id='mock-response', model_extra={'cost': .001, 'currency': 'USD'},
            choices=[S(finish_reason='tool_calls', message=S(content=None, tool_calls=[call(name, arguments)]))],
            usage=None if self.no_usage else {'prompt_tokens': 128, 'completion_tokens': 32, 'total_tokens': 160})


class NoNetwork(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(socket.socket, 'connect', side_effect=AssertionError('No real providers permitted'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.clock = Clock()
        self.values = settings(self.clock)
        self.control = live_policy.Authority(live_policy.Policy.from_settings(self.values), self.clock)
    def authorize(self, session='browser-one'):
        token = self.control.authenticate(PASSWORD, session)
        self.control.arm(admin['sign_challenge'](self.control.challenge(), SIGNING_KEY), token, session)
        return token, session


class PolicyTests(NoNetwork):
    def test_first_activation_defaults_to_one_attempt_across_all_sessions(self):
        self.values.pop('LEAKPROBE_LIVE_MAX_INVESTIGATIONS')
        policy = live_policy.Policy.from_settings(self.values)
        self.assertEqual(policy.public()['max_runs'], 1)
        self.control = live_policy.Authority(policy, self.clock)
        token, session = self.authorize()
        lease = self.control.begin(token, session, 'LP-0405')
        self.control.end(lease)  # Failed attempts consume the allowance too.
        other = self.control.authenticate(PASSWORD, 'another-browser')
        for candidate, browser in ((token, session), (other, 'another-browser')):
            with self.assertRaises(live_policy.LiveDenied):
                self.control.begin(candidate, browser, 'another-alert')
        self.assertEqual(len(self.control.runs), 1)
        self.assertLessEqual(self.control.spent, Decimal('.25'))
        changed = live_policy.Policy.from_settings({**self.values, 'LEAKPROBE_LIVE_MAX_INVESTIGATIONS': '2'})
        self.assertNotEqual(policy.fingerprint, changed.fingerprint)

    def test_offline_bootstrap_overrides_accidental_live_profile(self):
        with patch.dict(os.environ, {'LEAKPROBE_DEPLOYMENT_PROFILE': 'restricted_live', 'LEAKPROBE_ENABLE_LIVE_AI': '1'}):
            runpy.run_path(str(ROOT / 'deploy/app.py'))['configure_demo']()
            factory = Mock()
            self.assertEqual(ai_service.run_investigation({}, Mock(), client_factory=factory)['status'], 'unavailable')
            factory.assert_not_called()
            self.assertEqual(os.environ['LEAKPROBE_DEPLOYMENT_PROFILE'], 'offline')
    def test_no_client_injection_or_forged_session_bypass(self):
        token, session = self.authorize()
        for candidate, browser in ((None, session), ('forged', session), (token, 'other-browser')):
            with patch.object(ai_service, 'authority', return_value=self.control):
                factory, store = Mock(), Mock()
                self.assertEqual(ai_service.run_investigation({}, store, client_factory=factory,
                    authorization=candidate, browser_session=browser)['request_count'], 0)
                factory.assert_not_called()
                store.reserve_ai.assert_not_called()
    def test_expiry_logout_and_global_login_rate_limit(self):
        token, session = self.authorize()
        self.clock.now += 901
        self.assertFalse(self.control.authorized(token, session))
        self.control.logout(token)
        for _ in range(6):
            with self.assertRaises(live_policy.LiveDenied):
                self.control.authenticate('wrong-code-long-enough', 'new-browser')
        with self.assertRaises(live_policy.LiveDenied):
            self.control.authenticate(PASSWORD, 'another-browser')
    def test_unarmed_reused_and_restart_permits_fail_closed(self):
        token = self.control.authenticate(PASSWORD, 'one')
        with self.assertRaises(live_policy.LiveDenied):
            self.control.begin(token, 'one', 'alert')
        permit = admin['sign_challenge'](self.control.challenge(), SIGNING_KEY)
        self.control.arm(permit, token, 'one')
        with self.assertRaises(live_policy.LiveDenied):
            self.control.arm(permit, token, 'one')
        restarted = live_policy.Authority(self.control.policy, self.clock)
        other = restarted.authenticate(PASSWORD, 'one')
        with self.assertRaises(live_policy.LiveDenied):
            restarted.arm(permit, other, 'one')
        self.assertEqual(restarted.spent, 0)
    def test_tampered_permit_and_wrong_signing_key_rejected(self):
        token = self.control.authenticate(PASSWORD, 'one')
        permit = admin['sign_challenge'](self.control.challenge(), '56' * 32)
        with self.assertRaises(live_policy.LiveDenied):
            self.control.arm(permit, token, 'one')
        permit = admin['sign_challenge'](self.control.challenge(), SIGNING_KEY)
        permit['limits']['budget_usd'] = '999'
        with self.assertRaises(live_policy.LiveDenied):
            self.control.arm(permit, token, 'one')
    def test_concurrent_requests_are_atomic_and_failed_reservation_not_refunded(self):
        token, session = self.authorize()
        def begin(number):
            try:
                return self.control.begin(token, session, str(number))
            except live_policy.LiveDenied:
                return None
        with ThreadPoolExecutor(2) as pool:
            attempts = list(pool.map(begin, (1, 2)))
        self.assertEqual(sum(row is not None for row in attempts), 1)
        lease = next(row for row in attempts if row)
        self.control.end(lease)
        self.assertEqual(self.control.spent, Decimal('.23296'))
    def test_spending_cap_global_case_and_session_limits(self):
        self.values['LEAKPROBE_LIVE_BUDGET_USD'] = '.50'
        self.control = live_policy.Authority(live_policy.Policy.from_settings(self.values), self.clock)
        token, session = self.authorize()
        for i in range(2):
            lease = self.control.begin(token, session, 'alert')
            self.control.end(lease)
            self.clock.now += 61
        for browser in (session, 'other'):
            other = self.control.authenticate(PASSWORD, browser)
            with self.assertRaises(live_policy.LiveDenied):
                self.control.begin(other, browser, 'another-alert')
        self.assertLessEqual(self.control.spent, Decimal('.50'))
    def test_case_limit_shared_across_browser_sessions(self):
        token, session = self.authorize()
        for i in range(2):
            other = self.control.authenticate(PASSWORD, str(i))
            lease = self.control.begin(other, str(i), 'same-alert')
            self.control.end(lease)
            self.clock.now += 61
        with self.assertRaises(live_policy.LiveDenied):
            self.control.begin(token, session, 'same-alert')
    def test_unsafe_incomplete_or_overbudget_configuration_is_denied(self):
        for key, value in (('NEBIUS_BASE_URL', 'https://untrusted.invalid/v1/'), ('NEBIUS_MODEL', 'other'),
            ('NEBIUS_API_KEY', ''), ('LEAKPROBE_LIVE_ADMIN_KEY', 'bad'),
            ('LEAKPROBE_INPUT_USD_PER_MILLION', 'NaN'), ('LEAKPROBE_OUTPUT_USD_PER_MILLION', '10000'),
            ('LEAKPROBE_LIVE_BUDGET_USD', '2'), ('LEAKPROBE_LIVE_UNTIL_UTC', '2000-01-01T00:00:00Z'),
            ('LEAKPROBE_LIVE_MAX_INVESTIGATIONS', '0'), ('LEAKPROBE_LIVE_MAX_INVESTIGATIONS', '5'),
            ('LEAKPROBE_LIVE_MAX_INVESTIGATIONS', '1.5')):
            with self.subTest(key=key), self.assertRaises(live_policy.LiveDenied):
                live_policy.Policy.from_settings({**self.values, key: value})
    def test_secret_loader_uses_only_cloud_or_environment_and_never_dotenv(self):
        with patch.dict(os.environ, {'LEAKPROBE_DEPLOYMENT_PROFILE': 'restricted_live', 'NEBIUS_API_KEY': 'server-value'}, clear=True), \
             patch('streamlit.secrets', {'NEBIUS_API_KEY': 'cloud-value', 'LEAKPROBE_LIVE_MODE': 'restricted'}):
            self.assertEqual(live_policy.server_settings()['NEBIUS_API_KEY'], 'server-value')


class WorkflowTests(NoNetwork):
    @classmethod
    def setUpClass(cls):
        cls.session = Net3Investigation('case_005')
        cls.report = report_for(cls.session)
        cls.alert = build_alert({'case_id': cls.session.case_id, 'observations': cls.session.observations,
                                'comparison': cls.session.compare_hypotheses()})
    def run_case(self, client, folder, token=None, session=None):
        store = AlertStore(Path(folder) / 'review.sqlite3')
        store.register(self.alert)
        with patch.object(ai_service, 'authority', return_value=self.control):
            return ai_service.run_investigation(self.alert, store, client_factory=lambda: client,
                output=Path(folder) / 'traces', authorization=token, browser_session=session)
    def test_complete_mocked_workflow_keeps_evidence_scores_and_trace(self):
        token, session = self.authorize()
        client = Fake(self.report)
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_case(client, folder, token, session)
            self.assertTrue(is_validated_report(result), result.get('error'))
            self.assertEqual(result['origin'], 'live_nebius')
            self.assertEqual(result['request_count'], 2)
            self.assertEqual(result['usage_summary']['total_tokens'], 320)
            self.assertEqual(result['usage_summary']['provider_cost_info'][0]['provider_fields']['cost'], .001)
            self.assertEqual(result['live_budget']['reservation_usd'], '0.23296')
            self.assertEqual(len(self.session.observations.columns), 210)  # timestamp plus all 209 channels
            self.assertTrue((self.session.observations.flow_229_lps.dropna() > 0).all())
            self.assertEqual(result['report']['evidence'][1]['sign'], 'positive')
            self.assertEqual(result['report']['leading_candidate']['pipe'], '243')
            self.assertEqual(len(list((Path(folder) / 'traces').glob('*.json'))), 1)
            self.assertIsNone(self.control.active)
            self.assertNotIn('not-a-real-key', json.dumps(result))
            self.assertTrue(all(0 < row['timeout'] <= 20 for row in client.requests))
    def test_lp0405_initial_single_attempt_workflow_with_mocked_provider(self):
        self.values['LEAKPROBE_LIVE_MAX_INVESTIGATIONS'] = '1'
        self.control = live_policy.Authority(live_policy.Policy.from_settings(self.values), self.clock)
        actual = Net3Investigation('case_405')
        self.alert = build_alert({'case_id': actual.case_id, 'observations': actual.observations,
                                  'comparison': actual.compare_hypotheses()})
        report = report_for(actual)
        token, browser = self.authorize()
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_case(Fake(report), folder, token, browser)
            self.assertTrue(is_validated_report(result), result.get('error'))
            self.assertEqual(result['case_id'], 'case_405')
            self.assertEqual(result['request_count'], 2)
            self.assertEqual(result['report']['leading_candidate'], report['leading_candidate'])
            self.assertLessEqual(Decimal(result['live_budget']['reservation_usd']), Decimal('.25'))
            blocked_client = Fake(report)
            blocked = self.run_case(blocked_client, folder, token, browser)
            self.assertEqual(blocked['status'], 'unavailable')
            self.assertEqual(blocked['request_count'], 0)
            self.assertEqual(blocked_client.requests, [])
            self.assertEqual(len(list((Path(folder) / 'traces').glob('*.json'))), 1)
    def test_incorrect_direction_remains_invalid_and_saved_separately(self):
        token, session = self.authorize()
        with tempfile.TemporaryDirectory() as folder:
            good = self.run_case(Fake(self.report), folder, token, session)
            bad = self.run_case(Fake(self.report, bad=True), folder, token, session)
            self.assertEqual(bad['status'], 'invalid_report')
            self.assertFalse(is_validated_report(bad))
            self.assertEqual(len(list((Path(folder) / 'traces').glob('*.json'))), 2)
            selected = select_investigations([good, bad], self.alert, self.session.observations)
            self.assertIs(selected['validated'], good)
    def test_provider_timeout_redacts_error_retains_reservation_and_releases_slot(self):
        token, session = self.authorize()
        client = Fake(self.report, failure=True)
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_case(client, folder, token, session)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['request_count'], 1)
        self.assertEqual(len(client.requests), 1)
        self.assertNotIn('Sensitive provider exception', json.dumps(result))
        self.assertIsNone(self.control.active)
        self.assertEqual(self.control.spent, self.control.policy.reserve_usd)
    def test_unreported_usage_stops_further_calls_without_refund(self):
        token, session = self.authorize()
        client = Fake(self.report, no_usage=True)
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_case(client, folder, token, session)
        self.assertEqual(len(client.requests), 1)
        self.assertNotEqual(result['status'], 'completed')
        self.assertIn('did not report usage', result['error'])
        self.assertEqual(self.control.spent, self.control.policy.reserve_usd)
    def test_storage_failure_never_claims_saved_completion(self):
        token, session = self.authorize()
        with tempfile.TemporaryDirectory() as folder, patch.object(ai_service, 'save_trace', side_effect=OSError('disk')):
            result = self.run_case(Fake(self.report), folder, token, session)
        self.assertEqual(result['status'], 'storage_failed')
        self.assertNotIn('trace_file', result)
    def test_budget_proxy_checks_deadline_size_and_request_count_before_sending(self):
        token, session = self.authorize()
        raw = Mock()
        payload = dict(model=live_policy.MODEL, messages=[], tools=[], tool_choice='auto', max_tokens=2048)
        lease = self.control.begin(token, session, 'alert')
        proxy = ProtectedClient(self.control, lease, raw)
        for kind in ('deadline', 'size', 'count', 'token_allowance'):
            lease.update(deadline=self.clock() + 90, stop=None, requests=0, tokens=0)
            changed = copy.deepcopy(payload)
            if kind == 'deadline':
                lease['deadline'] = self.clock()
            elif kind == 'size':
                changed['messages'] = ['x' * 24001]
            elif kind == 'count':
                lease['requests'] = 4
            else:
                lease['tokens'] = live_policy.MAX_TOKEN_ALLOWANCE
            with self.subTest(kind=kind), self.assertRaises(live_policy.LiveDenied):
                proxy.create(**changed)
        raw.chat.completions.create.assert_not_called()
    def test_usage_overrun_latches_all_live_requests_closed(self):
        token, session = self.authorize()
        raw = S(chat=S(completions=S(create=lambda **kw: S(usage={'prompt_tokens': 1000000,
            'completion_tokens': 1, 'total_tokens': 1000001}))))
        lease = self.control.begin(token, session, 'alert')
        ProtectedClient(self.control, lease, raw).create(model=live_policy.MODEL, messages=[], tools=[], tool_choice='auto', max_tokens=2048)
        self.assertTrue(self.control.poisoned)
        self.control.end(lease)
        with self.assertRaises(live_policy.LiveDenied):
            self.control.begin(token, session, 'another')
    def test_disabling_mode_or_inspection_guard_stops_the_next_request(self):
        switch = {'enabled': True}
        self.control = live_policy.Authority(self.control.policy, self.clock, enabled=lambda: switch['enabled'])
        token, session = self.authorize()
        raw = Mock()
        raw.chat.completions.create.return_value = S(usage={'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12})
        lease = self.control.begin(token, session, 'alert')
        client = ProtectedClient(self.control, lease, raw)
        payload = dict(model=live_policy.MODEL, messages=[], tools=[], tool_choice='auto', max_tokens=2048)
        client.create(**payload)
        switch['enabled'] = False
        with self.assertRaises(live_policy.LiveDenied):
            client.create(**payload)
        self.assertEqual(raw.chat.completions.create.call_count, 1)
        with patch.object(live_policy, 'server_settings', return_value=self.values), \
             patch.dict(os.environ, {'LEAKPROBE_INSPECTION_MODE': '1'}):
            self.assertFalse(live_policy.current_policy_matches(self.control.policy))
    def test_actual_sdk_adapter_is_mocked_no_network_and_no_redirect_following(self):
        import httpx
        import openai
        token, session = self.authorize()
        lease = self.control.begin(token, session, 'alert')
        seen = []
        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200, json={'id': 'mock', 'object': 'chat.completion', 'created': 1,
                'model': live_policy.MODEL, 'choices': [{'index': 0, 'finish_reason': 'stop',
                    'message': {'role': 'assistant', 'content': 'draft'}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12}})
        options = {}
        class OfflineHTTP(httpx.Client):
            def __init__(self, **kwargs):
                options.update(kwargs)
                super().__init__(transport=httpx.MockTransport(handler), **kwargs)
        with patch('httpx.Client', OfflineHTTP):
            client = provider(self.control, lease)
        self.assertEqual(client.max_retries, 0)
        self.assertFalse(options['follow_redirects'])
        self.assertFalse(options['trust_env'])
        wrapped = ProtectedClient(self.control, lease, client)
        wrapped.create(model=live_policy.MODEL, messages=[{'role': 'user', 'content': 'mock only'}],
                       tools=[], tool_choice='auto', max_tokens=2048)
        wrapped.close()
        self.assertEqual(len(seen), 1)


class InterfaceTests(NoNetwork):
    def test_restricted_entrypoint_navigation_login_and_arm_make_no_requests(self):
        from leakprobe.ui import data_access
        with tempfile.TemporaryDirectory() as folder, patch.object(live_policy, 'server_settings', return_value=self.values), \
             patch.object(live_policy, '_authority', self.control), \
             patch.object(ai_service, 'provider_client', side_effect=AssertionError('No inference on navigation')) as factory, \
             patch('tempfile.tempdir', folder), patch.object(data_access, 'OUTPUTS', Path(folder)):
            app = AppTest.from_file(str(ROOT / 'deploy/live/app.py')).run(timeout=120)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.selectbox(key='monitoring_record_id').options), 500)
            self.assertTrue(next(b for b in app.button if b.label == 'Run AI Investigation').disabled)
            self.assertTrue(any('cited facts checked' in row.value for row in app.success))
            next(w for w in app.text_input if w.label == 'Operator access code').set_value(PASSWORD)
            next(b for b in app.button if b.label == 'Sign in for live investigations').click().run(timeout=120)
            self.assertFalse(app.exception)
            token, session = app.session_state[live_access.TOKEN], app.session_state[live_access.SESSION]
            permit = admin['sign_challenge'](self.control.challenge(), SIGNING_KEY)
            next(w for w in app.text_area if w.label == 'Signed activation permit').set_value(json.dumps(permit))
            next(b for b in app.button if b.label == 'Apply spending authorization').click().run(timeout=120)
            self.assertFalse(app.exception)
            self.assertFalse(next(b for b in app.button if b.label == 'Run AI Investigation').disabled)
            app.selectbox(key='monitoring_record_id').set_value('case_402').run(timeout=120)
            self.assertFalse(app.exception)
            self.assertTrue(self.control.authorized(token, session))
            factory.assert_not_called()
            app.selectbox(key='monitoring_record_id').set_value('case_005').run(timeout=120)
            model_report = report_for(Net3Investigation('case_005'))
            with patch.object(ai_service, 'OUTPUTS', Path(folder)), \
                 patch.object(ai_service, 'provider_client', return_value=Fake(model_report)) as explicit:
                next(b for b in app.button if b.label == 'Run AI Investigation').click().run(timeout=120)
                self.assertFalse(app.exception)
                self.assertTrue(any('Newly generated live' in row.value for row in app.caption))
                self.assertTrue(any('cited facts checked' in row.value for row in app.success))
                app.run(timeout=120)
                self.assertFalse(app.exception)
                self.assertTrue(any('Saved live Nemotron' in row.value for row in app.caption))
                self.assertEqual(explicit.call_count, 1)
            with patch.object(ai_service, 'OUTPUTS', Path(folder)), \
                 patch.object(ai_service, 'provider_client', return_value=Fake(model_report, failure=True)) as failed:
                next(b for b in app.button if b.label == 'Run AI Investigation').click().run(timeout=120)
                self.assertFalse(app.exception)
                self.assertTrue(any('Latest attempt: failed' in row.value for row in app.warning))
                self.assertTrue(any('cited facts checked' in row.value for row in app.success))
                app.selectbox(key='monitoring_record_id').set_value('case_405').run(timeout=120)
                self.assertFalse(app.exception)
                self.assertTrue(any('cited facts checked' in row.value for row in app.success))
                self.assertEqual(failed.call_count, 1)


if __name__ == '__main__':
    unittest.main()
