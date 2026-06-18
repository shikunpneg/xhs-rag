"""调试笔记详情页 - 通过页面元素提取"""
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
        const selectors = [
            '[class*="note-content"]',
            '[class*="description"]',
            '[class*="detail-content"]',
            '[class*="desc"]',
            '[class*="post-content"]',
            '[class*="article-content"]',
            '.content',
            '.main-content',
            '#app',
        ];
        
        let foundContent = '';
        
        for (const selector of selectors) {
            const els = document.querySelectorAll(selector);
            for (const el of els) {
                const text = el.textContent.trim();
                if (text.length > 50 && 
                    !text.includes('ICP备') && 
                    !text.includes('营业执照') && 
                    !text.includes('行吟信息') &&
                    !text.includes('小红书') &&
                    !text.includes('关于我们') &&
                    !text.includes('帮助中心')) {
                    foundContent = text;
                    break;
                }
            }
            if (foundContent) break;
        }
        
        const titleSelectors = [
            '[class*="title"]',
            'h1',
            'h2',
            '.title',
        ];
        
        let foundTitle = '';
        for (const selector of titleSelectors) {
            const els = document.querySelectorAll(selector);
            for (const el of els) {
                const text = el.textContent.trim();
                if (text.length > 5 && text.length < 100) {
                    foundTitle = text;
                    break;
                }
            }
            if (foundTitle) break;
        }
        
        return {
            content: foundContent.slice(0, 500),
            contentLength: foundContent.length,
            title: foundTitle,
        };
    })()""")
    
    print('\n=== 页面元素提取结果 ===')
    print(f'标题: {result["title"]}')
    print(f'内容长度: {result["contentLength"]}')
    print(f'内容: {result["content"][:300]}')
    
    browser.close()