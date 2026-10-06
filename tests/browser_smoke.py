"""Optional real-browser gate. Uses existing Chromium, no production dependency.
Run: uv run --with playwright==1.58.0 python tests/browser_smoke.py
Start a localhost static server first; override COFFEE_VIEW_URL if needed.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'), headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':390,'height':844}, device_scale_factor=1)
    errors=[]
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.goto(os.environ.get('COFFEE_VIEW_URL','http://127.0.0.1:8765/'))
    page.wait_for_selector('article')
    assert page.locator('article').count()==3
    assert 'Вымышленные' in page.locator('.banner').inner_text()
    assert page.locator('form').count()==0
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('input[type=checkbox]').nth(0).check()
    page.locator('input[type=checkbox]').nth(1).check()
    assert 'Сравнение · 2' in page.locator('.compare').inner_text()
    page.locator('summary').first.click()
    assert page.locator('details').first.evaluate('(n)=>n.open')
    page.locator('select').nth(2).select_option('rating')
    assert '85' in page.locator('article').first.inner_text()
    page.locator('select').nth(1).select_option('00000000-0000-4000-8000-000000000006')
    assert page.locator('article').count()==1
    page.locator('select').nth(0).select_option('00000000-0000-4000-8000-000000000002')
    assert page.locator('article').count()==1
    page.locator('select').nth(1).select_option('')
    assert page.locator('article').count()==2
    page.locator('select').nth(0).select_option('00000000-0000-4000-8000-000000000001')
    screenshot=Path(os.environ.get('COFFEE_SCREENSHOT','/opt/data/cache/scratch/coffee-journal-mobile.png'))
    screenshot.parent.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(screenshot),full_page=True)
    page.set_viewport_size({'width':1280,'height':800})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
    print(json.dumps({'mobile_width':390,'desktop_width':1280,'overflow':False,'browser_errors':errors,'checks':'coffee/device/rating filters, comparison, details, demo label, no forms','screenshot':str(screenshot)}))
