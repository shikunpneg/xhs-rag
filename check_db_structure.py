import sqlite3

conn = sqlite3.connect('data/xhs_notes.db')

cursor = conn.execute("SELECT note_id, title, content, cover_url FROM notes LIMIT 5")
print('示例数据:')
for row in cursor.fetchall():
    print(f'\n笔记ID: {row[0]}')
    print(f'标题: {row[1]}')
    print(f'content长度: {len(row[2]) if row[2] else 0}')
    print(f'content前200字符: {repr(row[2][:200]) if row[2] else "空"}')
    print(f'cover_url: {repr(row[3])}')

cursor = conn.execute("SELECT COUNT(*) FROM notes WHERE content IS NOT NULL AND content != ''")
non_empty_count = cursor.fetchone()[0]

cursor = conn.execute("SELECT COUNT(*) FROM notes")
total_count = cursor.fetchone()[0]

print(f'\n数据库统计:')
print(f'  总笔记数: {total_count}')
print(f'  content非空: {non_empty_count}')
print(f'  content为空: {total_count - non_empty_count}')

conn.close()
