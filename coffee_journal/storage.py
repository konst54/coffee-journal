"""Private SQLite journal. Fixed identifiers, strict validation, atomic idempotency."""
import json
import os
from pathlib import Path
import sqlite3
import uuid
from .validation import FIELDS, PRIVATE_FIELDS, validate, validate_bundle, valid_uuid

DEFAULT_DB = '/opt/data/coffee-journal-private/journal.sqlite3'
PLURALS = {'coffee':'coffees','batch':'batches','equipment':'equipment','recipe':'recipes','brew':'brews'}
REFERENCES = {'batch':{'coffee_id':('coffee',None)},'recipe':{'brewer_id':('equipment','brewer')},
 'brew':{'batch_id':('batch',None),'brewer_id':('equipment','brewer'),'grinder_id':('equipment','grinder'),'recipe_id':('recipe',None)}}


def private_parent(path):
    # Do not chmod arbitrary ancestors. Refuse symlinks on the complete path.
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Symlinks are not allowed')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def write_private(path, data):
    path = private_parent(path)
    # Exclusive creation avoids accidental overwrites and symlink races.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())


class Journal:
    def __init__(self, path=None):
        self.path = private_parent(path or os.environ.get('COFFEE_JOURNAL_DB', DEFAULT_DB))
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        os.close(fd)
        self.connection = sqlite3.connect(self.path, timeout=10)
        self.connection.execute('PRAGMA foreign_keys=ON')
        for entity in FIELDS:
            self.connection.execute(f'CREATE TABLE IF NOT EXISTS {entity} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self.connection.execute('CREATE TABLE IF NOT EXISTS requests (request_id TEXT PRIMARY KEY, entity TEXT NOT NULL, canonical TEXT NOT NULL, record_id TEXT NOT NULL)')
        self.connection.commit()

    def add(self, entity, payload, request_id):
        record = validate(entity, payload)
        canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False)
        return self._idempotent(request_id, entity, canonical, lambda: self._insert(entity, record))

    def import_bundle(self, bundle, request_id):
        """Insert several records in one transaction; later records may use {"$ref": label}."""
        items = validate_bundle(bundle)
        canonical = json.dumps(bundle, ensure_ascii=False, sort_keys=True, allow_nan=False)

        def work():
            refs, ids = {}, []
            for item in items:
                data = dict(item['data'])
                for key, value in data.items():
                    if isinstance(value, dict):
                        if set(value) != {'$ref'} or not key.endswith('_id'):
                            continue  # left for validate() to reject or accept (e.g. sensory)
                        if value['$ref'] not in refs:
                            raise ValueError('Unknown or forward reference')
                        data[key] = refs[value['$ref']]
                record_id = self._insert(item['entity'], validate(item['entity'], data))
                ids.append(record_id)
                if 'ref' in item:
                    refs[item['ref']] = record_id
            return json.dumps({'ids': ids, 'refs': refs})

        return json.loads(self._idempotent(request_id, 'bundle', canonical, work))

    def _idempotent(self, request_id, kind, canonical, work):
        if not isinstance(request_id, str) or not request_id.strip() or len(request_id)>500:
            raise ValueError('Request ID required')
        # BEGIN IMMEDIATE prevents concurrent replays from racing.
        self.connection.execute('BEGIN IMMEDIATE')
        try:
            prev = self.connection.execute('SELECT entity,canonical,record_id FROM requests WHERE request_id=?', (request_id,)).fetchone()
            if prev:
                if prev[:2] != (kind, canonical):
                    raise ValueError('Idempotency conflict')
                self.connection.commit()
                return prev[2]
            result = work()
            self.connection.execute('INSERT INTO requests VALUES (?,?,?,?)', (request_id, kind, canonical, result))
            self.connection.commit()
            return result
        except Exception:
            self.connection.rollback()
            raise

    def _insert(self, entity, record):
        """Reference checks and INSERT; the caller owns the transaction."""
        if entity=='batch' and not record.get('coffee_id'):
            raise ValueError('Coffee required')
        for key,(target,kind) in REFERENCES.get(entity,{}).items():
            if record.get(key) is not None:
                ref = self.get(target, record[key])
                if kind and ref.get('kind') != kind:
                    raise ValueError('Equipment kind mismatch')
        record['id'] = record.get('id') or str(uuid.uuid4())
        self.connection.execute(f'INSERT INTO {entity} VALUES (?, ?)',
                                (record['id'], json.dumps(record, ensure_ascii=False, allow_nan=False)))
        return record['id']

    def list(self, entity):
        if entity not in FIELDS:
            raise ValueError('Invalid entity')
        return [json.loads(row[0]) for row in self.connection.execute(f'SELECT payload FROM {entity} ORDER BY rowid')]

    def get(self, entity, record_id):
        if entity not in FIELDS:
            raise ValueError('Invalid entity')
        valid_uuid(record_id)
        row = self.connection.execute(f'SELECT payload FROM {entity} WHERE id=?', (record_id,)).fetchone()
        if row is None:
            raise ValueError('Record not found')
        return json.loads(row[0])

    def export(self):
        # Snapshot all tables consistently; user-facing comments remain private data!
        self.connection.execute('BEGIN')
        try:
            return {'schema_version':1, **{PLURALS[e]:[{k:v for k,v in r.items() if k not in PRIVATE_FIELDS} for r in self.list(e)] for e in FIELDS}}
        finally:
            self.connection.rollback()

    def backup(self, path):
        path = private_parent(path)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        dest = sqlite3.connect(path)
        try:
            self.connection.backup(dest)
        finally:
            dest.close()

    def close(self):
        self.connection.close()
