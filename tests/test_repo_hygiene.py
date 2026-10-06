"""Gate: the repository may become public, so no tracked file may carry secrets or private data."""
import base64
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = {
    'supabase secret key': re.compile(r'sb_secret_[A-Za-z0-9_-]{8,}'),
    'private key block': re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    'github token': re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}'),
    'openai/anthropic key': re.compile(r'\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}'),
    'aws key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    'postgres url with password': re.compile(r'postgres(?:ql)?://[^:\s/]+:[^@\s]{3,}@'),
}
JWT = re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.(eyJ[A-Za-z0-9_-]{8,})\.[A-Za-z0-9_-]{8,}')
FORBIDDEN_SUFFIXES = ('.sqlite', '.sqlite3', '.db', '.env', '.pem', '.key', '.jpg', '.jpeg', '.heic', '.png')


def tracked_files():
    out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout
    return [ROOT / p for p in out.decode().split('\0') if p]


def jwt_role(segment):
    padded = segment + '=' * (-len(segment) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded)).get('role')
    except ValueError:
        return 'undecodable'


def scan_text(text):
    """Return names of secret kinds found; a legacy anon JWT is public by design and allowed."""
    hits = [name for name, rx in SECRET_PATTERNS.items() if rx.search(text)]
    hits += ['jwt role=%s' % jwt_role(m.group(1)) for m in JWT.finditer(text) if jwt_role(m.group(1)) != 'anon']
    return hits


class RepoHygieneTests(unittest.TestCase):
    def test_scanner_detects_known_secret_shapes(self):
        service = 'eyJhbGciOiJIUzI1NiJ9.' + base64.urlsafe_b64encode(b'{"role":"service_role"}').decode().rstrip('=') + '.abcdefghijk'
        anon = 'eyJhbGciOiJIUzI1NiJ9.' + base64.urlsafe_b64encode(b'{"role":"anon"}').decode().rstrip('=') + '.abcdefghijk'
        self.assertTrue(scan_text(service))
        self.assertEqual(scan_text(anon), [])
        self.assertTrue(scan_text('key = "sb_secret_' + 'abcdefghij123"'))
        self.assertEqual(scan_text('publishable: sb_publishable_abcdefghij'), [])

    def test_no_secrets_or_private_files_tracked(self):
        problems = []
        for path in tracked_files():
            rel = path.relative_to(ROOT).as_posix()
            if rel.lower().endswith(FORBIDDEN_SUFFIXES) or '/private/' in '/' + rel:
                problems.append((rel, 'forbidden file type/location'))
                continue
            if rel == 'tests/test_repo_hygiene.py':
                continue
            text = path.read_text(encoding='utf-8', errors='ignore')
            problems += [(rel, hit) for hit in scan_text(text)]
        self.assertEqual(problems, [])


if __name__ == '__main__':
    unittest.main()
