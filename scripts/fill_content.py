"""
补全笔记内容脚本
直接访问已有笔记的详情页获取完整正文
"""

import os
import time
import sqlite3
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()


class NoteContentFiller:
    """补全笔记内容"""

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

    def fill_missing_content(self, db_path: str, batch_size: int = 10):
        """补全缺失的笔记内容"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT note_id, title, url FROM notes WHERE content IS NULL OR content = '' ORDER BY RANDOM()")
        notes_to_fill = cursor.fetchall()
        
        print(f'发现 {len(notes_to_fill)} 篇内容为空的笔记')
        
        if not notes_to_fill:
            print('没有需要补全的笔记')
            conn.close()
            return
        
        try:
            self._init_browser()
            
            success_count = 0
            fail_count = 0
            
            for i, note in enumerate(notes_to_fill, 1):
                print(f'\n[{i}/{len(notes_to_fill)}] 正在获取: {note["title"][:30]}...')
                print(f'  URL: {note["url"]}')
                
                try:
                    content = self._get_note_detail(note['note_id'])
                    
                    if content and len(content) > 20:
                        conn.execute('UPDATE notes SET content = ?, updated_at = ? WHERE note_id = ?', 
                                   (content, datetime.now().isoformat(), note['note_id']))
                        conn.commit()
                        success_count += 1
                        print(f'  ✅ 获取成功，内容长度: {len(content)}')
                    else:
                        print(f'  ⚠️ 内容过短或为空')
                        fail_count += 1
                        
                except Exception as e:
                    print(f'  ❌ 获取失败: {e}')
                    fail_count += 1
                
                if i % batch_size == 0:
                    time.sleep(5)
                    print(f'  休息5秒...')
            
            print(f'\n补全完成！')
            print(f'✅ 成功: {success_count}')
            print(f'❌ 失败: {fail_count}')
            
        finally:
            self.close()
            conn.close()

    def _get_note_detail(self, note_id: str) -> str:
        """获取笔记详情页的完整正文"""
        url = f'https://www.xiaohongshu.com/explore/{note_id}'
        
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            
            content = self.page.evaluate("(() => { const contentEls = document.querySelectorAll('[class*=\"note-content\"], [class*=\"description\"], [class*=\"detail-content\"]'); if (contentEls.length > 0) { return contentEls[0].textContent.trim(); } const article = document.querySelector('article'); if (article) { return article.textContent.trim(); } const main = document.querySelector('main'); if (main) { return main.textContent.trim(); } return ''; })()")
            
            if not content or len(content) < 50 or content.includes('ICP备') or content.includes('营业执照'):
                self.page.wait_for_timeout(3000)
                
                content = self.page.evaluate("(() => { const textNodes = []; document.querySelectorAll('section, div[role=\"main\"], .post-content, .note-detail').forEach(el => { const text = el.textContent.trim(); if (text.length > 50 && !text.includes('ICP备') && !text.includes('营业执照') && !text.includes('行吟信息')) { textNodes.push(text); } }); return textNodes.join('\\n\\n'); })()")
            
            if len(content) > 5000:
                content = content[:5000]
            
            return content
            
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
    db_path = os.getenv('DB_PATH', './data/xhs_notes.db')
    
    cookie = os.getenv('XHS_COOKIE', '')
    if not cookie:
        print('警告: 未提供Cookie，可能无法获取完整内容')
    
    filler = NoteContentFiller(cookie)
    filler.fill_missing_content(db_path, batch_size=10)


if __name__ == '__main__':
    main()
