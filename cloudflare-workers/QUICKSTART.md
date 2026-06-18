# 🚀 快速部署指南

## 5分钟部署到Cloudflare Workers

### 第一步：登录Cloudflare（约1分钟）

```bash
cd e:\rag\xhs-rag\cloudflare-workers
npm install
npx wrangler login
```

### 第二步：创建Vectorize向量数据库（约1分钟）

```bash
# 创建Vectorize向量数据库（使用bge-base模型预设）
npx wrangler vectorize create xhs-embeddings --preset=@cf/baai/bge-base-en-v1.5

# 或者手动指定维度和度量（等效）
npx wrangler vectorize create xhs-embeddings --dimensions=768 --metric=cosine
```

### 第三步：本地测试（约1分钟）

```bash
npx wrangler dev

# 访问 http://localhost:8787
```

### 第四步：部署到生产环境（约1分钟）

```bash
npx wrangler deploy

# 部署成功后会显示你的Workers地址，例如：
# https://xhs-rag.<your-account>.workers.dev
```

---

## 📋 部署后操作

### 1. 查看API地址
```bash
npx wrangler info
```

### 2. 导入本地笔记到Cloudflare
```bash
node import-notes.js
```

### 3. 访问Web界面
- API地址：`https://xhs-rag.<your-account>.workers.dev`
- API文档：`https://xhs-rag.<your-account>.workers.dev/api`

---

## 🔧 常见问题

### Q: wrangler login失败？
A: 确保你的网络可以访问Cloudflare，并且浏览器没有阻止弹出窗口。

### Q: Vectorize创建失败？
A: Vectorize可能不在你的账号计划中。请先在Cloudflare Dashboard中确认Vectorize已启用。

### Q: 部署后无法访问？
A: 检查wrangler.toml中的路由配置。如果是workers.dev子域名，应该会自动配置。

### Q: 如何更新代码？
A: 修改`src/index.js`后，再次运行`npx wrangler deploy`即可。

---

## 📁 项目文件说明

```
cloudflare-workers/
├── wrangler.toml          # Cloudflare配置文件
├── package.json           # Node.js依赖
├── src/
│   └── index.js          # 主要RAG逻辑
├── index.html            # Web界面
├── import-notes.js       # 批量导入脚本
├── deploy.sh             # 部署脚本
└── README.md             # 详细文档
```

---

## 🎯 下一步

1. **测试API**：在浏览器打开`http://localhost:8787/api`
2. **导入笔记**：运行`node import-notes.js`
3. **配置自定义域名**（可选）：
   ```bash
   npx wrangler routes set --zone-name=yourdomain.com --pattern=rag.yourdomain.com
   ```

---

## 💰 费用

Cloudflare Workers免费额度：
- Workers：每天10万请求
- Vectorize：每月3000万向量维度
- Workers AI：每月10,000次推理

**个人使用完全免费！**
