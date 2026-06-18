# 小红书 RAG Cloudflare Workers 部署指南

## 📋 部署前准备

### 1. 环境要求
- Node.js >= 18.x
- npm >= 9.x
- Cloudflare 账号

### 2. 安装依赖
```bash
npm install
```

## 🚀 部署步骤

### 步骤1: 登录Cloudflare
```bash
npx wrangler login
```
这会打开浏览器，你需要授权wrangler访问你的Cloudflare账号。

### 步骤2: 创建Cloudflare资源

#### 创建Vectorize向量数据库
```bash
npx wrangler vectorize create xhs-embeddings --metric=cosine --dimension=768
```

#### 创建D1数据库（元数据存储）
```bash
npx wrangler d1 create xhs-metadata
```
创建后，会输出 `database_id`，需要更新到 `wrangler.toml`。

#### 创建R2存储桶（笔记存储）
```bash
npx wrangler r2 bucket create xhs-notes
```

### 步骤3: 更新配置文件

编辑 `wrangler.toml`，填入上一步创建的资源和ID：

```toml
# D1数据库配置
[[d1]]
binding = "DB"
database_name = "xhs-metadata"
database_id = "填入你的D1数据库ID"

# KV命名空间配置（可选，用于缓存）
[[kv_namespaces]]
binding = "CACHE"
id = "填入你的KV ID"
```

### 步骤4: 部署到开发环境
```bash
npx wrangler dev
```
访问 http://localhost:8787 进行本地测试。

### 步骤5: 部署到生产环境
```bash
npx wrangler deploy
```

### 步骤6: 绑定自定义域名（可选）

如果你有自定义域名（如 `rag.example.com`），可以添加路由：

```bash
npx wrangler routes set --zone-name=example.com --pattern=rag.example.com
```

或在 `wrangler.toml` 中配置：
```toml
routes = [{ pattern = "rag.example.com", zone_name = "example.com" }]
```

## 📡 API 使用

部署成功后，API地址为：`https://xhs-rag.<your-account>.workers.dev`

### 1. RAG聊天
```bash
curl -X POST https://xhs-rag.<your-account>.workers.dev/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "贾浅浅是谁？",
    "top_k": 5
  }'
```

### 2. 情感分析
```bash
curl -X POST https://xhs-rag.<your-account>.workers.dev/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "今天天气真好，心情很开心！"
  }'
```

### 3. 添加笔记
```bash
curl -X POST https://xhs-rag.<your-account>.workers.dev/api/notes \
  -H "Content-Type: application/json" \
  -d '{
    "note_id": "note123",
    "title": "测试笔记",
    "content": "这是一篇测试笔记的内容",
    "url": "https://www.xiaohongshu.com/explore/note123",
    "author": "test_user"
  }'
```

### 4. 批量添加笔记
```bash
curl -X POST https://xhs-rag.<your-account>.workers.dev/api/notes/batch \
  -H "Content-Type: application/json" \
  -d '{
    "notes": [
      {"note_id": "note1", "title": "笔记1", "content": "内容1"},
      {"note_id": "note2", "title": "笔记2", "content": "内容2"}
    ]
  }'
```

### 5. 健康检查
```bash
curl https://xhs-rag.<your-account>.workers.dev/health
```

## 🛠️ 故障排查

### 1. Vectorize索引未创建
```bash
# 列出所有Vectorize索引
npx wrangler vectorize list

# 删除并重建
npx wrangler vectorize delete xhs-embeddings
npx wrangler vectorize create xhs-embeddings --metric=cosine --dimension=768
```

### 2. D1数据库错误
```bash
# 列出D1数据库
npx wrangler d1 list

# 检查数据库
npx wrangler d1 execute xhs-metadata --command="SELECT 1"
```

### 3. 部署失败
```bash
# 查看详细错误
npx wrangler deploy --verbose

# 检查环境变量
npx wrangler secret list
```

## 💰 费用说明

Cloudflare Workers 免费额度：
- Workers: 每天10万次请求
- Vectorize: 每月3000万向量维度查询
- Workers AI: 每月10,000次神经元计算
- D1: 每月500万行读取
- R2: 每月10GB存储 + 100万次操作

**个人使用基本免费！**

## 🔧 本地开发

### 启动本地开发服务器
```bash
cd cloudflare-workers
npm run dev
# 或
npx wrangler dev
```

### 运行测试
```bash
npm test
```

### 格式化代码
```bash
npm run format
```

## 📁 项目结构

```
cloudflare-workers/
├── wrangler.toml          # Cloudflare配置文件
├── vectorize.json         # Vectorize索引配置
├── package.json           # Node.js依赖
├── src/
│   └── index.js          # 主要代码
├── deploy.sh              # 部署脚本
└── README.md             # 本文档
```

## 🎯 下一步

1. 配置你的笔记数据库
2. 编写爬虫脚本，将小红书笔记同步到RAG系统
3. 创建前端界面（可选，使用HTML/JS）
4. 设置CI/CD自动化部署
