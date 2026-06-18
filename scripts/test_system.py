"""
创建测试数据并验证 RAG 系统
"""

import os
import sys
import json
import sqlite3

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.crawl import DataStorage
from scripts.rag_pipeline import RAGPipeline
from scripts.chat import RAGChat


def create_test_data():
    """创建测试数据"""
    print('创建测试数据...')

    # 初始化数据库
    db_path = './data/xhs_notes.db'
    storage = DataStorage(db_path)

    # 模拟笔记数据
    test_notes = [
        {
            'note_id': 'test001',
            'user_id': 'user123',
            'nickname': 'AI探索者',
            'title': 'AI绘画入门指南：从零开始学习 Stable Diffusion',
            'desc': '''最近 AI 绘画特别火，我也来分享一下我的学习经验。

1. 硬件准备
首先你需要一张 NVIDIA 显卡，显存至少 8GB，推荐 12GB 以上。

2. 软件安装
推荐使用 Stable Diffusion WebUI，安装简单，界面友好。

3. 提示词技巧
好的提示词是成功的一半。推荐使用英文提示词，结构化描述效果更好。

4. 模型选择
不同模型风格不同，推荐几个我常用的模型：
- anything-v5: 通用二次元风格
- realisticVision: 真实风格
- dreamshaper: 梦幻风格

5. 进阶技巧
学会使用 ControlNet 和 LoRA，可以让你的作品更加精细。''',
            'type': 'normal',
            'liked_count': 1234,
            'collected_count': 567,
            'comment_count': 89,
            'share_count': 45,
            'cover_url': '',
            'url': 'https://www.xiaohongshu.com/explore/test001'
        },
        {
            'note_id': 'test002',
            'user_id': 'user123',
            'nickname': 'AI探索者',
            'title': 'ChatGPT 高效使用技巧大全',
            'desc': '''ChatGPT 是一个非常强大的 AI 助手，但很多人不知道如何高效使用它。

技巧一：角色扮演
让 ChatGPT 扮演特定角色，可以获得更专业的回答。
例如："你是一位资深产品经理，请帮我分析这个需求..."

技巧二：结构化提问
使用清晰的格式提问，比如：
- 背景：...
- 问题：...
- 期望：...

技巧三：迭代优化
如果回答不满意，可以要求 ChatGPT 改进：
"请用更简洁的语言重新回答"
"请给出更多具体例子"

技巧四：使用代码解释器
对于数据分析任务，可以让 ChatGPT 使用代码解释器来处理。

技巧五：多轮对话
利用上下文，进行深入探讨，而不是每次都重新开始。''',
            'type': 'normal',
            'liked_count': 2345,
            'collected_count': 890,
            'comment_count': 123,
            'share_count': 67,
            'cover_url': '',
            'url': 'https://www.xiaohongshu.com/explore/test002'
        },
        {
            'note_id': 'test003',
            'user_id': 'user123',
            'nickname': 'AI探索者',
            'title': 'RAG 技术详解：让 AI 更懂你的数据',
            'desc': '''RAG (Retrieval-Augmented Generation) 是一种让 AI 更好地理解和处理特定领域数据的技术。

什么是 RAG？
简单来说，RAG 就是先从知识库中检索相关信息，再让 AI 基于这些信息生成回答。

RAG 的核心组件：
1. 文档处理：将文档切分成小块
2. 向量化：将文本转换为向量表示
3. 向量数据库：存储和检索向量
4. 检索：根据问题找到最相关的文档
5. 生成：AI 基于检索结果生成回答

RAG 的优势：
- 可以处理最新数据
- 减少幻觉问题
- 可追溯信息来源
- 不需要重新训练模型

应用场景：
- 企业知识库
- 智能客服
- 文档问答
- 代码助手''',
            'type': 'normal',
            'liked_count': 3456,
            'collected_count': 1234,
            'comment_count': 234,
            'share_count': 89,
            'cover_url': '',
            'url': 'https://www.xiaohongshu.com/explore/test003'
        }
    ]

    # 保存测试数据
    storage.save_notes(test_notes)
    storage.close()

    print(f'已创建 {len(test_notes)} 条测试数据')
    return test_notes


def test_rag_pipeline():
    """测试 RAG 管道"""
    print('\n测试 RAG 管道...')

    # 使用测试 API Key
    api_key = os.getenv('DEEPSEEK_API_KEY', 'test_key')
    api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')

    pipeline = RAGPipeline(
        db_path='./data/xhs_notes.db',
        persist_dir='./data/chroma',
        api_key=api_key,
        api_base=api_base
    )

    # 构建知识库
    pipeline.build_knowledge_base()

    # 测试搜索
    print('\n测试搜索功能...')
    results = pipeline.search('AI 绘画', top_k=2)
    print(f'搜索 "AI 绘画" 找到 {len(results)} 个结果')
    for i, r in enumerate(results, 1):
        print(f'  [{i}] {r["metadata"].get("title", "N/A")}')

    return True


def test_chat():
    """测试聊天功能"""
    print('\n测试聊天功能...')

    api_key = os.getenv('DEEPSEEK_API_KEY', 'test_key')
    api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
    model = os.getenv('LLM_MODEL', 'deepseek-v4-flash')

    rag_chat = RAGChat(
        persist_dir='./data/chroma',
        api_key=api_key,
        api_base=api_base,
        model=model
    )

    # 测试搜索
    results = rag_chat.search('如何学习 AI 绘画', top_k=2)
    print(f'搜索找到 {len(results)} 个相关结果')

    # 注意：实际聊天需要有效的 API Key
    print('聊天功能需要有效的 DEEPSEEK_API_KEY 才能正常工作')


def main():
    """主函数"""
    print('=' * 60)
    print('小红书 RAG 系统测试')
    print('=' * 60)

    # 创建测试数据
    create_test_data()

    # 测试 RAG 管道
    test_rag_pipeline()

    # 测试聊天
    test_chat()

    print('\n' + '=' * 60)
    print('测试完成！')
    print('=' * 60)
    print('\n下一步:')
    print('1. 配置 .env 文件中的 XHS_COOKIE')
    print('2. 运行 python scripts/crawl.py --user-id <博主ID> 采集数据')
    print('3. 运行 python scripts/rag_pipeline.py 构建知识库')
    print('4. 运行 python scripts/chat.py 开始聊天')


if __name__ == '__main__':
    main()
