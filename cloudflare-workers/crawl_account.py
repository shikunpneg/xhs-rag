#!/usr/bin/env python
"""
小红书账号自动爬取脚本
爬取指定小红书账号的所有笔记，保存到数据库并自动导入到Vectorize
"""

import os
import sys
import json
import time
import sqlite3
import requests
import logging
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

load_dotenv()

# 配置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class XHSCrawler:
    """小红书爬虫"""

    def __init__(self, cookie: str = ''):
        self.cookie = cookie or os.getenv('XHS_COOKIE', '')
        self.playwright = None
        self.browser = None
        self.page = None

    def _init_browser(self):
        """初始化浏览器"""
        logger.info('🌐 正在初始化浏览器...')
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.error('❌ Playwright未安装')
            raise RuntimeError('Playwright未安装，请运行: pip install playwright')
        
        try:
            self.playwright = sync_playwright().start()
            logger.info('  ✅ Playwright启动成功')
            
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            logger.info('  ✅ 浏览器启动成功')
            
            self.page = self.browser.new_page()
            logger.info('  ✅ 页面创建成功')
            
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
                logger.info(f'  ✅ 已加载 {len(cookies)} 个Cookie')
            else:
                logger.warning('  ⚠️ 未提供Cookie，可能无法获取完整内容')
                
        except Exception as e:
            logger.error(f'❌ 浏览器初始化失败: {e}')
            raise

    def crawl_user_notes(self, user_id: str, max_notes: int = 50) -> List[Dict[str, Any]]:
        """爬取用户笔记"""
        all_notes = []
        
        try:
            logger.info(f'\n📖 开始爬取账号: {user_id}')
            logger.info(f'🎯 目标数量: {max_notes} 篇')
            
            self._init_browser()
            
            url = f'https://www.xiaohongshu.com/user/profile/{user_id}'
            logger.info(f'🔗 访问用户主页: {url}')
            
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            logger.info('  ✅ 页面加载完成')
            time.sleep(3)

            note_list = self._extract_note_list(max_notes)
            
            logger.info(f'\n📋 获取到 {len(note_list)} 篇笔记列表')
            
            for i, note in enumerate(note_list):
                logger.info(f'\n[{i+1}/{len(note_list)}] 正在获取笔记详情: {note["title"][:30]}...')
                logger.info(f'  📝 笔记ID: {note["note_id"]}')
                logger.info(f'  🔗 URL: {note["url"]}')
                
                try:
                    full_content = self._get_note_detail(note['note_id'])
                    note['content'] = full_content
                    note['user_id'] = user_id
                    
                    if full_content:
                        logger.info(f'  ✅ 内容长度: {len(full_content)} 字符')
                        logger.info(f'  📄 内容预览: {full_content[:100]}...')
                    else:
                        logger.warning(f'  ⚠️ 内容为空')
                        
                except Exception as e:
                    logger.error(f'  ❌ 获取详情失败: {e}')
                    note['content'] = ''
                
                all_notes.append(note)
            
            logger.info(f'\n🎉 共获取 {len(all_notes)} 篇笔记')
            return all_notes
            
        except Exception as e:
            logger.error(f'\n❌ 爬取失败: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return all_notes
        finally:
            self.close()

    def _extract_note_list(self, max_notes: int) -> List[Dict[str, Any]]:
        """提取笔记列表"""
        notes = []
        seen_ids = set()
        scroll_count = 0
        
        logger.info('🔍 开始提取笔记列表...')
        
        while len(notes) < max_notes:
            scroll_count += 1
            logger.info(f'  📜 滚动加载第 {scroll_count} 次 (已获取 {len(notes)}/{max_notes})')
            
            try:
                current_notes = self.page.evaluate("""
                    Array.from(document.querySelectorAll('div[class*="note"], article[class*="note"], div[class*="feed-item"]')).map(item => {
                        const link = item.querySelector('a');
                        if (!link) return null;
                        
                        const href = link.getAttribute('href');
                        const match = href.match(/explore\\/(\\w+)/) || href.match(/note\\/(\\w+)/);
                        if (!match) return null;
                        
                        const noteId = match[1];
                        const title = item.querySelector('[class*="title"], [class*="desc"], span[class*="name"]')?.textContent || '';
                        const cover = item.querySelector('img')?.getAttribute('src') || '';
                        
                        return {
                            note_id: noteId,
                            title: title.trim().substring(0, 150),
                            url: 'https://www.xiaohongshu.com' + href,
                            cover_url: cover
                        };
                    }).filter(note => note !== null);
                """)
                
                logger.info(f'  📊 当前页面找到 {len(current_notes)} 个笔记元素')
                
                new_count = 0
                for note in current_notes:
                    if note['note_id'] not in seen_ids:
                        seen_ids.add(note['note_id'])
                        notes.append(note)
                        new_count += 1
                        logger.info(f'  ✅ 新发现: {note["title"][:40]}... (ID: {note["note_id"]})')
                
                if new_count == 0:
                    logger.warning('  ⚠️ 未发现新笔记，停止滚动')
                    break
                
                if len(notes) >= max_notes:
                    logger.info(f'  ✅ 已达到目标数量 {max_notes}')
                    break
                
                self.page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
                time.sleep(2)
                
            except Exception as e:
                logger.error(f'  ❌ 提取笔记列表失败: {e}')
                break
        
        logger.info(f'📋 笔记列表提取完成，共 {len(notes)} 篇')
        return notes[:max_notes]

    def _get_note_detail(self, note_id: str) -> str:
        """获取笔记详情页的完整正文"""
        url = f'https://www.xiaohongshu.com/explore/{note_id}'
        
        try:
            logger.info(f'  🔗 访问详情页: {url}')
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            logger.info('  ✅ 页面加载完成')
            time.sleep(3)
            
            # 尝试点击"阅读全文"按钮
            logger.info('  🔍 检查是否有展开内容按钮...')
            try:
                expand_button = self.page.query_selector('button:has-text("阅读全文"), div:has-text("阅读全文"), [class*="expand"]')
                if expand_button:
                    expand_button.click()
                    time.sleep(1)
                    logger.info('  ✅ 已点击展开按钮')
            except Exception as e:
                logger.warning(f'  ⚠️ 展开内容失败: {e}')
            
            # 方法1：尝试查找主要内容元素（小红书详情页专用选择器）
            logger.info('  🔍 尝试方法1: 查找主要内容元素...')
            content = self.page.evaluate("""
                // 小红书详情页的多种可能选择器
                const selectors = [
                    '.detail-content',
                    '.note-content',
                    '[class*="content"]',
                    'article',
                    '.note-detail',
                    '[class*="desc"]',
                    '.main-content',
                    '[class*="body"]',
                    '#detail-desc',
                    '.content-wrapper',
                    '[class*="rich-text"]',
                    '.post-content',
                    '.entry-content',
                ];
                
                let contentElement = null;
                for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent.trim().length > 50) {
                        contentElement = el;
                        break;
                    }
                }
                
                if (contentElement) {
                    return contentElement.textContent.trim();
                }
                return '';
            """)
            
            if content and len(content) >= 30:
                logger.info(f'  ✅ 方法1成功，获取 {len(content)} 字符')
                return content[:5000]
            
            logger.warning('  ⚠️ 方法1失败，尝试方法2...')
            
            # 方法2：查找所有段落和文本元素
            logger.info('  🔍 尝试方法2: 查找所有段落和文本元素...')
            content = self.page.evaluate("""
                const allTexts = [];
                const skipKeywords = ['ICP备', '营业执照', '增值电信', '沪公网安备', '小红书', 'Copyright', 'APP', '扫码', '打开小红书'];
                
                document.querySelectorAll('p, span, div, section, article').forEach(el => {
                    const text = el.textContent.trim();
                    const shouldSkip = skipKeywords.some(keyword => text.includes(keyword));
                    if (text.length > 30 && !shouldSkip && text.length < 2000) {
                        allTexts.push(text);
                    }
                });
                
                const uniqueTexts = [...new Set(allTexts)];
                return uniqueTexts.join('\\n');
            """)
            
            if content and len(content) >= 30:
                logger.info(f'  ✅ 方法2成功，获取 {len(content)} 字符')
                return content[:5000]
            
            logger.warning('  ⚠️ 方法2失败，尝试方法3...')
            
            # 方法3：检查页面状态
            logger.info('  🔍 尝试方法3: 检查页面状态...')
            page_state = self.page.evaluate("""
                const bodyText = document.body.textContent.trim();
                
                if (bodyText.includes('登录') && bodyText.includes('查看完整内容')) {
                    return 'LOGIN_REQUIRED';
                }
                
                if (bodyText.includes('暂无内容') || bodyText.includes('无法查看')) {
                    return 'NO_CONTENT';
                }
                
                return 'CONTENT_FOUND';
            """)
            
            if page_state == 'LOGIN_REQUIRED':
                logger.warning('  ⚠️ 需要登录才能查看完整内容')
                title = self.page.evaluate("document.title")
                return title
            elif page_state == 'NO_CONTENT':
                logger.warning('  ⚠️ 笔记内容不可见')
                return ''
            
            # 方法4：获取页面所有文本
            logger.info('  🔍 尝试方法4: 获取页面所有文本...')
            content = self.page.evaluate("""
                const bodyText = document.body.textContent.trim();
                const lines = bodyText.split('\\n').filter(line => 
                    line.length > 20 && 
                    !line.includes('ICP备') && 
                    !line.includes('营业执照') &&
                    !line.includes('增值电信') &&
                    !line.includes('沪公网安备') &&
                    !line.includes('打开小红书App')
                );
                return lines.join('\\n');
            """)
            
            if content:
                logger.info(f'  ✅ 方法4获取 {len(content)} 字符')
                return content[:5000]
            
            logger.error('  ❌ 所有方法都失败，无法获取内容')
            return ''
            
        except Exception as e:
            logger.error(f'  ❌ 获取详情失败: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return ''

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

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv('DB_PATH', '../data/xhs_notes.db')
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
        logger.info(f'\n💾 开始保存 {len(notes)} 篇笔记到数据库...')
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        saved_count = 0
        for note in notes:
            try:
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
                    note.get('content', ''),
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
                saved_count += 1
            except Exception as e:
                logger.error(f'  ❌ 保存笔记失败 (ID: {note.get("note_id")}): {e}')

        self.conn.commit()
        logger.info(f'✅ 已保存 {saved_count}/{len(notes)} 篇笔记到数据库')

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """获取所有笔记"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM notes')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_notes_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """获取指定用户的笔记"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM notes WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


class VectorizeImporter:
    """Vectorize导入器"""

    def __init__(self, api_base: str = None):
        self.api_base = api_base or os.getenv('API_BASE', 'https://xhs-rag.ok2442504.workers.dev')

    def import_notes(self, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """导入笔记到Vectorize"""
        logger.info(f'\n📤 开始导入 {len(notes)} 篇笔记到Vectorize...')
        logger.info(f'🌐 API地址: {self.api_base}')
        
        try:
            logger.info('  📡 发送请求...')
            response = requests.post(
                f'{self.api_base}/api/notes/batch',
                json={'notes': notes},
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=60
            )
            
            logger.info(f'  📊 HTTP状态: {response.status_code}')
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f'  ✅ 导入成功: {result.get("successful", 0)} 篇')
                return result
            else:
                logger.error(f'  ❌ 导入失败: HTTP {response.status_code}')
                logger.error(f'  📄 响应内容: {response.text[:500]}')
                return {'success': False, 'error': f'HTTP {response.status_code}', 'message': response.text}
                
        except Exception as e:
            logger.error(f'  ❌ 请求异常: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}

    def health_check(self) -> bool:
        """检查API是否可用"""
        logger.info(f'🔍 检查API连接: {self.api_base}')
        try:
            response = requests.get(f'{self.api_base}/health', timeout=10)
            if response.status_code == 200:
                logger.info('  ✅ API连接正常')
                return True
            else:
                logger.warning(f'  ⚠️ API返回异常状态: {response.status_code}')
                return False
        except Exception as e:
            logger.error(f'  ❌ API连接失败: {e}')
            return False


def main():
    """主函数"""
    print('=' * 70)
    print('📚 小红书账号自动爬取工具')
    print('=' * 70)
    print()
    
    user_id = input('请输入小红书账号ID: ').strip()
    if not user_id:
        logger.error('❌ 账号ID不能为空')
        return
    
    max_notes = input('请输入最大爬取数量 (默认50): ').strip()
    max_notes = int(max_notes) if max_notes.isdigit() else 50
    
    cookie = os.getenv('XHS_COOKIE', '')
    if not cookie:
        logger.warning('⚠️ 未设置XHS_COOKIE环境变量，可能无法获取完整内容')
        logger.info('💡 建议在.env文件中设置XHS_COOKIE')
        print()
    
    logger.info(f'\n🚀 开始爬取任务')
    logger.info(f'👤 账号ID: {user_id}')
    logger.info(f'🎯 目标数量: {max_notes}')
    logger.info(f'🍪 Cookie状态: {"已设置" if cookie else "未设置"}')
    print('=' * 70)
    
    crawler = XHSCrawler(cookie)
    storage = DataStorage()
    importer = VectorizeImporter()
    
    try:
        logger.info('\n📌 第1步: 爬取小红书笔记')
        notes = crawler.crawl_user_notes(user_id, max_notes)
        
        if not notes:
            logger.error('\n❌ 未获取到任何笔记，请检查账号ID是否正确')
            return
        
        logger.info(f'\n📌 第2步: 保存到本地数据库')
        storage.save_notes(notes)
        
        logger.info(f'\n📌 第3步: 检查API连接')
        if importer.health_check():
            logger.info(f'\n📌 第4步: 导入到Vectorize')
            result = importer.import_notes(notes)
            
            if result.get('success'):
                successful = result.get('successful', 0)
                total = result.get('total', 0)
                logger.info(f'  ✅ 导入成功: {successful}/{total}')
            else:
                logger.error(f'  ❌ 导入失败: {result.get("error", "未知错误")}')
        else:
            logger.warning('  ⚠️ API不可用，跳过Vectorize导入')
            logger.info('  💡 笔记已保存到本地数据库，可以稍后手动导入')
        
        logger.info('\n' + '=' * 70)
        logger.info('🎉 爬取任务完成！')
        logger.info(f'📊 共获取 {len(notes)} 篇笔记')
        logger.info(f'📁 本地数据库: {storage.db_path}')
        logger.info(f'🌐 API地址: {importer.api_base}')
        logger.info('=' * 70)
        
    except Exception as e:
        logger.error(f'\n❌ 运行出错: {e}')
        import traceback
        logger.error(traceback.format_exc())
    finally:
        storage.close()


if __name__ == '__main__':
    main()
