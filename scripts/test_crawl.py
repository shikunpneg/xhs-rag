"""测试小红书Cookie和API"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

cookie = os.getenv('XHS_COOKIE')
user_id = '5bd9405f6b58b737b5401d2e'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Cookie': cookie,
    'Accept': 'application/json',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

print(f'测试Cookie: {cookie[:50]}...')
print(f'测试用户ID: {user_id}')

# 测试1: 获取用户主页
print('\n=== 测试1: 获取用户主页 ===')
try:
    resp = requests.get(f'https://www.xiaohongshu.com/user/profile/{user_id}', headers=headers, timeout=30)
    print(f'状态码: {resp.status_code}')
    print(f'页面长度: {len(resp.text)}')
    print(f'是否登录: {"登录" in resp.text or "登录" in resp.text}')
    print(f'是否需要验证: {"captcha" in resp.text.lower() or "验证码" in resp.text}')
except Exception as e:
    print(f'错误: {e}')

# 测试2: 尝试API接口
print('\n=== 测试2: 尝试API接口 ===')
api_urls = [
    f'https://www.xiaohongshu.com/api/sns/v1/user_posted?user_id={user_id}&page=1&page_size=10',
    f'https://www.xiaohongshu.com/api/sns/v2/user_posted?user_id={user_id}&page=1&page_size=10',
    f'https://www.xiaohongshu.com/api/sns/v1/user/profile?user_id={user_id}',
]

for url in api_urls:
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        print(f'\nURL: {url[:80]}...')
        print(f'状态码: {resp.status_code}')
        try:
            data = resp.json()
            print(f'响应: {json.dumps(data, ensure_ascii=False)[:200]}')
        except:
            print(f'响应前200字符: {resp.text[:200]}')
    except Exception as e:
        print(f'错误: {e}')