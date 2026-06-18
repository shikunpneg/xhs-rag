# GitHub Actions 自动更新 Cookie 配置指南

## 前置准备

### 1. 获取 Cloudflare API Token

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 进入 **My Profile** → **API Tokens**
3. 点击 **Create Token**
4. 选择 **Edit Cloudflare Workers** 模板
5. 配置：
   - **Account Resources**: 选择你的账号
   - **Zone Resources**: 不需要
6. 点击 **Continue to Summary** → **Create Token**
7. 复制生成的 Token

### 2. 获取 Cloudflare Account ID

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 点击右侧边栏的 **Workers & Pages**
3. 复制页面顶部的 **Account ID**

### 3. 上传项目到 GitHub

```bash
cd e:\rag\xhs-rag
git init
git add .
git commit -m "Initial commit with GitHub Actions"
git branch -M main
git remote add origin https://github.com/你的用户名/xhs-rag.git
git push -u origin main
```

### 4. 配置 GitHub Secrets

1. 进入 GitHub 仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**，添加：

| Secret 名称 | 值 |
|------------|-----|
| `CLOUDFLARE_API_TOKEN` | 你的 Cloudflare API Token |
| `CLOUDFLARE_ACCOUNT_ID` | 你的 Cloudflare Account ID |

## 功能说明

### 自动执行流程

```
每天凌晨2点自动执行：
┌─────────────────────────────────────────────┐
│ 1. 使用 Playwright 访问小红书获取新 Cookie   │
│ 2. 将新 Cookie 更新到 Cloudflare Workers    │
│ 3. 重新部署 Worker                          │
│ 4. 触发笔记爬取                             │
└─────────────────────────────────────────────┘
```

### 手动触发

1. 进入 GitHub 仓库
2. 点击 **Actions** → **Update XHS Cookie & Crawl**
3. 点击 **Run workflow**
4. 可以指定用户 ID

## 费用说明

| 项目 | 费用 | 说明 |
|------|------|------|
| GitHub Actions | 免费 | 每月 2000 分钟 |
| Cloudflare Workers | 免费 | 每天 100,000 次请求 |
| Playwright 浏览器 | 免费 | 使用 GitHub 托管的 Runner |

## 注意事项

1. **Cookie 有效期**：小红书 Cookie 通常有效期为 30 天
2. **执行时间**：每天凌晨 2 点执行，避免高峰期
3. **失败重试**：如果当天失败，第二天会自动重试
