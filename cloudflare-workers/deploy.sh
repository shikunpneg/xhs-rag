#!/bin/bash
# 小红书 RAG Cloudflare Workers 部署脚本

set -e

echo "================================"
echo "XHS RAG Cloudflare Workers 部署"
echo "================================"

# 检查wrangler是否安装
if ! command -v npx &> /dev/null; then
    echo "错误: npx 未安装，请先安装 Node.js"
    exit 1
fi

# 登录Cloudflare（如果需要）
echo "检查Cloudflare登录状态..."
npx wrangler whoami 2>/dev/null || {
    echo "请先登录Cloudflare:"
    echo "  npx wrangler login"
    exit 1
}

# 创建Vectorize索引
echo ""
echo "步骤1: 创建Vectorize向量数据库..."
npx wrangler vectorize create xhs-embeddings --metric=cosine --dimension=768

# 创建D1数据库（元数据存储）
echo ""
echo "步骤2: 创建D1数据库（元数据）..."
npx wrangler d1 create xhs-metadata

# 创建R2存储桶（笔记存储）
echo ""
echo "步骤3: 创建R2存储桶..."
npx wrangler r2 bucket create xhs-notes

# 更新wrangler.toml中的数据库ID
echo ""
echo "步骤4: 请手动更新 wrangler.toml 中的数据库ID和R2 bucket配置"
echo "1. 运行 'npx wranger d1 list' 获取D1数据库ID"
echo "2. 运行 'npx wrangler kv namespace list' 获取KV ID"
echo "3. 更新 wrangler.toml 中的 database_id 和 kv_namespaces id"

# 部署到开发环境
echo ""
echo "步骤5: 部署到开发环境..."
npx wrangler dev

# 提示生产部署
echo ""
echo "================================"
echo "开发环境已启动！"
echo "访问 http://localhost:8787 进行测试"
echo ""
echo "部署到生产环境："
echo "  npx wrangler deploy"
echo "================================"
