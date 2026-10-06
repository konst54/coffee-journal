"""Real-browser check of the Supabase sign-in path with the network mocked (no real project).
Run: uv run --with playwright==1.58.0 python tests/browser_auth_smoke.py   (CHROMIUM_PATH optional)
"""
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'https://fakeproject.supabase.co'
site = Path(tempfile.mkdtemp())
shutil.copytree(ROOT / 'web', site, dirs_exist_ok=True)
(site / 'config.js').write_text(f"export const SUPABASE_URL='{PROJECT}';\nexport const SUPABASE_PUBLISHABLE_KEY='sb_publishable_fake';\n")
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
private = {'schema_version': 1, 'coffees': [{'id': 'c', 'name': 'Мой тестовый кофе'}], 'batches': [{'id': 'b', 'coffee_id': 'c'}],
           'equipment': [], 'recipes': [], 'brews': [{'id': 'x', 'batch_id': 'b', 'rating': 77, 'taste_notes': 'Тест'}]}
seen = []

def supabase(route):
    req = route.request
    seen.append((req.method, req.url.split('?')[0].replace(PROJECT, ''), req.headers.get('authorization')))
    if '/auth/v1/otp' in req.url:
        assert json.loads(req.post_data)['create_user'] is False
        return route.fulfill(status=200, body='{}', content_type='application/json')
    if '/rest/v1/journal_snapshots' in req.url:
        return route.fulfill(status=200, body=json.dumps([{'dataset': private, 'revision': 3}]), content_type='application/json')
    if '/auth/v1/logout' in req.url:
        return route.fulfill(status=204, body='')
    return route.fulfill(status=404, body='{}')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route(PROJECT + '/**', supabase)
    page.goto(url)
    page.wait_for_selector('article')
    assert 'Вымышленные' in page.locator('.banner').inner_text()
    assert page.locator('form').count() == 0 and page.locator('input[type=password]').count() == 0
    page.fill('#auth input[type=email]', 'me@example.org')
    page.click('#auth button')
    page.wait_for_selector('text=Ссылка отправлена')
    page.goto('about:blank')  # a magic link opens as a fresh navigation
    page.goto(url + '#access_token=acc&refresh_token=ref&expires_in=3600&token_type=bearer&type=magiclink')
    page.wait_for_selector('text=Личные данные')
    assert '#' not in page.url, page.url
    assert 'Мой тестовый кофе' in page.inner_text('#app')
    assert page.evaluate("localStorage.getItem('coffee-journal.refresh')") == 'ref'
    assert ('GET', '/rest/v1/journal_snapshots', 'Bearer acc') in seen
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.click('#auth button')
    page.wait_for_selector('text=Вы вышли')
    assert 'Вымышленные' in page.locator('.banner').inner_text()
    assert page.evaluate("localStorage.getItem('coffee-journal.refresh')") is None
    assert not errors, errors
    browser.close()
server.shutdown()
shutil.rmtree(site)
print(json.dumps({'auth_flow': 'ok', 'requests': [s[:2] for s in seen], 'browser_errors': errors}))
