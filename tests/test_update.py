import json
import unittest

from cli_case import CliCase


class UpdateTests(CliCase):
    """Corrections keep every previous version; no silent duplicate brews."""

    def setUp(self):
        super().setUp()
        coffee = self.add('coffee', {'name': 'Fictional'}, 'c')['id']
        self.batch = self.add('batch', {'coffee_id': coffee}, 'b')['id']
        self.brew = self.add('brew', {'batch_id': self.batch, 'coffee_g': 15, 'water_g': 250,
                                      'rating': 80, 'source_text': 'private'}, 'x')['id']

    def update(self, patch, request='fix-1', entity='brew', record=None, ok=True):
        path = self.root / 'patch.json'
        path.write_text(json.dumps(patch), encoding='utf-8')
        return self.cli('update', '--entity', entity, '--id', record or self.brew,
                        '--file', str(path), '--request-id', request, ok=ok)

    def get(self):
        return self.cli('get', '--entity', 'brew', '--id', self.brew)

    def test_patch_changes_fields_and_keeps_history(self):
        result = self.update({'rating': 85, 'temperature_c': None, 'taste_notes': 'ярче'})
        self.assertEqual(result, {'id': self.brew, 'version': 2})
        record = self.get()
        self.assertEqual((record['rating'], record['taste_notes'], record['coffee_g']), (85, 'ярче', 15))
        history = self.cli('history', '--entity', 'brew', '--id', self.brew)
        self.assertEqual([h['version'] for h in history], [1, 2])
        self.assertEqual(history[0]['record']['rating'], 80)
        self.assertEqual(history[1]['record'], record)
        self.assertEqual(len(self.cli('list', '--entity', 'brew')), 1)

    def test_replay_and_conflict(self):
        first = self.update({'rating': 85})
        self.assertEqual(first, self.update({'rating': 85}))
        self.update({'rating': 86}, ok=False)
        self.assertEqual(len(self.cli('history', '--entity', 'brew', '--id', self.brew)), 2)
        self.assertEqual(self.update({'rating': 90}, 'fix-2')['version'], 3)

    def test_invalid_patches_leave_record_unchanged(self):
        before = self.get()
        missing = '00000000-0000-4000-8000-000000000000'
        bad = [{'rating': 101}, {'surprise': 1}, {'id': missing}, {'batch_id': None},
               {'batch_id': missing}, {}, [], {'brewed_at': '2026-10-05T08:00:00'}]
        for i, patch in enumerate(bad):
            with self.subTest(patch=patch):
                self.assertIn('error', self.update(patch, 'bad-%d' % i, ok=False))
        self.update({'rating': 85}, 'other', record=missing, ok=False)
        self.update({'name': 'x'}, 'wrong-entity', entity='coffee', ok=False)
        self.assertEqual(self.get(), before)
        self.assertEqual(len(self.cli('history', '--entity', 'brew', '--id', self.brew)), 1)

    def test_export_excludes_history_and_private_fields(self):
        self.update({'rating': 85, 'source_text': 'still private'})
        out = self.root / 'export.json'
        self.cli('export', '--file', str(out))
        data = json.loads(out.read_text())
        self.assertEqual(set(data), {'schema_version', 'coffees', 'batches', 'equipment', 'recipes', 'brews'})
        self.assertNotIn('source_text', data['brews'][0])
        self.assertEqual(data['brews'][0]['rating'], 85)


    def test_backup_restores_records_and_history(self):
        self.update({'rating': 85})
        backup = self.root / 'restore' / 'journal-backup.sqlite3'
        self.cli('backup', '--file', str(backup))
        self.update({'rating': 90}, 'after-backup')
        self.env['COFFEE_JOURNAL_DB'] = str(backup)  # restore = point the CLI at the copy
        self.assertEqual(self.get()['rating'], 85)
        self.assertEqual([h['record']['rating'] for h in self.cli('history', '--entity', 'brew', '--id', self.brew)], [80, 85])


if __name__ == '__main__':
    unittest.main()
