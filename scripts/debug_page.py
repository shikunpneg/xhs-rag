"""调试页面内容"""
import os
import sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

cookie = os.getenv('XHS_COOKIE')
user_id = '5bd9405f6b58b737b5401d2e'

print(f'Cookie: {cookie[:50]}...')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
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
        print(f'已加载 {len(cookies)} 个Cookie')
    
    print('\n=== 访问主页 ===')
    page.goto('https://www.xiaohongshu.com', wait_until='domcontentloaded', timeout=60000)
    print(f'URL: {page.url}')
    print(f'Title: {page.title()}')
    
    print('\n=== 页面HTML前500字符 ===')
    html = page.content()
    print(html[:500])
    
    print('\n=== 页面内所有script标签内容 ===')
    scripts = page.query_selector_all('script')
    for i, script in enumerate(scripts):
        text = script.inner_text()
        if text:
            print(f'\n--- Script {i} (长度: {len(text)}) ---')
            if len(text) < 500:
                print(text)
            else:
                print(text[:200] + '...')
                if 'INITIAL' in text or 'note' in text.lower() or 'user' in text.lower():
                    print(f'包含关键词: INITIAL={("INITIAL" in text)}, note={("note" in text.lower())}, user={("user" in text.lower())}')
    
    print('\n=== 访问用户页面 ===')
    page.goto(f'https://www.xiaohongshu.com/user/profile/{user_id}', wait_until='domcontentloaded', timeout=60000)
    print(f'URL: {page.url}')
    print(f'Title: {page.title()}')
    
    print('\n=== 用户页面HTML前500字符 ===')
    html = page.content()
    print(html[:500])
    
    print('\n=== 用户页面内所有script标签内容 ===')
    scripts = page.query_selector_all('script')
    for i, script in enumerate(scripts):
        text = script.inner_text()
        if text:
            print(f'\n--- Script {i} (长度: {len(text)}) ---')
            if len(text) < 500:
                print(text)
            else:
                print(text[:200] + '...')
                if 'INITIAL' in text or 'note' in text.lower() or 'user' in text.lower():
                    print(f'包含关键词: INITIAL={("INITIAL" in text)}, note={("note" in text.lower())}, user={("user" in text.lower())}')
    
    print('\n=== 页面内链接 ===')
    links = page.query_selector_all('a')
    print(f'共有 {len(links)} 个链接')
    for link in links[:20]:
        href = link.get_attribute('href')
        if href and '/explore/' in href:
            print(f'  {href}')
    
    browser.close()