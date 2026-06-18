"""调试笔记详情页数据结构"""
import os
import sys
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

cookie = os.getenv('XHS_COOKIE')

note_id = '6a258a8f0000000008032f07'

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
    
    url = f'https://www.xiaohongshu.com/explore/{note_id}'
    print(f'访问笔记详情: {url}')
    page.goto(url, wait_until='networkidle', timeout=60000)
    time.sleep(15)
    
    result = page.evaluate("""(() => {
        const state = window.__INITIAL_STATE__;
        
        const result = {
            stateExists: !!state,
            noteExists: !!state && !!state.note,
            noteDataExists: !!state && !!state.note && !!state.note.data,
            noteKeys: state && state.note ? Object.keys(state.note).slice(0, 20) : [],
        };
        
        if (state && state.note && state.note.data) {
            let data = state.note.data;
            if (data._value !== undefined) data = data._value;
            if (data._rawValue !== undefined) data = data._rawValue;
            
            result.dataKeys = Object.keys(data).slice(0, 30);
            result.desc = data.desc || 'NOT FOUND';
            result.descType = typeof data.desc;
            result.title = data.title || data.displayTitle || 'NOT FOUND';
            result.likedCount = data.liked_count || (data.interactInfo && data.interactInfo.likedCount) || 0;
            result.commentCount = data.comment_count || (data.interactInfo && data.interactInfo.commentCount) || 0;
            result.shareCount = data.share_count || (data.interactInfo && data.interactInfo.shareCount) || 0;
        }
        
        return result;
    })()""")
    
    print('\n=== 笔记详情页数据结构 ===')
    print(f'state存在: {result["stateExists"]}')
    print(f'note存在: {result["noteExists"]}')
    print(f'note.data存在: {result["noteDataExists"]}')
    print(f'note键: {result["noteKeys"]}')
    
    if result.get('dataKeys'):
        print(f'\ndata键: {result["dataKeys"]}')
        print(f'desc: {result["desc"][:100]}')
        print(f'desc类型: {result["descType"]}')
        print(f'title: {result["title"][:50]}')
        print(f'likedCount: {result["likedCount"]}')
        print(f'commentCount: {result["commentCount"]}')
        print(f'shareCount: {result["shareCount"]}')
    
    browser.close()