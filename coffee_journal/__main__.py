"""Run with python3 -m coffee_journal; all responses are JSON."""
import argparse
import json
import sqlite3
import sys
from .storage import Journal


MAX_INPUT_BYTES = 5 * 1024 * 1024


def read_json(path):
    # Bound memory before parsing; payloads come from chat/OCR and are untrusted.
    with open(path, 'rb') as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError('Input file too large')
    return json.loads(raw.decode('utf-8'))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Private local coffee journal')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    add = sub.add_parser('add')
    add.add_argument('--entity', required=True, choices=['coffee', 'batch', 'equipment', 'recipe', 'brew'])
    add.add_argument('--file', required=True)
    add.add_argument('--request-id', required=True)
    bundle = sub.add_parser('import')
    bundle.add_argument('--file', required=True)
    bundle.add_argument('--request-id', required=True)
    update = sub.add_parser('update')
    update.add_argument('--entity', required=True, choices=['coffee', 'batch', 'equipment', 'recipe', 'brew'])
    update.add_argument('--id', required=True)
    update.add_argument('--file', required=True)
    update.add_argument('--request-id', required=True)
    for name in ('list', 'get', 'history'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--entity', required=True, choices=['coffee', 'batch', 'equipment', 'recipe', 'brew'])
        if name != 'list':
            cmd.add_argument('--id', required=True)
    for name in ('export', 'backup'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--file', required=True)
    args = parser.parse_args(argv)
    journal = None
    try:
        journal = Journal()
        if args.command == 'init':
            result = {'ok': True, 'schema_version': 1}
        elif args.command == 'add':
            result = {'id': journal.add(args.entity, read_json(args.file), args.request_id)}
        elif args.command == 'import':
            result = journal.import_bundle(read_json(args.file), args.request_id)
        elif args.command == 'update':
            result = journal.update(args.entity, args.id, read_json(args.file), args.request_id)
        elif args.command == 'history':
            result = journal.history(args.entity, args.id)
        elif args.command == 'get':
            result = journal.get(args.entity, args.id)
        elif args.command == 'export':
            from .storage import write_private
            write_private(args.file, json.dumps(journal.export(), ensure_ascii=False, allow_nan=False, indent=2))
            result = {'ok': True}
        elif args.command == 'backup':
            journal.backup(args.file)
            result = {'ok': True}
        else:
            result = journal.list(args.entity)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, TypeError, OSError, RecursionError, sqlite3.Error):
        print(json.dumps({'error': 'Invalid request or storage operation failed'}))
        return 1
    finally:
        if journal is not None:
            journal.close()


if __name__ == '__main__':
    sys.exit(main())
