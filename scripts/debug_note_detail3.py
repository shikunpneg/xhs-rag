"""调试笔记详情页数据结构 - noteDetailMap.note"""
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
        
        if (!state || !state.note || !state.note.noteDetailMap) {
            return {error: 'noteDetailMap not found'};
        }
        
        let map = state.note.noteDetailMap;
        if (map._value !== undefined) map = map._value;
        if (map._rawValue !== undefined) map = map._rawValue;
        
        const keys = Object.keys(map);
        if (keys.length === 0) {
            return {error: 'noteDetailMap is empty'};
        }
        
        const noteData = map[keys[0]];
        if (!noteData || !noteData.note) {
            return {error: 'note not found in map'};
        }
        
        const note = noteData.note;
        let data = note;
        if (data._value !== undefined) data = data._value;
        if (data._rawValue !== undefined) data = data._rawValue;
        
        const dataKeys = Object.keys(data).slice(0, 40);
        
        return {
            mapKeys: keys,
            dataKeys: dataKeys,
            desc: data.desc || 'NOT FOUND',
            descLength: data.desc ? data.desc.length : 0,
            title: data.title || data.displayTitle || 'NOT FOUND',
            likedCount: data.liked_count || (data.interactInfo && data.interactInfo.likedCount) || 0,
            commentCount: data.comment_count || (data.interactInfo && data.interactInfo.commentCount) || 0,
            shareCount: data.share_count || (data.interactInfo && data.interactInfo.shareCount) || 0,
            hasContent: !!data.content,
            contentKeys: data.content ? Object.keys(data.content).slice(0, 10) : [],
            hasImages: !!data.images,
            imagesLength: data.images && Array.isArray(data.images) ? data.images.length : 0,
        };
    })()""")
    
    print('\n=== noteDetailMap.note 数据结构 ===')
    if result.get('error'):
        print(f'错误: {result["error"]}')
    else:
        print(f'map键: {result["mapKeys"]}')
        print(f'data键: {result["dataKeys"]}')
        print(f'desc长度: {result["descLength"]}')
        print(f'desc: {result["desc"][:300]}')
        print(f'title: {result["title"][:50]}')
        print(f'likedCount: {result["likedCount"]}')
        print(f'commentCount: {result["commentCount"]}')
        print(f'shareCount: {result["shareCount"]}')
        print(f'hasContent: {result["hasContent"]}')
        print(f'content键: {result["contentKeys"]}')
        print(f'hasImages: {result["hasImages"]}')
        print(f'imagesLength: {result["imagesLength"]}')
    
    browser.close()