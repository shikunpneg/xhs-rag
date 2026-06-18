import re

with open('./data/page_dump.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找 window.__INITIAL_STATE__
initial_state = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', content, re.DOTALL)
if initial_state:
    print(f'找到 __INITIAL_STATE__, 长度: {len(initial_state.group(1))}')
else:
    print('未找到 __INITIAL_STATE__')

# 查找 window.__REDUX_STATE__  
redux_state = re.search(r'window\.__REDUX_STATE__\s*=\s*({.*?});', content, re.DOTALL)
if redux_state:
    print(f'找到 __REDUX_STATE__, 长度: {len(redux_state.group(1))}')
else:
    print('未找到 __REDUX_STATE__')

# 查找 window.__data__
window_data = re.search(r'window\.__data__\s*=\s*({.*?});', content, re.DOTALL)
if window_data:
    print(f'找到 __data__, 长度: {len(window_data.group(1))}')
else:
    print('未找到 __data__')

# 查找 <script> 标签中的 JSON 数据
scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
print(f'\n找到 {len(scripts)} 个 script 标签')

for i, script in enumerate(scripts[:5]):
    if len(script) > 100:
        print(f'\nScript {i}: {script[:200]}...')
