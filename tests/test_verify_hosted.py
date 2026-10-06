import http.server
import importlib.util
import json
from pathlib import Path
import threading
import unittest

spec = importlib.util.spec_from_file_location('verify_hosted', Path(__file__).resolve().parents[1] / 'tools' / 'verify_hosted.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class Fake(http.server.BaseHTTPRequestHandler):
    cfg = {}

    def log_message(self, *a):
        pass

    def reply(self, code, body):
        self.send_response(code); self.send_header('content-type', 'application/json'); self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        if self.path.startswith('/auth/v1/settings'):
            return self.reply(200, {'disable_signup': self.cfg['signup_off'], 'external': {'email': True}})
        if self.path.startswith('/rest/v1/journal_snapshots'):
            return self.reply(*self.cfg['read'])
        return self.reply(404, {'code': 'PGRST205'})

    def do_POST(self):
        self.rfile.read(int(self.headers['content-length']))
        return self.reply(*self.cfg['rpc'])


class VerifyHostedTests(unittest.TestCase):
    def check(self, **cfg):
        Fake.cfg = cfg
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        return verify.run('http://127.0.0.1:%d' % server.server_port, 'sb_publishable_x')

    def test_secure_project_passes(self):
        result = self.check(signup_off=True, read=(401, {'code': '42501'}), rpc=(401, {'code': '42501'}))
        self.assertTrue(all(result.values()), result)

    def test_insecure_or_missing_setup_fails(self):
        result = self.check(signup_off=False, read=(200, [{'owner_id': 'x'}]), rpc=(200, 1))
        for name in ('public signup disabled', 'anonymous cannot read journals', 'anonymous cannot publish'):
            self.assertFalse(result[name], name)
        missing = self.check(signup_off=True, read=(404, {'code': 'PGRST205'}), rpc=(404, {}))
        self.assertFalse(missing['table exists (migration applied)'])


if __name__ == '__main__':
    unittest.main()
