#!/usr/bin/env python
"""
测试RAG检索功能（本地生成中文查询嵌入）
"""

import requests
from sentence_transformers import SentenceTransformer

MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
API_BASE = 'https://xhs-rag.ok2442504.workers.dev'


def test_rag(query, top_k=3):
    print(f'\n查询: {query}')
    print('=' * 60)
    
    embedding = MODEL.encode(query).tolist()
    
    response = requests.post(
        f'{API_BASE}/api/chat',
        json={'query': query, 'top_k': top_k, 'embedding': embedding},
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
            print(f'   URL: {source["url"]}')
    else:
        print(f'请求失败: {response.status_code} - {response.text}')


if __name__ == '__main__':
    print('测试RAG检索功能')
    print('=' * 60)
    
    test_rag('贾浅浅是谁', top_k=3)
    test_rag('AI绘画教程', top_k=3)
