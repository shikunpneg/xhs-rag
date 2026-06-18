import sqlite3

conn = sqlite3.connect('data/xhs_notes.db')
conn.row_factory = sqlite3.Row

cursor = conn.execute("SELECT user_id, COUNT(*) as cnt FROM notes GROUP BY user_id ORDER BY cnt DESC")
print('数据库中的用户:')
for row in cursor.fetchall():
    print(f'  {row["user_id"]}: {row["cnt"]} 篇笔记')

cursor = conn.execute("SELECT DISTINCT url FROM notes WHERE url LIKE '%explore%' LIMIT 5")
print('\n示例URL:')
for row in cursor.fetchall():
    print(f'  {row["url"]}')

conn.close()
