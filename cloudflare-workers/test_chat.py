import requests

url = 'https://xhs-rag.ok2442504.workers.dev/api/chat'
data = {'query': '贾浅浅是谁', 'top_k': 5}

try:
    response = requests.post(url, json=data, timeout=30)
    print('HTTP状态:', response.status_code)
    result = response.json()
    print('\n=== AI回答 ===')
    print(result.get('answer', '无回答'))
    print('\n=== 参考来源 ===')
    for i, source in enumerate(result.get('sources', [])):
        print(f'[{i+1}] {source.get("title", "无标题")}')
        print(f'   相似度: {source.get("score", 0) * 100:.1f}%')
        print(f'   内容: {source.get("content", "")[:100]}...')
except Exception as e:
    print('请求失败:', e)
