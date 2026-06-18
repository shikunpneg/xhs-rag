import sqlite3

conn = sqlite3.connect('data/xhs_notes.db')
conn.row_factory = sqlite3.Row

cursor = conn.execute("SELECT note_id, title FROM notes WHERE title LIKE ? OR content LIKE ?", ('%贾浅浅%', '%贾浅浅%'))
results = cursor.fetchall()

print('贾浅浅相关笔记:')
for i, r in enumerate(results, 1):
    print(f'{i}. {r["title"][:80]}')

conn.close()
