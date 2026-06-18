import sqlite3

conn = sqlite3.connect('data/xhs_notes.db')
cursor = conn.cursor()

cursor.execute("SELECT note_id, title, SUBSTR(content, 1, 100) FROM notes WHERE title LIKE '%贾浅浅%'")
rows = cursor.fetchall()

print('贾浅浅相关笔记:')
for r in rows:
    print(f'\nID: {r[0]}')
    print(f'Title: {r[1]}')
    print(f'Content: {r[2][:100]}')

conn.close()
