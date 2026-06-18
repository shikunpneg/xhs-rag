"""
重新获取贾浅浅相关笔记的真实内容
"""

import os
import time
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()


class JiaQianQianCrawler:
    """专门爬取贾浅浅相关笔记"""

    def __init__(self, cookie: str = ''):
        self.cookie = cookie or os.getenv('XHS_COOKIE', '')
        self.playwright = None
        self.browser = None
        self.page = None

    def _init_browser(self):
        """初始化浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        self.page = self.browser.new_page()
        
        if self.cookie:
            cookies = []
            for cookie in self.cookie.split(';'):
                cookie = cookie.strip()
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.xiaohongshu.com',
                        'path': '/'
                    })
            self.page.context.add_cookies(cookies)

    def crawl_jiaqianqian_notes(self):
        """爬取贾浅浅相关笔记"""
        conn = sqlite3.connect('./data/xhs_notes.db')
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT note_id, title, url FROM notes WHERE title LIKE '%贾浅浅%'")
        notes = cursor.fetchall()
        
        print(f'发现 {len(notes)} 篇贾浅浅相关笔记')
        
        if not notes:
            print('没有找到贾浅浅相关笔记')
            conn.close()
            return
        
        try:
            self._init_browser()
            
            for i, note in enumerate(notes, 1):
                print(f'\n[{i}/{len(notes)}] 正在获取: {note["title"]}')
                print(f'  URL: {note["url"]}')
                
                try:
                    content = self._get_real_content(note['note_id'])
                    
                    if content and len(content) > 50 and not content.startswith('首页'):
                        conn.execute('UPDATE notes SET content = ?, updated_at = ? WHERE note_id = ?', 
                                   (content, datetime.now().isoformat(), note['note_id']))
                        conn.commit()
                        print(f'  ✅ 获取成功，内容长度: {len(content)}')
                        print(f'  内容预览: {content[:100]}...')
                    else:
                        print(f'  ⚠️ 内容无效')
                        
                except Exception as e:
                    print(f'  ❌ 获取失败: {e}')
            
            conn.commit()
            
        finally:
            self.close()
            conn.close()

    def _get_real_content(self, note_id: str) -> str:
        """获取笔记真实内容"""
        url = f'https://www.xiaohongshu.com/explore/{note_id}'
        
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(4)
            
            content = self.page.evaluate("""
                (() => {
                    let result = '';
                    const selectors = [
                        '[class*="note-detail-content"]',
                        '[class*="note-text"]', 
                        '[class*="detail-text"]',
                        '.rich-text',
                        '.note-content',
                        '[data-note-content]',
                        'div[class*="content"] p'
                    ];
                    
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const text = el.textContent.trim();
                            if (text.length > 50 && !text.includes('ICP备')) {
                                result = text;
                                break;
                            }
                        }
                    }
                    
                    if (!result) {
                        const paragraphs = document.querySelectorAll('p');
                        const texts = [];
                        paragraphs.forEach(p => {
                            const text = p.textContent.trim();
                            if (text.length > 30 && !text.includes('ICP备') && !text.includes('营业执照')) {
                                texts.push(text);
                            }
                        });
                        result = texts.join('\\n');
                    }
                    
                    return result;
                })()
            """)
            
            return content[:5000]
            
        except Exception as e:
            raise e

    def close(self):
        """关闭浏览器"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


def main():
    cookie = os.getenv('XHS_COOKIE', '')
    if not cookie:
        print('警告: 未提供Cookie')
    
    crawler = JiaQianQianCrawler(cookie)
    crawler.crawl_jiaqianqian_notes()


if __name__ == '__main__':
    main()
