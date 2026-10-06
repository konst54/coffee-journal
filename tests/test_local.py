import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalTests(unittest.TestCase):
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

    def test_validation_rejects_unknown_keys_and_bad_types(self):
        for payload in ({'name': 'Coffee', 'surprise': None}, {'name': None},
                        {'name': ''}, {'name': 123}, {'name': 'Coffee', 'id': 'bad'},
                        {'name': 'Coffee', 'source_refs': 'private/photo.jpg'},
                        {'name': 'Coffee', 'notes': float('nan')}):
            with self.subTest(payload=payload):
                self.assertIn('error', self.add('coffee', payload, ok=False))
        self.assertEqual(self.cli('list', '--entity', 'coffee'), [])
        self.add('batch', {'coffee_id': None}, 'null-coffee', ok=False)
        self.add('equipment', {'name': 'X'}, 'missing-kind', ok=False)
        coffee = self.add('coffee', {'name':'Safe'}, 'safe')['id']
        batch = self.add('batch', {'coffee_id':coffee}, 'safe-batch')['id']
        self.add('brew', {'batch_id':batch, 'sensory':{'source_text':'secret'}}, 'nested-private', ok=False)
        self.add('brew', {'batch_id':batch, 'sensory':{'sweetness':True}}, 'boolean-sensory', ok=False)

    def test_validation_all_entities_dates_numbers_and_nulls(self):
        coffee = self.add('coffee', {'name': 'C', 'roaster': None})['id']
        batch = self.add('batch', {'coffee_id': coffee, 'roast_date': '2026-09-30',
                                 'initial_weight_g': 250}, 'batch')['id']
        brewer = self.add('equipment', {'name': 'V60', 'kind': 'brewer'}, 'brewer')['id']
        grinder = self.add('equipment', {'name': 'Hand grinder', 'kind': 'grinder'}, 'grinder')['id']
        recipe = self.add('recipe', {'name': 'R', 'brewer_id': brewer,
                         'steps': [{'name': None, 'instruction': 'Pour', 'duration_s': 30, 'water_g': 50}]}, 'recipe')['id']
        brew = {'batch_id': batch, 'brewer_id': brewer, 'grinder_id': grinder,
                'recipe_id': recipe, 'brewed_at': '2026-10-05T08:30:00+03:00',
                'coffee_g': 15, 'water_g': 250, 'rating': 100, 'sensory': {'sweetness': 5},
                'temperature_c': None}
        self.add('brew', brew, 'brew')
        bad = [('batch', {'coffee_id': coffee, 'roast_date': '2026-02-30'}),
               ('batch', {'coffee_id': coffee, 'roast_date': '20260930'}),
               ('equipment', {'name': 'X', 'kind': 'other'}),
               ('recipe', {'name': 'X', 'steps': [{'extra': 1}]}),
               ('brew', dict(brew, batch_id=None)),
               ('brew', dict(brew, brewed_at='2026-10-05T08:30:00')),
               ('brew', dict(brew, coffee_g=0)), ('brew', dict(brew, water_g=-1)),
               ('brew', dict(brew, temperature_c=101)),
               ('brew', dict(brew, duration_s=86401)),
               ('brew', dict(brew, tds=101)), ('brew', dict(brew, extraction_yield=-1)),
               ('brew', dict(brew, water_g=float('inf'))),
               ('brew', dict(brew, rating=True)), ('brew', dict(brew, rating=1.5)),
               ('brew', dict(brew, rating=101)), ('brew', dict(brew, rating=0))]
        for i, (entity, payload) in enumerate(bad):
            with self.subTest(entity=entity, payload=payload):
                self.add(entity, payload, 'bad-' + str(i), ok=False)

    def test_idempotency_foreign_keys_and_export_privacy(self):
        first = self.add('coffee', {'name': 'C', 'source_text': 'secret', 'source_refs': ['photo.jpg']})
        self.assertEqual(first, self.add('coffee', {'name': 'C', 'source_text': 'secret', 'source_refs': ['photo.jpg']}))
        self.add('coffee', {'name': 'Different'}, ok=False)
        self.add('batch', {'coffee_id': '00000000-0000-4000-8000-000000000000'}, 'missing', ok=False)
        batch = self.add('batch', {'coffee_id': first['id']}, 'batch')['id']
        grinder = self.add('equipment', {'name': 'G', 'kind': 'grinder'}, 'grinder')['id']
        self.add('brew', {'batch_id': batch, 'brewer_id': grinder}, 'wrong-kind', ok=False)
        brew = self.add('brew', {'batch_id': batch, 'coffee_g': 15, 'water_g': 225, 'rating': 80}, 'brew')['id']
        self.assertEqual(self.cli('get', '--entity', 'brew', '--id', brew)['rating'], 80)
        out = self.root / 'export.json'
        self.cli('export', '--file', str(out))
        data = json.loads(out.read_text())
        self.assertEqual(len(data['coffees']), 1)
        self.assertNotIn('source_text', data['coffees'][0])
        self.assertNotIn('source_refs', data['coffees'][0])
        backup = self.root / 'backup.sqlite3'
        self.cli('backup', '--file', str(backup))
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_symlink_db_rejected_without_changing_target(self):
        self.db.parent.mkdir()
        target = self.root / 'target'; target.write_text('safe')
        self.db.symlink_to(target)
        self.cli('init', ok=False)
        self.assertEqual(target.read_text(), 'safe')

    def test_init_and_coffee_roundtrip(self):
        self.cli('init')
        result = self.add('coffee', {'name': 'Test coffee', 'origin': None})
        record = self.cli('get', '--entity', 'coffee', '--id', result['id'])
        self.assertEqual(record['name'], 'Test coffee')
        self.assertEqual(record['id'], result['id'])
        self.assertEqual(self.cli('list', '--entity', 'coffee'), [record])
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.db.parent.stat().st_mode & 0o777, 0o700)


if __name__ == '__main__':
    unittest.main()
