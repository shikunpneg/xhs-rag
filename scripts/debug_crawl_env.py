"""调试爬虫环境中的页面状态"""
import os
import sys
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

cookie = os.getenv('XHS_COOKIE')

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
        print(f'已加载 {len(cookies)} 个Cookie')
    
    print('\n=== 访问小红书主页 ===')
    page.goto('https://www.xiaohongshu.com', wait_until='networkidle', timeout=60000)
    print(f'页面URL: {page.url}')
    
    print('\n等待15秒...')
    time.sleep(15)
    
    print('\n=== 检查INITIAL_STATE ===')
    result = page.evaluate("""(() => {
        const state = window.__INITIAL_STATE__;
        
        return {
            stateExists: !!state,
            feedExists: !!state && !!state.feed,
            feedsExists: !!state && !!state.feed && !!state.feed.feeds,
            feedsType: state && state.feed && state.feed.feeds ? typeof state.feed.feeds : 'N/A',
            feedsIsArray: state && state.feed && state.feed.feeds ? Array.isArray(state.feed.feeds) : false,
            feedsLength: state && state.feed && state.feed.feeds && Array.isArray(state.feed.feeds) ? state.feed.feeds.length : 0,
            firstItem: state && state.feed && state.feed.feeds && Array.isArray(state.feed.feeds) && state.feed.feeds.length > 0 
                ? JSON.stringify(state.feed.feeds[0]).slice(0, 500) : null,
        };
    })()""")
    
    print(f'stateExists: {result["stateExists"]}')
    print(f'feedExists: {result["feedExists"]}')
    print(f'feedsExists: {result["feedsExists"]}')
    print(f'feedsType: {result["feedsType"]}')
    print(f'feedsIsArray: {result["feedsIsArray"]}')
    print(f'feedsLength: {result["feedsLength"]}')
    
    if result['firstItem']:
        print(f'\n第一个元素: {result["firstItem"]}')
    
    print('\n=== 尝试提取笔记 ===')
    notes = page.evaluate("""(() => {
        const notes = [];
        const state = window.__INITIAL_STATE__;
        
        if (!state || !state.feed || !state.feed.feeds) return notes;
        
        const feeds = state.feed.feeds;
        if (!Array.isArray(feeds)) return notes;
        
        for (let i = 0; i < feeds.length; i++) {
            const feedItem = feeds[i];
            if (!feedItem || !feedItem.noteCard) continue;
            
            const card = feedItem.noteCard;
            
            notes.push({
                note_id: card.noteId || card.note_id || '',
                title: card.displayTitle || card.title || card.desc || '',
            });
        }
        
        return notes;
    })()""")
    
    print(f'提取到 {len(notes)} 篇笔记')
    for note in notes[:5]:
        print(f'  - {note["note_id"]}: {note["title"][:50]}')
    
    browser.close()