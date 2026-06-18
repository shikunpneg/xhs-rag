"""调试笔记详情页数据结构 - noteDetailMap"""
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
        
        if (!state || !state.note) {
            return {error: 'state.note not found'};
        }
        
        const noteDetailMap = state.note.noteDetailMap;
        if (!noteDetailMap) {
            return {error: 'noteDetailMap not found'};
        }
        
        let map = noteDetailMap;
        if (map._value !== undefined) map = map._value;
        if (map._rawValue !== undefined) map = map._rawValue;
        
        const keys = Object.keys(map);
        
        if (keys.length === 0) {
            return {error: 'noteDetailMap is empty'};
        }
        
        const firstKey = keys[0];
        const firstNote = map[firstKey];
        
        if (!firstNote) {
            return {error: 'note data is null'};
        }
        
        const dataKeys = Object.keys(firstNote).slice(0, 30);
        
        return {
            mapKeys: keys.slice(0, 5),
            firstKey: firstKey,
            dataKeys: dataKeys,
            desc: firstNote.desc || 'NOT FOUND',
            descLength: firstNote.desc ? firstNote.desc.length : 0,
            title: firstNote.title || firstNote.displayTitle || 'NOT FOUND',
            likedCount: firstNote.liked_count || (firstNote.interactInfo && firstNote.interactInfo.likedCount) || 0,
            commentCount: firstNote.comment_count || (firstNote.interactInfo && firstNote.interactInfo.commentCount) || 0,
            shareCount: firstNote.share_count || (firstNote.interactInfo && firstNote.interactInfo.shareCount) || 0,
        };
    })()""")
    
    print('\n=== noteDetailMap 数据结构 ===')
    if result.get('error'):
        print(f'错误: {result["error"]}')
    else:
        print(f'map键: {result["mapKeys"]}')
        print(f'第一个键: {result["firstKey"]}')
        print(f'data键: {result["dataKeys"]}')
        print(f'desc长度: {result["descLength"]}')
        print(f'desc: {result["desc"][:200]}')
        print(f'title: {result["title"][:50]}')
        print(f'likedCount: {result["likedCount"]}')
        print(f'commentCount: {result["commentCount"]}')
        print(f'shareCount: {result["shareCount"]}')
    
    browser.close()