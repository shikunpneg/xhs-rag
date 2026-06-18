import sqlite3

conn = sqlite3.connect('data/xhs_notes.db')
conn.row_factory = sqlite3.Row

cursor = conn.execute("SELECT note_id, title, content FROM notes WHERE title LIKE ? OR content LIKE ?", ('%贾浅浅%', '%贾浅浅%'))
results = cursor.fetchall()

print('贾浅浅相关笔记详情:')
for i, r in enumerate(results, 1):
    content = r["content"] or ''
    print(f'\n{i}. 标题: {r["title"]}')
    print(f'   ID: {r["note_id"]}')
    print(f'   内容长度: {len(content)} 字符')
    print(f'   前500字符: {content[:500]}...')

conn.close()
