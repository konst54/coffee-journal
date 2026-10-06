import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CliCase(unittest.TestCase):
    """Runs the real CLI against an isolated temporary database."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'private' / 'journal.sqlite3'
        self.env = dict(os.environ, COFFEE_JOURNAL_DB=str(self.db))

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, '-m', 'coffee_journal', *args],
                                cwd=ROOT, env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stderr + result.stdout)
        self.assertNotIn('Traceback', result.stderr + result.stdout)
        return json.loads(result.stdout)

    def add(self, entity, payload, request='req-1', ok=True):
        path = self.root / 'input.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        return self.cli('add', '--entity', entity, '--file', str(path),
                        '--request-id', request, ok=ok)
