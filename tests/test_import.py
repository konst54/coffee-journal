import json
import unittest

from cli_case import CliCase


class ImportTests(CliCase):
    """Atomic multi-record import: new bag + first brew from one chat message."""

    def bundle(self):
        return {'records': [
            {'entity': 'coffee', 'ref': 'c', 'data': {'name': 'Fictional Test Coffee', 'labeled_notes': 'bag text'}},
            {'entity': 'batch', 'ref': 'b', 'data': {'coffee_id': {'$ref': 'c'}, 'roast_date': None}},
            {'entity': 'equipment', 'ref': 'v60', 'data': {'name': 'V60', 'kind': 'brewer'}},
            {'entity': 'brew', 'ref': 'x', 'data': {'batch_id': {'$ref': 'b'}, 'brewer_id': {'$ref': 'v60'},
                                                     'coffee_g': 15, 'water_g': 250, 'rating': 82}},
        ]}

    def run_import(self, bundle, request='msg-1', ok=True):
        path = self.root / 'bundle.json'
        path.write_text(json.dumps(bundle), encoding='utf-8')
        return self.cli('import', '--file', str(path), '--request-id', request, ok=ok)

    def counts(self):
        return {e: len(self.cli('list', '--entity', e)) for e in ('coffee', 'batch', 'equipment', 'recipe', 'brew')}

    def test_bundle_resolves_refs_and_reads_back(self):
        result = self.run_import(self.bundle())
        self.assertEqual(set(result['refs']), {'c', 'b', 'v60', 'x'})
        self.assertEqual(len(result['ids']), 4)
        brew = self.cli('get', '--entity', 'brew', '--id', result['refs']['x'])
        self.assertEqual(brew['batch_id'], result['refs']['b'])
        self.assertEqual(brew['brewer_id'], result['refs']['v60'])
        batch = self.cli('get', '--entity', 'batch', '--id', result['refs']['b'])
        self.assertEqual(batch['coffee_id'], result['refs']['c'])

    def test_replay_is_idempotent_and_conflict_rejected(self):
        first = self.run_import(self.bundle())
        self.assertEqual(first, self.run_import(self.bundle()))
        self.assertEqual(self.counts()['brew'], 1)
        changed = self.bundle()
        changed['records'][3]['data']['rating'] = 83
        self.assertIn('error', self.run_import(changed, ok=False))
        self.assertEqual(self.counts(), {'coffee': 1, 'batch': 1, 'equipment': 1, 'recipe': 0, 'brew': 1})

    def test_any_invalid_record_rolls_back_everything(self):
        bad = self.bundle()
        bad['records'][3]['data']['rating'] = 101
        self.run_import(bad, ok=False)
        self.assertEqual(self.counts(), {'coffee': 0, 'batch': 0, 'equipment': 0, 'recipe': 0, 'brew': 0})
        # Equipment kind is checked against records created earlier in the same bundle.
        wrong_kind = self.bundle()
        wrong_kind['records'][3]['data']['grinder_id'] = {'$ref': 'v60'}
        self.run_import(wrong_kind, 'msg-2', ok=False)
        self.assertEqual(sum(self.counts().values()), 0)
        # The request ID of a failed import is not burned.
        self.run_import(self.bundle(), 'msg-2')

    def test_bad_refs_and_shapes_rejected(self):
        cases = []
        forward = self.bundle(); forward['records'].reverse(); cases.append(forward)
        unknown = self.bundle(); unknown['records'][1]['data']['coffee_id'] = {'$ref': 'nope'}; cases.append(unknown)
        dup = self.bundle(); dup['records'][2]['ref'] = 'c'; cases.append(dup)
        not_id = self.bundle(); not_id['records'][3]['data']['taste_notes'] = {'$ref': 'c'}; cases.append(not_id)
        bad_entity = self.bundle(); bad_entity['records'][0]['entity'] = 'user'; cases.append(bad_entity)
        extra = self.bundle(); extra['records'][0]['surprise'] = 1; cases.append(extra)
        cases += [{'records': []}, {'records': 'x'}, {}, {'records': [{'entity': 'coffee'}]},
                  {'records': [{'entity': 'coffee', 'data': {'name': 'x'}}] * 201}]
        for i, case in enumerate(cases):
            with self.subTest(i=i):
                self.assertIn('error', self.run_import(case, 'bad-%d' % i, ok=False))
        self.assertEqual(sum(self.counts().values()), 0)

    def test_bundle_can_reference_existing_records(self):
        coffee = self.add('coffee', {'name': 'Existing'}, 'old-coffee')['id']
        batch = self.add('batch', {'coffee_id': coffee}, 'old-batch')['id']
        result = self.run_import({'records': [{'entity': 'brew', 'data': {'batch_id': batch, 'coffee_g': 16}}]})
        self.assertEqual(self.cli('get', '--entity', 'brew', '--id', result['ids'][0])['batch_id'], batch)

    def test_oversized_input_file_rejected(self):
        # Each record is individually valid; only the 5 MiB input cap rejects the file.
        big = {'records': [{'entity': 'coffee', 'data': {'name': 'x', 'notes': 'y' * 99000}}] * 60}
        self.assertGreater(len(json.dumps(big)), 5 * 1024 * 1024)
        self.assertIn('error', self.run_import(big, ok=False))
        self.assertEqual(self.cli('list', '--entity', 'coffee'), [])

    def test_deeply_nested_json_is_a_clean_error(self):
        path = self.root / 'deep.json'
        path.write_text('[' * 100000, encoding='utf-8')
        self.assertIn('error', self.cli('import', '--file', str(path), '--request-id', 'deep', ok=False))


if __name__ == '__main__':
    unittest.main()
