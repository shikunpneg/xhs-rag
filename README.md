# 小红书 RAG 知识库系统

基于小红书博主内容的 RAG（检索增强生成）知识库系统，支持数据采集、向量化存储和智能问答。

## 功能特性

- 📊 **数据采集**: 支持爬取指定博主的小红书笔记
- 🗄️ **数据存储**: SQLite 本地存储，方便管理
- 🔍 **向量检索**: 基于 ChromaDB 的语义相似度搜索
- 💬 **智能问答**: 结合 DeepSeek LLM 的 RAG 问答系统
- 🌐 **多语言支持**: 支持中文内容分析

## 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   小红书平台     │────▶│   数据采集层     │────▶│   数据存储层     │
│  (博主笔记)      │     │  (爬虫脚本)      │     │   (SQLite)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   应用查询层     │◀────│   向量数据库     │◀────│   知识构建层     │
│  (RAG 聊天)      │     │   (ChromaDB)    │     │  (分块+向量化)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 快速开始

### 1. 环境准备

确保已安装:
- Python 3.8+
- Node.js 16+

### 2. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Node.js 依赖 (可选，用于 MCP 服务)
npm install
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入必要配置
# - XHS_COOKIE: 小红书 Cookie (必填)
# - DEEPSEEK_API_KEY: DeepSeek API Key
```

#### 获取小红书 Cookie

1. 打开 Chrome 浏览器，访问 https://www.xiaohongshu.com 并登录
2. 按 F12 打开开发者工具
3. 切换到 Application (应用程序) 标签
4. 左侧选择 Cookies -> https://www.xiaohongshu.com
5. 复制所有 Cookie 值，拼接成字符串

格式示例:
```
a1=xxx; webId=xxx; web_session=xxx; ...
```

### 4. 数据采集

```bash
# 爬取指定博主的笔记
python scripts/crawl.py --user-id <博主ID> --max-notes 50
```

### 5. 构建知识库

```bash
# 将笔记向量化并存入向量数据库
python scripts/rag_pipeline.py
```

### 6. 开始聊天

```bash
# 启动交互式聊天
python scripts/chat.py
```

## 项目结构

```
xhs-rag/
├── data/                   # 数据目录
│   ├── xhs_notes.db       # SQLite 数据库
│   ├── chroma/            # 向量数据库
│   └── notes_*.json       # 导出的笔记数据
├── scripts/
│   ├── crawl.py           # 数据采集脚本
│   ├── rag_pipeline.py    # RAG 管道脚本
│   └── chat.py            # 聊天脚本
├── .env                   # 环境变量配置
├── .env.example           # 环境变量模板
├── requirements.txt       # Python 依赖
├── package.json           # Node.js 配置
└── README.md              # 项目说明
```

## API 使用

### 数据采集 API

```python
from scripts.crawl import XHSCrawler, DataStorage

crawler = XHSCrawler(cookie='your_cookie')
storage = DataStorage('./data/xhs_notes.db')

# 爬取用户笔记
notes = crawler.crawl_user_all_notes('user_id', max_notes=50)
storage.save_notes(notes)
```

### RAG 查询 API

```python
from scripts.chat import RAGChat

rag = RAGChat(
    persist_dir='./data/chroma',
    api_key='your_api_key',
    api_base='https://api.deepseek.com/v1',
    model='deepseek-v4-flash'
)

# 查询
result = rag.chat('这个博主最近在讨论什么？')
print(result['answer'])
```

## 注意事项

⚠️ **重要提醒**:
- 本项目仅供学习研究使用
- 请遵守小红书平台服务条款
- 控制爬取频率，避免账号被风控
- Cookie 会过期，需要定期更新
- 请勿将抓取的数据用于商业或非法用途

## 技术栈

- **数据采集**: Python + Requests
- **数据存储**: SQLite
- **向量数据库**: ChromaDB
- **LLM**: DeepSeek API
- **嵌入模型**: 简化版 (可替换为真实嵌入服务)

## 后续优化

- [ ] 使用真实嵌入模型 (如 BGE-large-zh)
- [ ] 添加混合检索 (BM25 + 向量)
- [ ] 实现 Rerank 重排序
- [ ] 添加 Web UI 界面
- [ ] 支持多博主对比分析

## License

MIT License
