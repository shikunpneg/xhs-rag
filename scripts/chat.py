"""
小红书 RAG 聊天服务 - 最终版
使用 sentence-transformers 语义嵌入模型
"""

import os
import re
import json
import requests
from typing import List, Dict, Any


class LLMService:
    """LLM 服务"""

    def __init__(self, api_key: str, api_base: str, model: str):
        self.api_key = api_key
        self.api_base = api_base.rstrip('/')
        self.model = model

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """发送聊天请求"""
        try:
            response = requests.post(
                f'{self.api_base}/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': messages,
                    'temperature': temperature
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f'LLM 调用失败: {e}'


class EmbeddingService:
    """语义嵌入服务 - 使用 sentence-transformers"""

    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            print(f'[OK] Loading semantic embedding model: {model_name}')
        except ImportError:
            print('WARNING: sentence-transformers not installed, using MD5 hash fallback')
            self.model = None

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本嵌入向量"""
        if self.model:
            try:
                embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
                return embeddings.tolist()
            except Exception as e:
                print(f'Embedding error: {e}')

        # Fallback: MD5 hash
        import hashlib
        embeddings = []
        for text in texts:
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()
            vector = []
            for i in range(384):
                byte_idx = i % len(hash_bytes)
                vector.append((hash_bytes[byte_idx] - 128) / 128.0)
            embeddings.append(vector)
        return embeddings

    def get_embedding(self, text: str) -> List[float]:
        """获取单个文本的嵌入向量"""
        return self.get_embeddings([text])[0]


class SentimentAnalyzer:
    """情感分析器"""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def analyze(self, text: str) -> Dict[str, Any]:
        """分析文本情感"""
        prompt = f"""请分析以下文本的情感倾向：

文本内容：{text}

请输出 JSON 格式结果，包含以下字段：
- sentiment: 情感类别（positive/neutral/negative）
- score: 情感分数（-1 到 1 之间，负数表示负面，正数表示正面）
- keywords: 关键词列表（提取 5-10 个重要关键词）
- summary: 文本摘要（50字以内）

只输出 JSON，不要其他内容。"""

        messages = [{'role': 'user', 'content': prompt}]
        result = self.llm_service.chat(messages)

        try:
            json_str = re.search(r'\{.*\}', result, re.DOTALL)
            if json_str:
                return json.loads(json_str.group())
        except:
            pass

        return {
            'sentiment': 'neutral',
            'score': 0.0,
            'keywords': [],
            'summary': text[:50]
        }


class KeywordExtractor:
    """关键词提取器"""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def extract(self, text: str, top_k: int = 10) -> List[Dict[str, float]]:
        """提取关键词及权重"""
        prompt = f"""请从以下文本中提取关键词及其重要性权重。

文本内容：{text}

请输出 JSON 格式结果，包含一个关键词列表：
- keywords: 关键词列表，每个关键词包含 name 和 weight（权重 0-1）

只输出 JSON，不要其他内容。"""

        messages = [{'role': 'user', 'content': prompt}]
        result = self.llm_service.chat(messages)

        try:
            json_str = re.search(r'\[.*\]|\{{.*\}}', result, re.DOTALL)
            if json_str:
                data = json.loads(json_str.group())
                if isinstance(data, dict) and 'keywords' in data:
                    return data['keywords']
                return data
        except:
            pass

        return []


class RAGChat:
    """RAG 聊天系统"""

    def __init__(self, persist_dir: str, api_key: str, api_base: str, model: str):
        self.persist_dir = persist_dir
        self.llm_service = LLMService(api_key, api_base, model)
        self.embedding_service = EmbeddingService()
        self.sentiment_analyzer = SentimentAnalyzer(self.llm_service)
        self.keyword_extractor = KeywordExtractor(self.llm_service)
        self.history = []

        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.collection = self.client.get_or_create_collection('xhs_notes')
        except Exception as e:
            print(f'ChromaDB init failed: {e}')
            self.client = None
            self.collection = None

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关文档"""
        if not self.collection:
            return []

        try:
            query_embedding = self.embedding_service.get_embedding(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['metadatas', 'documents', 'distances']
            )

            if not results or not results.get('ids') or not results['ids'][0]:
                return []

            sources = []
            for i in range(len(results['ids'][0])):
                distance = results['distances'][0][i] if 'distances' in results and results['distances'] else 1.0
                similarity = 1 - distance

                if distance < 0.7:
                    metadata = results['metadatas'][0][i]
                    document = results['documents'][0][i]
                    sources.append({
                        'title': metadata.get('title', '无标题'),
                        'content': document[:500],
                        'url': metadata.get('url', ''),
                        'score': similarity
                    })

            return sources

        except Exception as e:
            print(f'Retrieval failed: {e}')
            return []

    def chat(self, query: str, top_k: int = 5, use_history: bool = True) -> Dict[str, Any]:
        """聊天"""
        sources = self.retrieve(query, top_k)

        if sources:
            context = '\n\n'.join([
                f'[{i+1}] {s["title"]}\n{s["content"]}'
                for i, s in enumerate(sources)
            ])

            messages = [
                {'role': 'system', 'content': '''你是一个专业的小红书内容助手。请根据提供的参考资料回答用户的问题。

要求：
1. 只基于参考资料中的信息回答，不要编造内容
2. 如果参考资料中没有相关信息，请明确告知用户
3. 回答要简洁、准确、有条理
4. 如果多个参考资料内容相关，可以综合整理后回答'''}
            ]

            if use_history and self.history:
                messages.extend(self.history[-5:])

            messages.append({
                'role': 'user',
                'content': f'参考资料：\n{context}\n\n用户问题：{query}'
            })

            answer = self.llm_service.chat(messages)

            if use_history:
                self.history.append({'role': 'user', 'content': query})
                self.history.append({'role': 'assistant', 'content': answer})
        else:
            answer = '抱歉，知识库中暂时没有找到与您问题相关的内容。请尝试更换关键词或扩展搜索范围。'

        return {
            'answer': answer,
            'sources': sources
        }

    def analyze_all_notes(self, top_k: int = 20) -> Dict[str, Any]:
        """分析所有笔记"""
        if not self.collection:
            return {
                'sentiment': {'sentiment': 'neutral', 'score': 0.0, 'summary': ''},
                'keywords': [],
                'note_count': 0
            }

        try:
            results = self.collection.get(limit=top_k, include=['documents', 'metadatas'])

            if not results or not results.get('documents'):
                return {
                    'sentiment': {'sentiment': 'neutral', 'score': 0.0, 'summary': ''},
                    'keywords': [],
                    'note_count': 0
                }

            all_text = '\n\n'.join(results['documents'][:top_k])

            sentiment = self.sentiment_analyzer.analyze(all_text)
            keywords_data = self.keyword_extractor.extract(all_text)
            keywords = [kw['name'] if isinstance(kw, dict) else kw for kw in keywords_data[:10]]

            return {
                'sentiment': sentiment,
                'keywords': keywords,
                'note_count': len(results['documents'])
            }

        except Exception as e:
            print(f'Analysis failed: {e}')
            return {
                'sentiment': {'sentiment': 'neutral', 'score': 0.0, 'summary': ''},
                'keywords': [],
                'note_count': 0
            }

    def clear_history(self):
        """清空对话历史"""
        self.history = []
