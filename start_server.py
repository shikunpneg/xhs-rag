#!/usr/bin/env python
"""
小红书 RAG 服务启动脚本
"""

import os
import sys
import subprocess
import time

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    print(f"项目目录: {project_dir}")
    print(f"Python版本: {sys.version}")
    
    # 设置环境变量
    os.environ['DEEPSEEK_API_KEY'] = 'sk-87ca71c098b14a68a12e2b4461bd986a'
    os.environ['DEEPSEEK_API_BASE'] = 'https://api.deepseek.com/v1'
    os.environ['LLM_MODEL'] = 'deepseek-v4-flash'
    os.environ['CHROMA_PERSIST_DIR'] = os.path.join(project_dir, 'data', 'chroma')
    os.environ['DB_PATH'] = os.path.join(project_dir, 'data', 'xhs_notes.db')
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    
    # 启动Streamlit服务
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 
        'scripts/web_ui.py',
        '--server.port', '8502',
        '--server.address', '0.0.0.0',
        '--server.enableCORS', 'false',
        '--server.enableXsrfProtection', 'false'
    ]
    
    print(f"\n启动命令: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # 读取输出
        for line in iter(process.stdout.readline, ''):
            print(line.strip())
            if "Local URL" in line or "Network URL" in line:
                print("=" * 60)
                print("🎉 服务启动成功！")
                print(f"本地访问: http://localhost:8502")
                print(f"局域网访问: http://192.168.1.11:8502")
                print("=" * 60)
                
        process.wait()
        
    except KeyboardInterrupt:
        print("\n服务已停止")
        if process:
            process.terminate()
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
