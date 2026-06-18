"""调试笔记数据结构"""
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
        
        let feeds = state.feed.feeds;
        if (feeds._value !== undefined) feeds = feeds._value;
        if (feeds._rawValue !== undefined) feeds = feeds._rawValue;
        
        if (!Array.isArray(feeds)) {
            return {error: 'feeds is not array'};
        }
        
        if (feeds.length === 0) {
            return {error: 'feeds is empty'};
        }
        
        const firstItem = feeds[0];
        const firstKeys = Object.keys(firstItem).slice(0, 20);
        
        let card = null;
        if (firstItem.noteCard) card = firstItem.noteCard;
        else if (firstItem.card) card = firstItem.card;
        else if (firstItem.data) card = firstItem.data;
        
        const cardKeys = card ? Object.keys(card).slice(0, 30) : [];
        
        const sampleData = {
            feedItemKeys: firstKeys,
            cardExists: !!card,
            cardKeys: cardKeys,
            noteId: card ? (card.noteId || card.note_id || card.id || card.noteIdStr || 'NOT FOUND') : 'N/A',
            displayTitle: card ? (card.displayTitle || card.title || 'NOT FOUND') : 'N/A',
            desc: card ? (card.desc || 'NOT FOUND') : 'N/A',
            interactInfoExists: card ? !!card.interactInfo : false,
            interactInfoKeys: card && card.interactInfo ? Object.keys(card.interactInfo).slice(0, 10) : [],
            coverExists: card ? !!card.cover : false,
            coverKeys: card && card.cover ? Object.keys(card.cover).slice(0, 10) : [],
            userExists: card ? !!card.user : false,
            userKeys: card && card.user ? Object.keys(card.user).slice(0, 10) : [],
        };
        
        return sampleData;
    })()""")
    
    print('=== 数据结构分析 ===')
    print(f'feedItem键: {result["feedItemKeys"]}')
    print(f'card存在: {result["cardExists"]}')
    print(f'card键: {result["cardKeys"]}')
    print(f'noteId: {result["noteId"]}')
    print(f'displayTitle: {result["displayTitle"][:50]}')
    print(f'desc: {result["desc"][:50]}')
    print(f'interactInfo存在: {result["interactInfoExists"]}')
    print(f'interactInfo键: {result["interactInfoKeys"]}')
    print(f'cover存在: {result["coverExists"]}')
    print(f'cover键: {result["coverKeys"]}')
    print(f'user存在: {result["userExists"]}')
    print(f'user键: {result["userKeys"]}')
    
    browser.close()