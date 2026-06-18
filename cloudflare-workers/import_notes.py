#!/usr/bin/env python
"""
批量导入笔记到Cloudflare Vectorize
在本地使用sentence-transformers生成中文嵌入
"""

import os
import sys
import json
import time
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import requests
except ImportError:
    print("请先安装requests: pip install requests")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
    MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print('[OK] 加载语义嵌入模型: paraphrase-multilingual-MiniLM-L12-v2')
except ImportError:
    print("请先安装sentence-transformers: pip install sentence-transformers")
    sys.exit(1)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'xhs_notes.db')
API_BASE = 'https://xhs-rag.ok2442504.workers.dev'


def generate_embedding(text):
    return MODEL.encode(text).tolist()


def load_notes_from_db():
    if not os.path.exists(DB_PATH):
        print(f'数据库文件不存在: {DB_PATH}')
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT note_id, title, content, url, user_id as author, nickname, 
               liked_count, collected_count, publish_time, created_at
        FROM notes
    ''')
    
    notes = []
    for row in cursor.fetchall():
        notes.append({
            'note_id': row['note_id'],
            'title': row['title'] or '',
            'content': row['content'] or '',
            'url': row['url'] or '',
            'author': row['author'] or '',
        })
    
    conn.close()
    print(f'从数据库加载了 {len(notes)} 篇笔记')
    return notes


def batch_add_notes_with_embeddings(notes, batch_size=5):
    success = 0
    failed = 0
    errors = []
    
    for i in range(0, len(notes), batch_size):
        batch = notes[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(notes) + batch_size - 1) // batch_size
        
        print(f'\n处理批次 {batch_num}/{total_batches} ({len(batch)} 条笔记)')
        
        try:
            notes_with_embeddings = []
            for note in batch:
                content = note["content"] or ''
                truncated_content = content[:2000]
                text_to_embed = f'{note["title"]}\n\n{truncated_content}'
                embedding = generate_embedding(text_to_embed)
                notes_with_embeddings.append({
                    'note_id': note['note_id'],
                    'title': note['title'],
                    'content': truncated_content,
                    'url': note['url'],
                    'author': note['author'],
                    'embedding': embedding,
                })
            
            response = requests.post(
                f'{API_BASE}/api/notes/batch-with-embedding',
                json={'notes': notes_with_embeddings},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('successful'):
                    success += result['successful']
                    print(f'  ✅ 成功添加 {result["successful"]}/{len(batch)} 条')
                if result.get('results'):
                    for r in result['results']:
                        if not r['success']:
                            failed += 1
                            errors.append({'note_id': r['note_id'], 'error': r['error']})
            else:
                print(f'  ❌ 请求失败: {response.status_code} - {response.text}')
                failed += len(batch)
                
        except Exception as e:
            print(f'  ❌ 批次 {batch_num} 请求失败: {e}')
            failed += len(batch)
        
        time.sleep(0.5)
    
    return {'success': success, 'failed': failed, 'errors': errors}


def main():
    print('================================')
    print('笔记批量导入工具（本地中文嵌入）')
    print('================================\n')
    
    print('检查API连接...')
    try:
        response = requests.get(f'{API_BASE}/health', timeout=10)
        if response.status_code == 200:
            print('✅ API已连接\n')
        else:
            raise Exception(f'API返回错误状态: {response.status_code}')
    except Exception as e:
        print(f'❌ API连接失败: {e}')
        print('\n请确保：')
        print('1. Cloudflare Worker已部署')
        print(f'2. API地址正确: {API_BASE}\n')
        sys.exit(1)
    
    notes = load_notes_from_db()
    
    if not notes:
        print('没有找到可导入的笔记')
        sys.exit(0)
    
    print('\n即将导入的笔记预览：')
    for i, note in enumerate(notes[:5], 1):
        print(f'  {i}. {note["title"][:50]}...')
    if len(notes) > 5:
        print(f'  ... 还有 {len(notes) - 5} 条')
    
    print('\n开始导入（本地生成中文嵌入）...\n')
    results = batch_add_notes_with_embeddings(notes)
    
    print('\n================================')
    print('导入完成！')
    print(f'✅ 成功: {results["success"]}')
    print(f'❌ 失败: {results["failed"]}')
    
    if results['errors']:
        print('\n错误详情：')
        for err in results['errors'][:10]:
            print(f'  - {err["note_id"]}: {err["error"]}')
    print('================================')


if __name__ == '__main__':
    main()
