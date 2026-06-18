"""调试搜索API"""
import os
import sys
import time
import json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

cookie = os.getenv('XHS_COOKIE')

all_api_data = {}

def handle_response(response):
    url = response.url
    try:
        if response.status == 200:
            if '/api/sns/v1/search' in url or '/api/sns/v2/search' in url or '/api/sns/v1/feed' in url:
                try:
                    data = response.json()
                    if data.get('code') == 0 and 'data' in data:
                        all_api_data[url] = data
                        print(f'✅ 捕获API: {url}')
                        print(f'   数据长度: {len(json.dumps(data))}')
                except:
                    pass
    except:
        pass

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--window-size=1920,1080',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--start-maximized',
        ]
    )
    
    page = browser.new_page(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    page.on('response', handle_response)
    
    if cookie:
        cookies = []
        for cookie in cookie.split(';'):
            cookie = cookie.strip()
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.xiaohongshu.com',
                    'path': '/'
                })
        page.context.add_cookies(cookies)
    
    page.goto('https://www.xiaohongshu.com', wait_until='networkidle', timeout=60000)
    time.sleep(10)
    
    print('\n=== 尝试搜索 ===')
    try:
        search_input = page.locator('input[placeholder*="搜索"]')
        if search_input.count() > 0:
            search_input.fill('美食')
            time.sleep(2)
            search_input.press('Enter')
            time.sleep(15)
    except Exception as e:
        print(f'搜索失败: {e}')
    
    print(f'\n=== 共捕获 {len(all_api_data)} 个API响应 ===')
    
    for url, data in all_api_data.items():
        print(f'\n--- {url} ---')
        if isinstance(data.get('data'), dict):
            keys = list(data['data'].keys())
            print(f'数据键: {keys}')
            
            if 'notes' in data['data']:
                notes = data['data']['notes']
                if isinstance(notes, list):
                    print(f'笔记数量: {len(notes)}')
                    if len(notes) > 0:
                        first_note = notes[0]
                        print(f'第一个笔记键: {list(first_note.keys())[:10]}')
                        print(f'标题: {first_note.get("title", "")[:50]}')
                        print(f'note_id: {first_note.get("note_id", "")}')
                        print(f'desc: {first_note.get("desc", "")[:100]}')
        
        elif isinstance(data.get('data'), list):
            print(f'数据长度: {len(data["data"])}')
    
    browser.close()