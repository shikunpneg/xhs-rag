"""
小红书数据采集脚本
通过搜索和页面数据提取获取笔记数据
"""

import os
import sys
import json
import sqlite3
import time
import random
import logging
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class XHSCrawler:
    """小红书数据采集器"""

    def __init__(self, cookie: str):
        self.cookie = cookie
        self.playwright = None
        self.browser = None
        self.page = None

    def _init_browser(self):
        """初始化浏览器"""
        from playwright.sync_api import sync_playwright
        
        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch(
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
        
        self.page = self.browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

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
            logger.info(f'已加载 {len(cookies)} 个Cookie')

    def close(self):
        """关闭浏览器"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def _random_delay(self, min_sec: float = 1, max_sec: float = 3):
        """随机延迟"""
        time.sleep(random.uniform(min_sec, max_sec))

    def _scroll_page(self):
        """模拟人类滚动"""
        for _ in range(3):
            self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.3)')
            self._random_delay(0.5, 1)

    def crawl_user_notes(self, user_id: str, max_notes: int = 50) -> List[Dict[str, Any]]:
        """爬取用户笔记"""
        all_notes = []
        
        try:
            self._init_browser()
            
            logger.info(f'访问小红书主页')
            self.page.goto('https://www.xiaohongshu.com', wait_until='networkidle', timeout=60000)
            logger.info(f'主页URL: {self.page.url}')
            
            logger.info('等待页面数据加载...')
            time.sleep(10)
            
            for attempt in range(5):
                logger.info(f'第 {attempt + 1} 次尝试提取主页笔记...')
                notes = self._extract_notes_from_initial_state()
                
                if notes and len(notes) > 0:
                    all_notes.extend(notes)
                    logger.info(f'✅ 获取到 {len(notes)} 篇笔记')
                    break
                
                logger.info(f'❌ 未获取到笔记，等待5秒后重试...')
                self._scroll_page()
                time.sleep(5)
            
            all_notes = list({n['note_id']: n for n in all_notes if n.get('note_id')}.values())[:max_notes]
            logger.info(f'共获取 {len(all_notes)} 篇去重后的笔记')
            
            return all_notes

        finally:
            self.close()

    def _extract_notes_from_initial_state(self) -> List[Dict[str, Any]]:
        """从页面的INITIAL_STATE提取笔记"""
        try:
            notes = self.page.evaluate("""(() => {
                const notes = [];
                const state = window.__INITIAL_STATE__;
                
                if (!state) {
                    console.log('ERROR: state is null');
                    return notes;
                }
                
                let feeds = [];
                
                if (state.feed && state.feed.feeds) {
                    feeds = state.feed.feeds;
                } else if (state.explore && state.explore.feeds) {
                    feeds = state.explore.feeds;
                }
                
                if (feeds._value !== undefined) feeds = feeds._value;
                if (feeds._rawValue !== undefined) feeds = feeds._rawValue;
                
                if (!Array.isArray(feeds)) {
                    if (typeof feeds === 'object' && feeds !== null) {
                        feeds = Object.values(feeds);
                    } else {
                        console.log('ERROR: feeds is not an array');
                        return notes;
                    }
                }
                
                console.log('SUCCESS: feeds length:', feeds.length);
                
                for (let i = 0; i < feeds.length; i++) {
                    const feedItem = feeds[i];
                    if (!feedItem) continue;
                    
                    let card = feedItem.noteCard;
                    if (!card && feedItem.card) card = feedItem.card;
                    if (!card && feedItem.data) card = feedItem.data;
                    if (!card) continue;
                    
                    notes.push({
                        note_id: feedItem.id || card.noteId || card.note_id || card.id || '',
                        title: card.displayTitle || card.title || card.desc || '',
                        desc: card.desc || '',
                        cover_url: card.cover && card.cover.infoList && card.cover.infoList[0] 
                            ? card.cover.infoList[0].url : (card.cover && card.cover.url ? card.cover.url : 
                              (card.cover && card.cover.urlDefault ? card.cover.urlDefault : '')),
                        liked_count: parseInt(card.interactInfo && card.interactInfo.likedCount) || 
                                     parseInt(card.interactInfo && card.interactInfo.liked) || 
                                     parseInt(card.liked_count) || 0,
                        comment_count: parseInt(card.interactInfo && card.interactInfo.commentCount) || 
                                       parseInt(card.comment_count) || 0,
                        share_count: parseInt(card.interactInfo && card.interactInfo.shareCount) || 
                                     parseInt(card.share_count) || 0,
                        user_id: card.user && card.user.userId ? card.user.userId : 
                                (card.user && card.user.user_id ? card.user.user_id : ''),
                        nickname: card.user && card.user.nickName ? card.user.nickName : 
                                  (card.user && card.user.nickname ? card.user.nickname : ''),
                    });
                }
                
                return notes;
            })()""")
            
            return notes
            
        except Exception as e:
            logger.error(f'提取笔记失败: {e}')
            return []

    def _get_note_content(self, note_id: str) -> str:
        """获取笔记内容"""
        url = f'https://www.xiaohongshu.com/explore/{note_id}'
        
        try:
            self.page.goto(url, wait_until='networkidle', timeout=60000)
            self._random_delay(5, 8)
            self._scroll_page()
            
            content = self.page.evaluate("""(() => {
                const state = window.__INITIAL_STATE__;
                
                if (state && state.note && state.note.data) {
                    let data = state.note.data;
                    if (data._value !== undefined) data = data._value;
                    if (data._rawValue !== undefined) data = data._rawValue;
                    
                    if (data.desc && typeof data.desc === 'string' && data.desc.length > 20) {
                        return data.desc;
                    }
                }
                
                const selectors = [
                    '[class*="note-content"]',
                    '[class*="description"]',
                    '[class*="detail-content"]',
                    '[class*="desc"]',
                    '.content',
                    '.main-content',
                    '.post-content',
                    '.article-content',
                    'article',
                    'main',
                    '#app'
                ];
                
                for (const selector of selectors) {
                    const els = document.querySelectorAll(selector);
                    for (const el of els) {
                        const text = el.textContent.trim();
                        if (text.length > 50 && !text.includes('ICP备') && !text.includes('营业执照') && !text.includes('行吟信息')) {
                            return text;
                        }
                    }
                }
                
                return '';
            })()""")
            
            return content
            
        except Exception as e:
            logger.error(f'获取笔记内容失败 {note_id}: {e}')
            return ''


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
        logger.info(f'已保存 {len(notes)} 篇笔记到数据库')

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
    parser.add_argument('--cookie', help='小红书Cookie')

    args = parser.parse_args()

    cookie = args.cookie or os.getenv('XHS_COOKIE')
    if not cookie:
        print(json.dumps({'success': False, 'error': '请提供小红书 Cookie'}, ensure_ascii=False))
        return

    crawler = XHSCrawler(cookie)
    storage = DataStorage(os.getenv('DB_PATH', './data/xhs_notes.db'))

    try:
        notes = crawler.crawl_user_notes(args.user_id, args.max_notes)

        storage.save_notes(notes)

        output_path = f'./data/notes_{args.user_id}.json'
        os.makedirs('./data', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
        
        print(json.dumps({
            'success': True,
            'total': len(notes),
            'notes': notes,
            'message': f'成功获取 {len(notes)} 篇笔记'
        }, ensure_ascii=False))

    finally:
        storage.close()


if __name__ == '__main__':
    main()