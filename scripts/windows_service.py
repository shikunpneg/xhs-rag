"""
小红书 RAG Windows 服务包装器
使用方式：
1. 安装 pywin32: pip install pywin32
2. 安装服务: python windows_service.py install
3. 启动服务: net start XHSRAGService
4. 卸载服务: python windows_service.py remove
"""

import win32serviceutil
import win32service
import win32event
import win32api
import servicemanager
import socket
import os
import sys
import subprocess


class XHSRAGService(win32serviceutil.ServiceFramework):
    _svc_name_ = "XHSRAGService"
    _svc_display_name_ = "小红书 RAG 服务"
    _svc_description_ = "提供小红书内容的智能问答和情感分析服务"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )
        self.main()

    def main(self):
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_dir)
        
        os.environ['DEEPSEEK_API_KEY'] = 'sk-87ca71c098b14a68a12e2b4461bd986a'
        os.environ['DEEPSEEK_API_BASE'] = 'https://api.deepseek.com/v1'
        os.environ['LLM_MODEL'] = 'deepseek-v4-flash'
        os.environ['CHROMA_PERSIST_DIR'] = os.path.join(project_dir, 'data', 'chroma')
        os.environ['DB_PATH'] = os.path.join(project_dir, 'data', 'xhs_notes.db')
        os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
        os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'

        cmd = [
            sys.executable, '-m', 'streamlit', 'run', 
            'scripts/web_ui.py',
            '--server.port', '8502',
            '--server.address', '0.0.0.0',
            '--server.enableCORS', 'false',
            '--server.enableXsrfProtection', 'false'
        ]

        self.process = subprocess.Popen(cmd)
        self.process.wait()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(XHSRAGService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(XHSRAGService)
