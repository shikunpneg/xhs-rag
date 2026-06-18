"""
RAG 知识库构建脚本 - 优化版
包含智能文本分块策略
"""

import os
import json
import sqlite3
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings

load_dotenv()


class SmartTextChunker:
    """智能文本分块器"""

    def __init__(self, chunk_size: int = 300, chunk_overlap: int = 50, 
                 min_chunk_size: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """按段落切分"""
        paragraphs = re.split(r'\n\n+', text.strip())
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_by_sentences(self, text: str) -> List[str]:
        """按句子切分"""
        sentences = re.split(r'(?<=[。！？；])', text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(self, text: str) -> List[str]:
        """智能分块"""
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        paragraphs = self._split_by_paragraphs(text)
        
        if len(paragraphs) == 1:
            return self._chunk_single_paragraph(text)
        
        return self._chunk_by_paragraphs(paragraphs)

    def _chunk_single_paragraph(self, text: str) -> List[str]:
        """处理单个长段落"""
        chunks = []
        sentences = self._split_by_sentences(text)
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk = ''.join(current_chunk)
                if len(chunk) >= self.min_chunk_size:
                    chunks.append(chunk)
                
                overlap_text = ''.join(current_chunk[-2:]) if len(current_chunk) >= 2 else ''
                current_chunk = [overlap_text, sentence]
                current_length = len(overlap_text) + sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        if current_chunk:
            chunk = ''.join(current_chunk)
            if len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)

        return chunks

    def _chunk_by_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """按段落进行分块"""
        chunks = []
        current_chunk = []
        current_length = 0

        for paragraph in paragraphs:
            paragraph_length = len(paragraph)
            
            if current_length + paragraph_length > self.chunk_size and current_chunk:
                chunk = '\n\n'.join(current_chunk)
                if len(chunk) >= self.min_chunk_size:
                    chunks.append(chunk)
                
                last_paragraph = current_chunk[-1] if current_chunk else ''
                overlap_length = min(len(last_paragraph), self.chunk_overlap)
                overlap_text = last_paragraph[-overlap_length:]
                
                current_chunk = [overlap_text, paragraph]
                current_length = len(overlap_text) + paragraph_length
            else:
                current_chunk.append(paragraph)
                current_length += paragraph_length

        if current_chunk:
            chunk = '\n\n'.join(current_chunk)
            if len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)

        return chunks

    def chunk_note(self, note: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将笔记分块"""
        title = note.get('title', '')
        content = note.get('content', '')
        
        chunks = []
        
        if title:
            title_chunk = {
                'chunk_id': f"{note['note_id']}_title",
                'note_id': note['note_id'],
                'user_id': note.get('user_id', ''),
                'nickname': note.get('nickname', ''),
                'title': title,
                'content': title,
                'url': note.get('url', ''),
                'publish_time': note.get('publish_time', ''),
                'chunk_index': -1,
                'chunk_type': 'title'
            }
            chunks.append(title_chunk)

        if content:
            content_chunks = self.chunk_text(content)
            for i, chunk in enumerate(content_chunks):
                chunks.append({
                    'chunk_id': f"{note['note_id']}_{i}",
                    'note_id': note['note_id'],
                    'user_id': note.get('user_id', ''),
                    'nickname': note.get('nickname', ''),
                    'title': title,
                    'content': chunk,
                    'url': note.get('url', ''),
                    'publish_time': note.get('publish_time', ''),
                    'chunk_index': i,
                    'chunk_type': 'content'
                })

        return chunks


class EmbeddingService:
    """语义嵌入服务 - 使用 sentence-transformers"""

    def __init__(self, api_key: str = None, api_base: str = None, 
                 model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
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
                print(f'Embedding 生成失败: {e}')

        # 备用方案：使用MD5哈希
        import hashlib
        embeddings = []
        for text in texts:
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()

            vector = []
            for i in range(384):  # MiniLM 输出384维
                byte_idx = i % len(hash_bytes)
                vector.append((hash_bytes[byte_idx] - 128) / 128.0)

            embeddings.append(vector)

        return embeddings

    def get_embedding(self, text: str) -> List[float]:
        """获取单个文本的嵌入向量"""
        return self.get_embeddings([text])[0]


class VectorStore:
    """向量存储"""

    def __init__(self, persist_dir: str):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name='xhs_notes',
            metadata={'hnsw:space': 'cosine'}
        )

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """添加文本块到向量数据库"""
        if not chunks:
            return

        ids = [chunk['chunk_id'] for chunk in chunks]
        documents = [chunk['content'] for chunk in chunks]
        metadatas = [{
            'note_id': chunk['note_id'],
            'user_id': chunk.get('user_id', ''),
            'nickname': chunk.get('nickname', ''),
            'title': chunk.get('title', ''),
            'url': chunk.get('url', ''),
            'chunk_index': str(chunk.get('chunk_index', 0)),
            'chunk_type': chunk.get('chunk_type', 'content')
        } for chunk in chunks]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    def query(self, query_embedding: List[float], top_k: int = 5,
              filter_metadata: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """查询相似文本"""
        where = None
        if filter_metadata:
            where = {k: v for k, v in filter_metadata.items() if v}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=['documents', 'metadatas', 'distances']
        )

        chunks = []
        if results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                chunks.append({
                    'chunk_id': chunk_id,
                    'content': results['documents'][0][i] if results['documents'] else '',
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0
                })

        return chunks

    def get_count(self) -> int:
        """获取存储的文档数量"""
        return self.collection.count()


class RAGPipeline:
    """RAG 管道"""

    def __init__(self, db_path: str, persist_dir: str, api_key: str, api_base: str):
        self.db_path = db_path
        self.chunker = SmartTextChunker()
        self.embedding_service = EmbeddingService(api_key, api_base)
        self.vector_store = VectorStore(persist_dir)

    def load_notes_from_db(self) -> List[Dict[str, Any]]:
        """从数据库加载笔记"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM notes')
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def build_knowledge_base(self, batch_size: int = 100):
        """构建知识库"""
        print('正在加载笔记...')
        notes = self.load_notes_from_db()
        print(f'共加载 {len(notes)} 篇笔记')

        if not notes:
            print('没有找到笔记，请先运行爬虫脚本采集数据')
            return

        print('正在智能分块...')
        all_chunks = []
        for note in notes:
            chunks = self.chunker.chunk_note(note)
            all_chunks.extend(chunks)
        print(f'共生成 {len(all_chunks)} 个文本块')

        print('正在向量化并存入向量数据库...')
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            texts = [chunk['content'] for chunk in batch]

            embeddings = self.embedding_service.get_embeddings(texts)
            self.vector_store.add_chunks(batch, embeddings)

            print(f'  已处理 {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} 个文本块')

        print(f'知识库构建完成，共存储 {self.vector_store.get_count()} 个向量')

    def search(self, query: str, top_k: int = 5,
               filter_metadata: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """搜索相关内容"""
        query_embedding = self.embedding_service.get_embedding(query)
        return self.vector_store.query(query_embedding, top_k, filter_metadata)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='构建 RAG 知识库')
    parser.add_argument('--db-path', default=os.getenv('DB_PATH', './data/xhs_notes.db'),
                        help='SQLite 数据库路径')
    parser.add_argument('--persist-dir', default=os.getenv('CHROMA_PERSIST_DIR', './data/chroma'),
                        help='向量数据库持久化目录')
    parser.add_argument('--batch-size', type=int, default=100, help='批处理大小')

    args = parser.parse_args()

    api_key = os.getenv('DEEPSEEK_API_KEY')
    api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')

    if not api_key:
        print('错误: 请设置 DEEPSEEK_API_KEY 环境变量')
        return

    pipeline = RAGPipeline(args.db_path, args.persist_dir, api_key, api_base)
    pipeline.build_knowledge_base(args.batch_size)


if __name__ == '__main__':
    main()
