"""
添加贾浅浅相关测试数据
用于验证RAG检索功能
"""

import sqlite3
from datetime import datetime


def add_test_notes():
    conn = sqlite3.connect('./data/xhs_notes.db')
    conn.row_factory = sqlite3.Row
    
    test_notes = [
        {
            'note_id': 'jqz_test_001',
            'title': '贾浅浅是谁？贾平凹女儿的诗歌争议',
            'content': '贾浅浅是著名作家贾平凹的女儿，也是一位诗人。她的诗歌作品曾引发广泛争议，特别是一些描写生活细节的诗作被网友戏称为"屎尿体"。贾浅浅毕业于西北大学中文系，获得文学博士学位，现任西北大学文学院副教授。她的代表作包括《真香定律》《雪地里的长镜头》等。虽然争议不断，但贾浅浅在文学界也有一定的支持者，认为她的作品具有独特的艺术风格。',
            'user_id': 'test_user',
            'nickname': '文学评论家',
            'url': 'https://www.xiaohongshu.com/explore/jqz_test_001'
        },
        {
            'note_id': 'jqz_test_002',
            'title': '贾浅浅诗歌争议事件全梳理',
            'content': '2022年，贾浅浅的诗歌在网络上引发巨大争议。她的一些诗歌如《我的娘》《日记独白》等被认为过于直白粗俗。网友将她的作品与"屎尿体"联系起来，引发了关于诗歌审美标准的大讨论。尽管争议不断，贾浅浅仍然坚持自己的创作风格，并表示会继续写作。这件事也引发了关于名人后代是否应该获得特殊待遇的讨论。',
            'user_id': 'test_user',
            'nickname': '文化观察者',
            'url': 'https://www.xiaohongshu.com/explore/jqz_test_002'
        },
        {
            'note_id': 'jqz_test_003',
            'title': '深度解析贾浅浅的文学创作',
            'content': '贾浅浅的文学创作主要集中在诗歌领域。她的作品常常以生活琐事为题材，语言直白，情感真挚。支持者认为她的诗歌打破了传统诗歌的束缚，具有创新性；反对者则认为她的作品缺乏文学性和美感。贾浅浅的创作风格深受其父贾平凹的影响，但也有自己的特点。她善于从日常生活中发现诗意，用简单的语言表达深刻的情感。',
            'user_id': 'test_user',
            'nickname': '文学研究',
            'url': 'https://www.xiaohongshu.com/explore/jqz_test_003'
        },
        {
            'note_id': 'jqz_test_004',
            'title': '贾浅浅的学术背景与成就',
            'content': '贾浅浅拥有扎实的学术背景。她毕业于西北大学中文系，先后获得学士、硕士和博士学位。她的研究方向主要是现当代文学，曾在《文艺争鸣》等核心期刊发表多篇学术论文。除了学术研究，贾浅浅也积极参与文学创作，出版了多部诗集。她的学术成就和创作实践使她成为当代文坛备受关注的人物。',
            'user_id': 'test_user',
            'nickname': '学术博主',
            'url': 'https://www.xiaohongshu.com/explore/jqz_test_004'
        },
        {
            'note_id': 'jqz_test_005',
            'title': '贾浅浅与贾平凹：父女作家的文学之路',
            'content': '贾浅浅的父亲贾平凹是中国当代著名作家，代表作有《废都》《秦腔》等。贾浅浅从小受到父亲的影响，对文学产生了浓厚的兴趣。她在父亲的指导下开始写作，并逐渐形成了自己的风格。尽管父女俩的创作风格有所不同，但都对中国当代文学产生了重要影响。贾平凹曾公开表示支持女儿的创作，认为她有自己的独特视角和表达方式。',
            'user_id': 'test_user',
            'nickname': '文坛观察',
            'url': 'https://www.xiaohongshu.com/explore/jqz_test_005'
        }
    ]
    
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    for note in test_notes:
        cursor.execute('''
            INSERT OR REPLACE INTO notes
            (note_id, user_id, nickname, title, content, note_type,
             liked_count, collected_count, comment_count, share_count,
             cover_url, url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            note['note_id'],
            note['user_id'],
            note['nickname'],
            note['title'],
            note['content'],
            'normal',
            100,
            50,
            30,
            20,
            '',
            note['url'],
            now,
            now
        ))
    
    conn.commit()
    print(f'成功添加 {len(test_notes)} 篇贾浅浅相关测试笔记')
    
    cursor.execute("SELECT COUNT(*) FROM notes WHERE title LIKE '%贾浅浅%'")
    count = cursor.fetchone()[0]
    print(f'数据库中共有 {count} 篇贾浅浅相关笔记')
    
    conn.close()


if __name__ == '__main__':
    add_test_notes()
