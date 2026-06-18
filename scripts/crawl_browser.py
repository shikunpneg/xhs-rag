"""
小红书数据采集脚本 - 使用 Playwright 浏览器自动化
"""

import os
import json
import time
import sqlite3
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page

load_dotenv()

class XHSBrowserCrawler:
    """使用浏览器自动化采集小红书数据"""

    def __init__(self):
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
        
        cookie_str = os.getenv('XHS_COOKIE', '')
        if cookie_str:
            cookies = []
            for cookie in cookie_str.split(';'):
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

    def crawl_user_notes(self, user_id: str, max_notes: int = 50) -> List[Dict[str, Any]]:
        """爬取用户笔记"""
        all_notes = []
        
        try:
            self._init_browser()
            
            url = f'https://www.xiaohongshu.com/user/profile/{user_id}'
            self.page.goto(url, wait_until='networkidle')
            time.sleep(3)

            all_notes = self._extract_all_notes(max_notes)
            
            print(f'共获取 {len(all_notes)} 篇笔记')
            return all_notes
            
        except Exception as e:
            print(f'爬取失败: {e}')
            import traceback
            traceback.print_exc()
            return all_notes
        finally:
            self.close()

    def _extract_all_notes(self, max_notes: int) -> List[Dict[str, Any]]:
        """提取所有笔记"""
        notes = []
        seen_ids = set()
        
        while len(notes) < max_notes:
            current_notes = self._extract_notes_from_page()
            
            new_count = 0
            for note in current_notes:
                if note['note_id'] not in seen_ids:
                    seen_ids.add(note['note_id'])
                    notes.append(note)
                    new_count += 1
            
            if new_count == 0:
                break
            
            if len(notes) >= max_notes:
                break
            
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(2)
        
        return notes[:max_notes]

    def _extract_notes_from_page(self) -> List[Dict[str, Any]]:
        """从页面提取笔记信息"""
        try:
            return self.page.evaluate("""
                Array.from(document.querySelectorAll('div[class*="note"]')).map(item => {
                    const link = item.querySelector('a');
                    if (!link) return null;
                    
                    const href = link.getAttribute('href');
                    const match = href.match(/explore\\/(\\w+)/);
                    if (!match) return null;
                    
                    const noteId = match[1];
                    const title = item.querySelector('[class*="title"], [class*="desc"]')?.textContent || '';
                    const stats = item.querySelectorAll('[class*="count"], span');
                    let likes = 0, comments = 0;
                    
                    stats.forEach(stat => {
                        const text = stat.textContent || '';
                        if (text.includes('赞')) likes = parseInt(text.replace(/[^\\d]/g, '')) || 0;
                        if (text.includes('评')) comments = parseInt(text.replace(/[^\\d]/g, '')) || 0;
                    });
                    
                    return {
                        note_id: noteId,
                        title: title.trim(),
                        desc: '',
                        url: 'https://www.xiaohongshu.com' + href,
                        liked_count: likes,
                        comment_count: comments,
                        collected_count: 0,
                        share_count: 0,
                        type: 'normal',
                        user_id: '',
                        nickname: '',
                        cover_url: ''
                    };
                }).filter(note => note !== null);
            """)
        except Exception as e:
            print(f'提取笔记失败: {e}')
            return []

    def close(self):
        """关闭浏览器"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


class DataStorage:
    """数据存储类"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                note_id TEXT PRIMARY KEY,
                user_id TEXT,
                nickname TEXT,
                title TEXT,
                content TEXT,
                note_type TEXT,
                liked_count INTEGER,
                collected_count INTEGER,
                comment_count INTEGER,
                share_count INTEGER,
                cover_url TEXT,
                url TEXT,
                publish_time TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        self.conn.commit()

    def save_notes(self, notes: List[Dict[str, Any]]):
        """批量保存笔记"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        for note in notes:
            cursor.execute('''
                INSERT OR REPLACE INTO notes
                (note_id, user_id, nickname, title, content, note_type,
                 liked_count, collected_count, comment_count, share_count,
                 cover_url, url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                note.get('note_id', ''),
                note.get('user_id', ''),
                note.get('nickname', ''),
                note.get('title', ''),
                note.get('desc', ''),
                note.get('type', 'normal'),
                note.get('liked_count', 0),
                note.get('collected_count', 0),
                note.get('comment_count', 0),
                note.get('share_count', 0),
                note.get('cover_url', ''),
                note.get('url', ''),
                now,
                now
            ))

        self.conn.commit()
        print(f'已保存 {len(notes)} 篇笔记到数据库')

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """获取所有笔记"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM notes')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='小红书数据采集')
    parser.add_argument('--user-id', default=os.getenv('XHS_USER_ID'), help='小红书用户ID')
    parser.add_argument('--max-notes', type=int, default=50, help='最大爬取笔记数')

    args = parser.parse_args()

    if not args.user_id:
        print('错误: 请提供博主 ID')
        return

    crawler = XHSBrowserCrawler()
    storage = DataStorage(os.getenv('DB_PATH', './data/xhs_notes.db'))

    try:
        notes = crawler.crawl_user_notes(args.user_id, args.max_notes)

        if not notes:
            print('警告: 未获取到任何笔记')
            return

        storage.save_notes(notes)

        output_path = f'./data/notes_{args.user_id}.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
        print(f'笔记已导出到 {output_path}')

    finally:
        storage.close()


if __name__ == '__main__':
    main()
