import os, sys, subprocess, json
from dotenv import load_dotenv
load_dotenv()

base_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(base_dir, 'scripts', 'crawl.py')

print("base_dir:", base_dir)
print("script_path:", script_path)

result = subprocess.run(
    [sys.executable, script_path, '--user-id', '5bd9405f6b58b737b5401d2e', '--max-notes', '1'],
    capture_output=True,
    encoding='utf-8',
    errors='replace',
    timeout=120,
    cwd=base_dir
)
print('returncode:', result.returncode)
print('stdout length:', len(result.stdout) if result.stdout else 0)
print('stdout preview:', result.stdout[:300] if result.stdout else 'None')
print('stderr:', result.stderr[:200] if result.stderr else 'None')
