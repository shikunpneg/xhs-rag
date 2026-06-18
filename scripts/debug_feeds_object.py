"""调试feeds对象结构"""
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
    
    page.goto('https://www.xiaohongshu.com', wait_until='networkidle', timeout=60000)
    time.sleep(15)
    
    result = page.evaluate("""(() => {
        const state = window.__INITIAL_STATE__;
        
        if (!state || !state.feed || !state.feed.feeds) {
            return {error: 'feeds not found'};
        }
        
        const feeds = state.feed.feeds;
        const keys = Object.keys(feeds);
        
        let hasNoteCard = false;
        let sampleNote = null;
        
        for (let i = 0; i < keys.length && !hasNoteCard; i++) {
            const key = keys[i];
            const val = feeds[key];
            if (val && val.noteCard) {
                hasNoteCard = true;
                const card = val.noteCard;
                sampleNote = {
                    noteId: card.noteId || card.note_id || '',
                    displayTitle: card.displayTitle || '',
                    hasInteractInfo: !!card.interactInfo,
                    hasCover: !!card.cover,
                    hasUser: !!card.user,
                };
            }
        }
        
        return {
            keyCount: keys.length,
            keysSample: keys.slice(0, 10),
            hasNoteCard: hasNoteCard,
            sampleNote: sampleNote,
        };
    })()""")
    
    print(f'feeds对象键数量: {result["keyCount"]}')
    print(f'前10个键: {result["keysSample"]}')
    print(f'是否包含noteCard: {result["hasNoteCard"]}')
    
    if result['sampleNote']:
        print(f'\n示例笔记:')
        print(f'  noteId: {result["sampleNote"]["noteId"]}')
        print(f'  displayTitle: {result["sampleNote"]["displayTitle"][:50]}')
        print(f'  hasInteractInfo: {result["sampleNote"]["hasInteractInfo"]}')
        print(f'  hasCover: {result["sampleNote"]["hasCover"]}')
        print(f'  hasUser: {result["sampleNote"]["hasUser"]}')
    
    browser.close()