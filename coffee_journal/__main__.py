"""Run with python3 -m coffee_journal; all responses are JSON."""
import argparse
import json
import sqlite3
import sys
from .storage import Journal


def main(argv=None):
    parser = argparse.ArgumentParser(description='Private local coffee journal')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    add = sub.add_parser('add')
    add.add_argument('--entity', required=True, choices=['coffee', 'batch', 'equipment', 'recipe', 'brew'])
    add.add_argument('--file', required=True)
    add.add_argument('--request-id', required=True)
    for name in ('list', 'get'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--entity', required=True, choices=['coffee', 'batch', 'equipment', 'recipe', 'brew'])
        if name == 'get':
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
            with open(args.file, encoding='utf-8') as source:
                payload = json.load(source)
            result = {'id': journal.add(args.entity, payload, args.request_id)}
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
    except (ValueError, TypeError, OSError, sqlite3.Error):
        print(json.dumps({'error': 'Invalid request or storage operation failed'}))
        return 1
    finally:
        if journal is not None:
            journal.close()


if __name__ == '__main__':
    sys.exit(main())
