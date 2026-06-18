#!/usr/bin/env python
"""
测试贾浅浅测试笔记的检索
"""

import requests
from sentence_transformers import SentenceTransformer

MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
API_BASE = 'https://xhs-rag.ok2442504.workers.dev'


def test_jiaqianqian():
    print('测试贾浅浅测试笔记检索')
    print('=' * 60)
    
    queries = ['贾浅浅是谁', '贾浅浅诗歌', '贾平凹女儿', '贾浅浅争议']
    
    for query in queries:
        print(f'\n查询: {query}')
        print('-' * 60)
        
        embedding = MODEL.encode(query).tolist()
        
        response = requests.post(
            f'{API_BASE}/api/chat',
            json={'query': query, 'top_k': 5, 'embedding': embedding},
            headers={'Content-Type': 'application/json; charset=utf-8'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f'回答: {result["answer"]}')
            print(f'\n检索到 {len(result["sources"])} 篇相关笔记:')
            for i, source in enumerate(result['sources'], 1):
                print(f'\n{i}. 标题: {source["title"]}')
                print(f'   分数: {source["score"]:.4f}')
                print(f'   内容预览: {source["content"][:100] if source["content"] else "空"}...')
        else:
            print(f'请求失败: {response.status_code}')


if __name__ == '__main__':
    test_jiaqianqian()
