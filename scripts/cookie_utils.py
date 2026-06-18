"""
Cookie 格式化工具
支持多种格式的 Cookie 自动解析
"""

import re
from typing import Dict, Optional


def parse_cookie_table(cookie_text: str) -> str:
    """
    解析浏览器复制的 Cookie 表格格式
    支持格式：
    - Chrome Application 面板复制的表格
    - Name\tValue 格式
    - name=value 格式
    """
    if not cookie_text:
        return ""

    cookie_text = cookie_text.strip()

    # 如果已经是标准格式 (name=value; name2=value2)
    if '=' in cookie_text and '\t' not in cookie_text and '\n' not in cookie_text.split(';')[0]:
        return cookie_text

    cookies = {}

    # 尝试解析表格格式 (Chrome DevTools 复制的格式)
    # 格式: name \t value \t domain \t path \t ...
    lines = cookie_text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 按制表符分割
        parts = line.split('\t')

        if len(parts) >= 2:
            name = parts[0].strip()
            value = parts[1].strip()

            # 过滤无效项
            if name and value and not name.startswith('#'):
                cookies[name] = value

        # 尝试解析 name=value 格式
        elif '=' in line:
            eq_pos = line.index('=')
            name = line[:eq_pos].strip()
            value = line[eq_pos + 1:].strip()
            if name and value:
                cookies[name] = value

    # 构建标准 Cookie 字符串
    return '; '.join([f'{k}={v}' for k, v in cookies.items()])


def parse_cookie_netscape(cookie_text: str) -> str:
    """
    解析 Netscape Cookie 格式
    格式: domain\tflag\tpath\tsecure\texpiry\tname\tvalue
    """
    cookies = {}
    lines = cookie_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        parts = line.split('\t')
        if len(parts) >= 7:
            name = parts[5].strip()
            value = parts[6].strip()
            if name and value:
                cookies[name] = value

    return '; '.join([f'{k}={v}' for k, v in cookies.items()])


def validate_cookie(cookie: str) -> Dict[str, any]:
    """
    验证 Cookie 是否有效
    返回验证结果和必要字段
    """
    result = {
        'valid': False,
        'message': '',
        'has_webId': False,
        'has_web_session': False,
        'has_a1': False
    }

    if not cookie:
        result['message'] = 'Cookie 为空'
        return result

    # 检查必要字段
    result['has_webId'] = 'webId=' in cookie
    result['has_web_session'] = 'web_session=' in cookie
    result['has_a1'] = 'a1=' in cookie

    if result['has_webId'] and result['has_web_session']:
        result['valid'] = True
        result['message'] = 'Cookie 格式正确'
    elif result['has_webId'] or result['has_a1']:
        result['valid'] = True
        result['message'] = 'Cookie 可能有效，但建议检查是否包含 web_session'
    else:
        result['message'] = 'Cookie 缺少必要字段 (webId 或 a1)'

    return result


def auto_format_cookie(cookie_text: str) -> Dict[str, any]:
    """
    自动识别并格式化 Cookie
    返回格式化结果和验证信息
    """
    result = {
        'original': cookie_text,
        'formatted': '',
        'validation': None,
        'format_type': 'unknown'
    }

    if not cookie_text:
        return result

    cookie_text = cookie_text.strip()

    # 检测格式类型
    if '\t' in cookie_text:
        # 表格格式
        result['format_type'] = 'table'
        result['formatted'] = parse_cookie_table(cookie_text)
    elif cookie_text.startswith('http') or '.xiaohongshu.com' in cookie_text.split('\t')[0] if '\t' in cookie_text else False:
        # Netscape 格式
        result['format_type'] = 'netscape'
        result['formatted'] = parse_cookie_netscape(cookie_text)
    elif '=' in cookie_text and ';' in cookie_text:
        # 已经是标准格式
        result['format_type'] = 'standard'
        result['formatted'] = cookie_text
    elif '=' in cookie_text:
        # 单个或多个 name=value 格式
        result['format_type'] = 'simple'
        result['formatted'] = cookie_text
    else:
        # 尝试表格解析
        result['format_type'] = 'auto'
        result['formatted'] = parse_cookie_table(cookie_text)

    # 验证
    result['validation'] = validate_cookie(result['formatted'])

    return result


# 测试
if __name__ == '__main__':
    test_cookie = """a1 	 19d6bf7363c7fujl2aqmp3ptr64pvf8xygkyu4gsy50000281379 	 .xiaohongshu.com 	 / 	 2027-04-08T07:20:56.000Z
web_session 	 040069b4d314487305a10c4ae33b4b030dee19 	 .xiaohongshu.com 	 / 	 2027-04-08T07:23:16.543Z
webId 	 0a09f0c8467b7e1879da63b0bc6ce681 	 .xiaohongshu.com 	 / 	 2027-04-08T07:20:56.000Z"""

    result = auto_format_cookie(test_cookie)
    print(f"格式类型: {result['format_type']}")
    print(f"格式化结果: {result['formatted']}")
    print(f"验证: {result['validation']}")
