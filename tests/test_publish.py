"""Publisher against a local fake of Supabase Auth + PostgREST (real hosted project not available)."""
import http.server
import json
import subprocess
import sys
import threading

from cli_case import CliCase, ROOT

OWNER = '11111111-1111-4111-8111-111111111111'


class FakeSupabase(http.server.BaseHTTPRequestHandler):
    state = None

    def log_message(self, *args):
        pass

    def send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('content-type', 'application/json')
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        return json.loads(self.rfile.read(int(self.headers['content-length'])))

    def user(self):
        s = self.state
        token = (self.headers.get('authorization') or '')[7:]
        return OWNER if token and token == s['access'] else None

    def do_POST(self):
        s = self.state
        s['log'].append(('POST', self.path, self.headers.get('apikey')))
        if self.path.startswith('/auth/v1/token?grant_type=password'):
            b = self.body()
            if (b['email'], b['password']) != ('me@example.org', 'correct horse'):
                return self.send(400, {'error': 'invalid_grant'})
        elif self.path.startswith('/auth/v1/token?grant_type=refresh_token'):
            if self.body()['refresh_token'] != s['refresh']:
                return self.send(400, {'error': 'invalid_grant'})
        elif self.path == '/rest/v1/rpc/publish_journal':
            if not self.user():
                return self.send(401, {})
            if not s['writer']:
                return self.send(403, {'code': '42501', 'message': 'Writer not authorized'})
            b = self.body()
            if b['p_expected_revision'] != s['revision']:
                return self.send(400, {'code': '40001', 'message': 'Projection changed; fetch before retry'})
            s['revision'] += 1
            s['dataset'] = b['p_dataset']
            return self.send(200, s['revision'])
        else:
            return self.send(404, {})
        s['n'] += 1
        s['access'], s['refresh'] = 'acc%d' % s['n'], 'ref%d' % s['n']
        return self.send(200, {'access_token': s['access'], 'refresh_token': s['refresh'], 'expires_in': 3600,
                               'user': {'id': OWNER}})

    def do_GET(self):
        s = self.state
        s['log'].append(('GET', self.path, self.headers.get('apikey')))
        if not self.user():
            return self.send(401, {})
        if s['dataset'] is None:
            return self.send(200, [])
        row = {'revision': s['revision']}
        if 'dataset' in self.path:
            row['dataset'] = s['tamper'] or s['dataset']
        return self.send(200, [row])


class PublishTests(CliCase):
    def setUp(self):
        super().setUp()
        FakeSupabase.state = self.state = {'n': 0, 'access': None, 'refresh': None, 'revision': 0, 'dataset': None,
                                           'writer': True, 'tamper': None, 'log': []}
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), FakeSupabase)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.session = self.root / 'private' / 'supabase-session.json'
        self.env.update(COFFEE_SUPABASE_URL='http://127.0.0.1:%d' % self.server.server_port,
                        COFFEE_SUPABASE_KEY='sb_publishable_test')

    def login(self, password='correct horse', ok=True):
        result = subprocess.run([sys.executable, '-m', 'coffee_journal', 'publish-login', '--email', 'me@example.org'],
                                cwd=ROOT, env=self.env, input=password + '\n', text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        self.assertNotIn(password, result.stdout + result.stderr)
        self.assertNotIn('acc', result.stdout)
        return json.loads(result.stdout)

    def test_login_stores_only_refresh_token_privately(self):
        self.assertEqual(self.login(), {'ok': True, 'user_id': OWNER})
        self.assertEqual(json.loads(self.session.read_text()), {'refresh_token': 'ref1'})
        self.assertEqual(self.session.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('correct horse', self.session.read_text())

    def test_bad_password_and_missing_config(self):
        self.assertEqual(self.login('wrong', ok=False)['category'], 'auth')
        self.assertFalse(self.session.exists())
        for env in ({'COFFEE_SUPABASE_URL': 'https://evil.example'}, {'COFFEE_SUPABASE_KEY': 'sb_secret_x'}):
            with self.subTest(env=env):
                saved = dict(self.env); self.env.update(env)
                self.assertEqual(self.cli('publish', ok=False)['category'], 'config')
                self.env = saved

    def test_publish_exports_without_private_fields_rotates_and_verifies(self):
        self.login()
        coffee = self.add('coffee', {'name': 'Fictional', 'source_text': 'secret OCR'}, 'c')['id']
        batch = self.add('batch', {'coffee_id': coffee}, 'b')['id']
        self.add('brew', {'batch_id': batch, 'rating': 80, 'source_refs': ['photo.jpg']}, 'x')
        self.assertEqual(self.cli('publish'), {'ok': True, 'revision': 1, 'brews': 1})
        published = json.dumps(self.state['dataset'])
        self.assertNotIn('secret OCR', published)
        self.assertNotIn('photo.jpg', published)
        self.assertEqual(json.loads(self.session.read_text())['refresh_token'], 'ref2')  # rotated
        self.assertEqual(self.cli('publish')['revision'], 2)
        self.assertTrue(all(key == 'sb_publishable_test' for _, _, key in self.state['log']))

    def test_conflict_writer_denial_and_tamper_detected(self):
        self.login()
        self.state['writer'] = False
        self.assertEqual(self.cli('publish', ok=False)['category'], 'auth')
        self.state['writer'] = True
        self.state.update(dataset={'schema_version': 1}, revision=5, tamper=None)
        original_get = FakeSupabase.do_GET

        def stale_get(handler):  # another writer publishes right after our revision read
            response = original_get(handler)
            handler.state['revision'] += 1
            return response
        FakeSupabase.do_GET = stale_get
        try:
            self.assertEqual(self.cli('publish', ok=False)['category'], 'conflict')
        finally:
            FakeSupabase.do_GET = original_get
        self.assertEqual(self.state['dataset'], {'schema_version': 1})  # nothing overwritten
        self.state['tamper'] = {'schema_version': 1, 'coffees': [{'id': 'x'}]}
        self.assertEqual(self.cli('publish', ok=False)['category'], 'verify')

    def test_world_readable_session_refused(self):
        self.login()
        self.session.chmod(0o644)
        self.assertEqual(self.cli('publish', ok=False)['category'], 'config')
