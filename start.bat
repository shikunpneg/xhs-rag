@echo off
chcp 65001 >nul
echo ============================================
echo 小红书 RAG 知识库系统
echo ============================================
echo.
echo 请选择要执行的操作:
echo.
echo [1] 启动 Web UI
echo [2] 采集数据
echo [3] 构建知识库
echo [4] 启动命令行聊天
echo [5] 测试系统
echo [0] 退出
echo.
set /p choice=请输入选项:

if "%choice%"=="1" goto web
if "%choice%"=="2" goto crawl
if "%choice%"=="3" goto build
if "%choice%"=="4" goto chat
if "%choice%"=="5" goto test
if "%choice%"=="0" goto end

:web
echo.
echo 启动 Web UI...
streamlit run scripts/web_ui.py
goto end

:crawl
echo.
set /p user_id=请输入博主ID:
set /p max_notes=请输入最大笔记数 (默认50):
if "%max_notes%"=="" set max_notes=50
python scripts/crawl.py --user-id %user_id% --max-notes %max_notes%
pause
goto end

:build
echo.
echo 构建知识库...
python scripts/rag_pipeline.py
pause
goto end

:chat
echo.
echo 启动命令行聊天...
python scripts/chat.py
goto end

:test
echo.
echo 测试系统...
python scripts/test_system.py
pause
goto end

:end
