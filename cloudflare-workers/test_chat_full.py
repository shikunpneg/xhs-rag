import requests

url = 'https://xhs-rag.ok2442504.workers.dev/api/chat'
data = {'query': '贾浅浅是谁', 'top_k': 5}

response = requests.post(url, json=data, timeout=30)
result = response.json()
print('完整返回:', result)
