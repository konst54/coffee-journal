"""Read-only checks of the hosted Supabase project with the PUBLIC key only (no secrets needed).

Usage: COFFEE_SUPABASE_URL=https://<ref>.supabase.co COFFEE_SUPABASE_KEY=sb_publishable_... python3 tools/verify_hosted.py
Exit code 0 only if every check passes. Makes no writes and sends no e-mails.
"""
import json
import os
import sys
import urllib.error
import urllib.request


def call(method, url, key, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={'apikey': key, 'content-type': 'application/json', 'accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read(1_000_000)
            return res.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        raw = err.read(100_000)
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, None


def run(url, key):
    checks = {}
    status, settings = call('GET', url + '/auth/v1/settings', key)
    checks['auth settings readable'] = status == 200 and isinstance(settings, dict)
    settings = settings if isinstance(settings, dict) else {}
    checks['public signup disabled'] = settings.get('disable_signup') is True
    checks['email login enabled'] = (settings.get('external') or {}).get('email') is True
    status, rows = call('GET', url + '/rest/v1/journal_snapshots?select=owner_id', key)
    checks['table exists (migration applied)'] = status in (200, 401, 403) and not (isinstance(rows, dict) and rows.get('code') in ('42P01', 'PGRST205'))
    checks['anonymous cannot read journals'] = status in (401, 403) or rows == []
    status, _ = call('POST', url + '/rest/v1/rpc/publish_journal', key, {'p_dataset': {}, 'p_expected_revision': 0})
    checks['anonymous cannot publish'] = status in (401, 403)
    status, _ = call('GET', url + '/rest/v1/writers?select=user_id', key)
    checks['writer allowlist not exposed'] = status >= 400
    return checks


if __name__ == '__main__':
    url = os.environ.get('COFFEE_SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('COFFEE_SUPABASE_KEY', '')
    if not url.startswith('https://') or not key or key.startswith('sb_secret_'):
        sys.exit('Set COFFEE_SUPABASE_URL and the PUBLIC COFFEE_SUPABASE_KEY (never a secret key).')
    result = run(url, key)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    sys.exit(0 if all(result.values()) else 1)
