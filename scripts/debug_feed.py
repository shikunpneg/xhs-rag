"""调试feed数据结构"""
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

cookie = os.getenv('XHS_COOKIE')

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
    
    page.goto('https://www.xiaohongshu.com', wait_until='domcontentloaded', timeout=60000)
    
    result = page.evaluate("""(() => {
        const state = window.__INITIAL_STATE__;
        if (!state || !state.feed) return {error: 'no feed'};
        
        const feeds = state.feed.feeds;
        return {
            feedsType: typeof feeds,
            feedsIsArray: Array.isArray(feeds),
            feedsLength: feeds ? (Array.isArray(feeds) ? feeds.length : Object.keys(feeds).length) : 0,
            feedsKeys: feeds && !Array.isArray(feeds) ? Object.keys(feeds).slice(0, 10) : null,
            firstItem: feeds && Array.isArray(feeds) && feeds.length > 0 ? JSON.stringify(feeds[0]).slice(0, 1000) : null,
        };
    })()""")
    
    print(f'feeds类型: {result["feedsType"]}')
    print(f'feeds是否数组: {result["feedsIsArray"]}')
    print(f'feeds长度: {result["feedsLength"]}')
    
    if result['feedsKeys']:
        print(f'\nfeeds键: {result["feedsKeys"]}')
    
    if result['firstItem']:
        print(f'\n第一个元素: {result["firstItem"]}')
    
    browser.close()