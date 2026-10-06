"""Publish the private journal's export to the owner's Supabase projection (stdlib only).

Security model: acts as the owner's normal Auth user (never a service/secret key). Only the
rotating refresh token is stored, in a 0600 file next to the private DB; the password is read
once from stdin by `publish-login` and never written. Tokens are never printed or logged.
"""
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

from .storage import private_parent

PROJECT_URL = re.compile(r'^https://[a-z0-9-]+\.supabase\.co$|^http://127\.0\.0\.1:\d+$')


class PublishError(Exception):
    """Category is safe to show: auth, conflict, verify, config, network, http."""

    def __init__(self, category):
        super().__init__(category)
        self.category = category


def settings():
    url = os.environ.get('COFFEE_SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('COFFEE_SUPABASE_KEY', '')
    if not PROJECT_URL.match(url) or not key or key.startswith('sb_secret_'):
        raise PublishError('config')
    db = os.environ.get('COFFEE_JOURNAL_DB', '/opt/data/coffee-journal-private/journal.sqlite3')
    session = os.environ.get('COFFEE_SUPABASE_SESSION', str(Path(db).parent / 'supabase-session.json'))
    return url, key, session


def _request(method, url, key, body=None, token=None, timeout=30):
    headers = {'apikey': key, 'content-type': 'application/json', 'accept': 'application/json'}
    if token:
        headers['authorization'] = 'Bearer ' + token
    data = None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read(8 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as err:
        detail = err.read(4096).decode('utf-8', 'replace')
        if err.code in (401, 403) or 'Writer not authorized' in detail or 'invalid_grant' in detail:
            raise PublishError('auth') from None
        if '40001' in detail:
            raise PublishError('conflict') from None
        raise PublishError('http') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise PublishError('network') from None
    if len(raw) > 8 * 1024 * 1024:
        raise PublishError('http')
    return json.loads(raw) if raw else None


def _save_session(path, refresh_token):
    path = private_parent(path)
    tmp = path.with_name(path.name + '.tmp')
    if tmp.exists():
        tmp.unlink()
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        json.dump({'refresh_token': refresh_token}, out)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, path)


def _load_session(path):
    path = private_parent(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        raise PublishError('auth') from None
    if os.fstat(fd).st_mode & 0o077:
        os.close(fd)
        raise PublishError('config')  # refuse a session file readable by others
    with os.fdopen(fd, encoding='utf-8') as source:
        token = json.load(source).get('refresh_token')
    if not isinstance(token, str) or not token:
        raise PublishError('auth')
    return token


def _adopt(tokens, session):
    if not isinstance(tokens, dict) or not isinstance(tokens.get('access_token'), str) or not isinstance(tokens.get('refresh_token'), str):
        raise PublishError('auth')
    _save_session(session, tokens['refresh_token'])
    return tokens


def login(email, password):
    url, key, session = settings()
    tokens = _adopt(_request('POST', url + '/auth/v1/token?grant_type=password', key,
                             {'email': email, 'password': password}), session)
    return {'ok': True, 'user_id': (tokens.get('user') or {}).get('id')}


def publish(journal):
    url, key, session = settings()
    token = _adopt(_request('POST', url + '/auth/v1/token?grant_type=refresh_token', key,
                            {'refresh_token': _load_session(session)}), session)['access_token']
    rows = _request('GET', url + '/rest/v1/journal_snapshots?select=revision', key, token=token)
    if not isinstance(rows, list) or len(rows) > 1:
        raise PublishError('verify')
    expected = rows[0]['revision'] if rows else 0
    dataset = journal.export()
    revision = _request('POST', url + '/rest/v1/rpc/publish_journal', key,
                        {'p_dataset': dataset, 'p_expected_revision': expected}, token=token)
    back = _request('GET', url + '/rest/v1/journal_snapshots?select=dataset,revision', key, token=token)
    if not isinstance(back, list) or len(back) != 1 or back[0].get('revision') != revision or back[0].get('dataset') != dataset:
        raise PublishError('verify')
    return {'ok': True, 'revision': revision, 'brews': len(dataset['brews'])}
