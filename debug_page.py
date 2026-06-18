import os
import json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

cookie_str = os.getenv('XHS_COOKIE', '')

headers_info = []

def handle_request(request):
    url = request.url
    if 'user_posted' in url:
        headers_info.append({
            'url': url,
            'method': request.method,
            'headers': dict(request.headers),
            'params': request.url.split('?')[1] if '?' in request.url else ''
        })

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    page.on('request', handle_request)
    
    if cookie_str:
        cookies = []
        for cookie in cookie_str.split(';'):
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
    
    page.goto('https://www.xiaohongshu.com/user/profile/5bd9405f6b58b737b5401d2e', wait_until='networkidle')
    page.wait_for_timeout(3000)
    
    page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
    page.wait_for_timeout(3000)
    
    with open('./data/request_headers.json', 'w', encoding='utf-8') as f:
        json.dump(headers_info, f, ensure_ascii=False, indent=2)
    
    print(f'捕获到 {len(headers_info)} 个请求')
    for info in headers_info:
        print(f'\nURL: {info["url"]}')
        print(f'Method: {info["method"]}')
        print(f'Params: {info["params"]}')
        print(f'Headers:')
        for k, v in info["headers"].items():
            print(f'  {k}: {v}')
    
    browser.close()
