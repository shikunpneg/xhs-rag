"""
小红书 RAG Web UI - 增强版
包含情感分析、关键词提取和批量采集功能
"""

import os
import sys
import streamlit as st
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.chat import RAGChat
from scripts.crawl import XHSCrawler, DataStorage
from scripts.rag_pipeline import RAGPipeline
from scripts.cookie_utils import auto_format_cookie

st.set_page_config(
    page_title='小红书 RAG 知识库',
    page_icon='📚',
    layout='wide'
)

st.markdown('''
<style>
.chat-message {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
}
.user-message {
    background-color: #e3f2fd;
}
.assistant-message {
    background-color: #f5f5f5;
}
.source-card {
    background-color: #fff3e0;
    padding: 0.5rem;
    border-radius: 0.25rem;
    margin-top: 0.5rem;
    font-size: 0.9rem;
}
.sentiment-positive {
    background-color: #e8f5e9;
    border-left: 4px solid #4caf50;
}
.sentiment-neutral {
    background-color: #f5f5f5;
    border-left: 4px solid #9e9e9e;
}
.sentiment-negative {
    background-color: #ffebee;
    border-left: 4px solid #f44336;
}
</style>
''', unsafe_allow_html=True)


@st.cache_resource
def init_rag_chat():
    """初始化 RAG 聊天系统"""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
    model = os.getenv('LLM_MODEL', 'deepseek-v4-flash')
    persist_dir = os.getenv('CHROMA_PERSIST_DIR', './data/chroma')

    if not api_key:
        return None

    return RAGChat(persist_dir, api_key, api_base, model)


def main():
    """主函数"""
    st.title('📚 小红书 RAG 知识库')

    with st.sidebar:
        st.header('⚙️ 设置')

        page = st.radio(
            '选择功能',
            ['💬 智能问答', '📊 数据采集', '🔧 知识库管理'],
            label_visibility='collapsed'
        )

        st.divider()

        if page == '💬 智能问答':
            top_k = st.slider('检索数量', 1, 10, 5)
            use_history = st.checkbox('使用对话历史', value=True)

            if st.button('清空对话历史'):
                if 'rag_chat' in st.session_state:
                    st.session_state.rag_chat.clear_history()
                st.success('对话历史已清空')

            st.divider()

            if st.button('📊 分析全部笔记'):
                if 'rag_chat' in st.session_state and st.session_state.rag_chat:
                    with st.spinner('正在分析...'):
                        try:
                            analysis = st.session_state.rag_chat.analyze_all_notes(top_k=20)
                            st.session_state['analysis_result'] = analysis
                            st.success('分析完成！')
                        except Exception as e:
                            st.error(f'分析失败: {e}')
                else:
                    st.warning('请先初始化 RAG 系统')

        elif page == '📊 数据采集':
            st.subheader('数据采集')

            mode = st.radio('采集模式', ['单用户采集', '批量采集'], horizontal=True)

            if mode == '单用户采集':
                user_id = st.text_input('博主 ID', value='5bd9405f6b58b737b5401d2e')
            else:
                user_ids_input = st.text_area('博主 ID 列表', 
                    placeholder='每行一个博主 ID\n例如:\n5bd9405f6b58b737b5401d2e\n5c1d6e7f8g9h0i1j2k3l4m5n6')

            max_notes = st.slider('最大笔记数', 10, 100, 50)

            st.markdown('**小红书 Cookie** (支持自动格式化)')
            cookie_raw = st.text_area(
                '直接粘贴浏览器复制的 Cookie 表格即可', 
                height=150,
                placeholder='粘贴从 Chrome DevTools 复制的 Cookie 表格...'
            )

            formatted_cookie = ''
            if cookie_raw:
                result = auto_format_cookie(cookie_raw)
                formatted_cookie = result['formatted']
                
                with st.expander('📋 格式化结果', expanded=True):
                    st.markdown(f"**检测格式**: `{result['format_type']}`")
                    
                    if result['validation']:
                        if result['validation']['valid']:
                            st.success(f"✅ {result['validation']['message']}")
                        else:
                            st.warning(f"⚠️ {result['validation']['message']}")
                    
                    st.code(formatted_cookie[:100] + '...' if len(formatted_cookie) > 100 else formatted_cookie, language='text')
                    
                    if st.button('📋 复制格式化后的 Cookie'):
                        st.session_state['copied_cookie'] = formatted_cookie
                        st.success('已复制到剪贴板!')

            if st.button('🚀 开始采集'):
                if mode == '单用户采集':
                    if not user_id:
                        st.error('请输入博主 ID')
                    elif not formatted_cookie and not os.getenv('XHS_COOKIE'):
                        st.error('请输入小红书 Cookie')
                    else:
                        with st.spinner('正在采集...'):
                            try:
                                crawler = XHSCrawler(formatted_cookie or os.getenv('XHS_COOKIE'))
                                storage = DataStorage(os.getenv('DB_PATH', './data/xhs_notes.db'))
                                notes = crawler.crawl_user_notes(user_id, max_notes)
                                storage.save_notes(notes)
                                storage.close()
                                st.success(f'✅ 成功采集 {len(notes)} 篇笔记')
                            except Exception as e:
                                st.error(f'采集失败: {e}')
                else:
                    user_ids = [u.strip() for u in user_ids_input.split('\n') if u.strip()]
                    if not user_ids:
                        st.error('请输入博主 ID 列表')
                    elif not formatted_cookie and not os.getenv('XHS_COOKIE'):
                        st.error('请输入小红书 Cookie')
                    else:
                        with st.spinner('正在批量采集...'):
                            try:
                                crawler = XHSCrawler(formatted_cookie or os.getenv('XHS_COOKIE'))
                                storage = DataStorage(os.getenv('DB_PATH', './data/xhs_notes.db'))
                                results = crawler.batch_crawl_users(user_ids, max_notes)
                                total = 0
                                for uid, notes in results.items():
                                    storage.save_notes(notes)
                                    total += len(notes)
                                storage.close()
                                st.success(f'✅ 批量采集完成，共采集 {len(user_ids)} 个用户，{total} 篇笔记')
                            except Exception as e:
                                st.error(f'批量采集失败: {e}')

        elif page == '🔧 知识库管理':
            st.subheader('知识库管理')

            if st.button('构建知识库'):
                with st.spinner('正在构建...'):
                    try:
                        api_key = os.getenv('DEEPSEEK_API_KEY')
                        api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')

                        pipeline = RAGPipeline(
                            db_path=os.getenv('DB_PATH', './data/xhs_notes.db'),
                            persist_dir=os.getenv('CHROMA_PERSIST_DIR', './data/chroma'),
                            api_key=api_key,
                            api_base=api_base
                        )
                        pipeline.build_knowledge_base()
                        st.success('知识库构建完成')
                    except Exception as e:
                        st.error(f'构建失败: {e}')

            try:
                import chromadb
                client = chromadb.PersistentClient(path=os.getenv('CHROMA_PERSIST_DIR', './data/chroma'))
                collection = client.get_or_create_collection('xhs_notes')
                st.metric('向量数量', collection.count())
            except:
                st.metric('向量数量', 0)

            storage = DataStorage(os.getenv('DB_PATH', './data/xhs_notes.db'))
            total_notes = len(storage.get_all_notes())
            user_count = storage.get_user_count()
            storage.close()
            
            st.metric('笔记总数', total_notes)
            st.metric('博主数量', user_count)

    if page == '💬 智能问答':
        rag_chat = init_rag_chat()

        if not rag_chat:
            st.warning('请先配置 DEEPSEEK_API_KEY 环境变量')
            return

        if 'rag_chat' not in st.session_state:
            st.session_state.rag_chat = rag_chat
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = None

        if st.session_state.analysis_result:
            analysis = st.session_state.analysis_result
            st.subheader('📊 笔记分析报告')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                sentiment = analysis['sentiment']['sentiment']
                score = analysis['sentiment']['score']
                if sentiment == 'positive':
                    st.markdown(f'<div class="sentiment-positive padding:1rem"><strong>情感倾向:</strong> 正面 😊<br><strong>情感分数:</strong> {score:.2f}</div>', unsafe_allow_html=True)
                elif sentiment == 'negative':
                    st.markdown(f'<div class="sentiment-negative padding:1rem"><strong>情感倾向:</strong> 负面 😞<br><strong>情感分数:</strong> {score:.2f}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="sentiment-neutral padding:1rem"><strong>情感倾向:</strong> 中性 😐<br><strong>情感分数:</strong> {score:.2f}</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown(f'<strong>笔记数量:</strong> {analysis.get("note_count", 0)}')
            
            with col3:
                st.markdown(f'<strong>摘要:</strong> {analysis["sentiment"]["summary"]}')

            st.subheader('🏷️ 关键词')
            keywords = analysis['keywords']
            st.markdown(' '.join([f'`{kw}`' for kw in keywords]))

            st.divider()

        for message in st.session_state.messages:
            with st.chat_message(message['role']):
                st.markdown(message['content'])

                if message['role'] == 'assistant' and 'sources' in message:
                    with st.expander('📖 查看来源'):
                        for i, source in enumerate(message['sources'], 1):
                            st.markdown(f'''
                            <div class="source-card">
                            <strong>[{i}] {source['title']}</strong><br>
                            {source['content']}<br>
                            <a href="{source['url']}" target="_blank">查看原文</a>
                            </div>
                            ''', unsafe_allow_html=True)

        if prompt := st.chat_input('输入你的问题...'):
            st.chat_message('user').markdown(prompt)
            st.session_state.messages.append({'role': 'user', 'content': prompt})

            with st.chat_message('assistant'):
                with st.spinner('思考中...'):
                    try:
                        result = st.session_state.rag_chat.chat(prompt, top_k, use_history)

                        st.markdown(result['answer'])
                        st.session_state.messages.append({
                            'role': 'assistant',
                            'content': result['answer'],
                            'sources': result['sources']
                        })

                        if result['sources']:
                            with st.expander('📖 查看来源'):
                                for i, source in enumerate(result['sources'], 1):
                                    st.markdown(f'''
                                    <div class="source-card">
                                    <strong>[{i}] {source['title']}</strong><br>
                                    {source['content']}<br>
                                    <a href="{source['url']}" target="_blank">查看原文</a>
                                    </div>
                                    ''', unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f'回答失败: {e}')

    elif page == '📊 数据采集':
        st.header('📊 数据采集')
        st.info('请在左侧输入博主 ID 和 Cookie，然后点击"开始采集"')

        with st.expander('📖 如何获取 Cookie'):
            st.markdown('''
            1. 打开 Chrome 浏览器，访问 https://www.xiaohongshu.com 并登录
            2. 按 F12 打开开发者工具
            3. 切换到 Application (应用程序) 标签
            4. 左侧选择 Cookies -> https://www.xiaohongshu.com
            5. 复制所有 Cookie 值，拼接成字符串

            格式示例: `a1=xxx; webId=xxx; web_session=xxx; ...`
            ''')

    elif page == '🔧 知识库管理':
        st.header('🔧 知识库管理')
        st.info('点击左侧"构建知识库"按钮，将数据库中的笔记向量化存入向量数据库')


if __name__ == '__main__':
    main()
