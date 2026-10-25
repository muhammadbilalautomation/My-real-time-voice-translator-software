"""Local-only API safety tests; never open a microphone or contact Google."""
import http.client
import json
import threading
import unittest
from unittest.mock import patch

from local_app import AppState, make_server


class LocalAppTests(unittest.TestCase):
    def setUp(self):
        self.state = AppState()
        self.server = make_server(self.state, port=0)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.state.stop()
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, body=None, token=True, **extra):
        headers = {'Content-Type': 'application/json', **extra}
        if token:
            headers['X-App-Token'] = self.state.token
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response.status, data

    def test_open_does_not_start_mic_and_status_has_no_key(self):
        with patch('local_app.load_key', return_value='SECRET-TEST-KEY'):
            status, data = self.call('GET', '/api/state')
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(data)['active'])
        self.assertNotIn(b'SECRET-TEST-KEY', data)
        self.assertIsNone(self.state.session)

    def test_untrusted_origin_and_missing_token_cannot_control_mic(self):
        self.assertEqual(self.call('POST', '/api/start', {}, token=False)[0], 403)
        self.assertEqual(self.call('POST', '/api/start', {}, Origin='https://evil.example')[0], 403)
        self.assertIsNone(self.state.session)

    def test_arbitrary_files_are_not_served(self):
        for path in ('/.env', '/../.env', '/gemini_client.py', '/api/unknown'):
            self.assertEqual(self.call('GET', path)[0], 404)

    def test_dns_rebinding_host_cannot_read_app_or_token(self):
        self.assertEqual(self.call('GET', '/', Host='evil.example')[0], 403)

    def test_second_launcher_cannot_bind_same_port(self):
        with self.assertRaises(OSError):
            other = make_server(AppState(), port=self.port)
            other.server_close()

    def test_refresh_cannot_disrupt_an_active_session(self):
        self.state.active = True
        with patch('local_app.sd._terminate') as terminate:
            self.assertEqual(self.call('POST', '/api/refresh', {})[0], 400)
        terminate.assert_not_called()

    def test_speaker_feedback_and_invalid_language_blocked(self):
        devices = {'inputs': [{'id': 1}], 'outputs': [{'id': 2, 'headphones': False}]}
        with patch.object(self.state, 'devices', return_value=devices):
            self.assertEqual(self.call('POST', '/api/start', {'mic': 1, 'output': 2, 'target': 'en', 'hear': True})[0], 400)
            self.assertEqual(self.call('POST', '/api/start', {'mic': 1, 'output': 2, 'target': 'fr', 'hear': False})[0], 400)

    def test_transcripts_are_bounded_and_error_survives_stop(self):
        import queue
        from types import SimpleNamespace
        session = SimpleNamespace(events=queue.Queue(), stop=lambda: None)
        self.state.session = session
        session.events.put(('original', 'a' * 40000))
        session.events.put(('error', 'HTTP 429'))
        session.events.put(('stopped', 'Stopped'))
        result = self.state.snapshot()
        self.assertLessEqual(len(result['original']), 12000)
        self.assertEqual(result['error'], 'HTTP 429')
        self.assertFalse(result['active'])


if __name__ == '__main__':
    unittest.main()
