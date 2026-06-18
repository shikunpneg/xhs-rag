"""调试INITIAL_STATE数据结构"""
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
        if (!state) return {error: 'no state'};
        
        const getKeys = (obj, prefix = '') => {
            const keys = [];
            if (!obj || typeof obj !== 'object') return keys;
            
            for (const key of Object.keys(obj)) {
                const fullKey = prefix ? `${prefix}.${key}` : key;
                keys.push(fullKey);
                
                if (obj[key] && typeof obj[key] === 'object') {
                    keys.push(...getKeys(obj[key], fullKey));
                }
            }
            return keys;
        };
        
        const keys = getKeys(state).slice(0, 100);
        
        return {
            keys: keys,
            explore: state.explore ? JSON.stringify(state.explore).slice(0, 500) : null,
            feed: state.feed ? JSON.stringify(state.feed).slice(0, 500) : null,
            hasNotes: keys.some(k => k.includes('note') || k.includes('feed')),
        };
    })()""")
    
    print('=== INITIAL_STATE 键路径 ===')
    for key in result['keys'][:50]:
        print(f'  {key}')
    
    print('\n=== explore 内容 ===')
    if result['explore']:
        print(result['explore'])
    
    print('\n=== feed 内容 ===')
    if result['feed']:
        print(result['feed'])
    
    print(f'\n=== 是否包含笔记相关键: {result["hasNotes"]} ===')
    
    browser.close()