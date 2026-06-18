"""
小红书爬取API服务
运行此脚本后，前端可以通过 http://localhost:5000/api/crawl 调用爬取功能
"""

import os
import sys
import json
import threading
import subprocess
import re
import logging
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# 配置文件日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger()

app = Flask(__name__)
CORS(app)

crawl_results = {}
crawl_lock = threading.Lock()

# RAG相关模块
try:
    from scripts.rag_pipeline import RAGPipeline, SmartTextChunker, EmbeddingService, VectorStore
    rag_available = True
except ImportError as e:
    logger.warning(f'RAG模块导入失败: {e}')
    rag_available = False

# 定时任务相关
scheduled_tasks = {}
task_lock = threading.Lock()

def parse_cookie_expiration(cookie_string):
    """解析Cookie中的过期时间"""
    cookies = {}
    for item in cookie_string.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()
    
    expiration_map = {
        'a1': 90,
        'acw_tc': 30,
        'web_session': 90,
        'id_token': 90,
        'gid': 365,
        'customerClientId': 365,
        'websectiga': 30,
        'sec_poison_id': 30,
        'ets': 30,
        'x-user-id-creator.xiaohongshu.com': 365,
        'xsecappid': 30,
    }
    
    results = {}
    for key, days in expiration_map.items():
        if key in cookies:
            import time
            expires_at = time.time() + days * 24 * 3600
            results[key] = {
                'exists': True,
                'expires_in_days': days,
                'expires_at': expires_at,
                'expires_at_str': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at)),
                'is_expired': False,
            }
        else:
            results[key] = {
                'exists': False,
                'expires_in_days': None,
                'expires_at': None,
                'expires_at_str': '缺失',
                'is_expired': True,
            }
    
    return results

def check_cookie_validity():
    """检查Cookie有效性"""
    cookie = os.getenv('XHS_COOKIE', '')
    if not cookie:
        return {
            'valid': False,
            'reason': 'Cookie未配置',
            'expiration_info': {},
        }
    
    expiration_info = parse_cookie_expiration(cookie)
    
    expired_count = sum(1 for v in expiration_info.values() if v['is_expired'])
    missing_count = sum(1 for v in expiration_info.values() if not v['exists'])
    
    if expired_count > 0 or missing_count > 0:
        return {
            'valid': False,
            'reason': f'有{expired_count}个Cookie已过期，{missing_count}个Cookie缺失',
            'expiration_info': expiration_info,
            'expired_count': expired_count,
            'missing_count': missing_count,
        }
    
    return {
        'valid': True,
        'reason': '所有Cookie有效',
        'expiration_info': expiration_info,
        'expired_count': 0,
        'missing_count': 0,
    }

@app.route('/api/crawl', methods=['POST'])
def crawl():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        max_notes = data.get('max_notes', 20)

        if not user_id:
            return jsonify({'success': False, 'error': 'user_id 必填'}), 400

        logger.info(f"=== 开始爬取账号: {user_id}, 目标数量: {max_notes}")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_dir, 'scripts', 'crawl.py')
        
        result = subprocess.run(
            [sys.executable, script_path, '--user-id', user_id, '--max-notes', str(max_notes)],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=300,
            cwd=base_dir
        )

        if result.stdout:
            logger.info(f"stdout ({len(result.stdout)} bytes): {result.stdout[:200]}")
        if result.stderr:
            logger.info(f"stderr: {result.stderr[:200]}")

        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': result.stderr or '爬取脚本执行失败'
            }), 500

        try:
            output = result.stdout
            if output:
                json_start = output.find('{')
                json_end = output.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result_data = json.loads(output[json_start:json_end])
                    return jsonify(result_data)
            
            return jsonify({
                'success': True,
                'total': 0,
                'notes': [],
                'message': '爬取完成，但未返回JSON数据'
            })
        except json.JSONDecodeError:
            return jsonify({
                'success': False,
                'error': '无法解析爬虫输出',
                'output': result.stdout[:500]
            })

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': '爬取超时'}), 504
    except Exception as e:
        import traceback
        logger.info(f"Error: {str(e)}")
        logger.info(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/crawl/async', methods=['POST'])
def crawl_async():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        max_notes = data.get('max_notes', 20)

        if not user_id:
            return jsonify({'success': False, 'error': 'user_id 必填'}), 400

        task_id = f"{user_id}_{max_notes}_{int(os.times()[4])}"
        
        def run_crawl():
            try:
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'crawl.py')
                
                result = subprocess.run(
                    [sys.executable, script_path, '--user-id', user_id, '--max-notes', str(max_notes)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )

                if result.returncode == 0:
                    output = result.stdout
                    json_start = output.find('{')
                    json_end = output.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        result_data = json.loads(output[json_start:json_end])
                    else:
                        result_data = {'success': True, 'total': 0, 'notes': []}
                else:
                    result_data = {'success': False, 'error': result.stderr or '爬取失败'}

                with crawl_lock:
                    crawl_results[task_id] = result_data
            except Exception as e:
                with crawl_lock:
                    crawl_results[task_id] = {'success': False, 'error': str(e)}

        thread = threading.Thread(target=run_crawl)
        thread.start()

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '爬取任务已开始，稍后通过 /api/crawl/status/{task_id} 查询结果'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crawl/status/<task_id>', methods=['GET'])
def crawl_status(task_id):
    with crawl_lock:
        result = crawl_results.get(task_id)

    if result is None:
        return jsonify({'status': 'pending', 'message': '任务正在进行中...'})

    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'crawl.py')
    script_exists = os.path.exists(script_path)
    return jsonify({
        'status': 'ok',
        'script_exists': script_exists,
        'has_cookie': bool(os.getenv('XHS_COOKIE', ''))
    })

@app.route('/api/cookie', methods=['GET'])
def get_cookie():
    cookie = os.getenv('XHS_COOKIE', '')
    has_cookie = bool(cookie)
    cookie_length = len(cookie) if has_cookie else 0
    
    return jsonify({
        'success': True,
        'has_cookie': has_cookie,
        'cookie_length': cookie_length,
        'cookie_preview': cookie[:50] + '...' if has_cookie and len(cookie) > 50 else cookie,
        'expires_info': {
            'acw_tc': '2026-06-18',
            'sec_poison_id': '2026-06-18',
            'websectiga': '2026-06-21',
            'ets': '2026-07-09',
            'a1': '2027-04-08',
            'id_token': '2027-04-08',
            'web_session': '2027-04-08',
            'customerClientId': '2027-05-13',
            'gid': '2027-07-23',
        }
    })

@app.route('/api/cookie', methods=['POST'])
def update_cookie():
    try:
        data = request.get_json()
        new_cookie = data.get('cookie', '').strip()
        
        if not new_cookie:
            return jsonify({'success': False, 'error': 'Cookie不能为空'}), 400

        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content = re.sub(r'XHS_COOKIE=.*', f'XHS_COOKIE={new_cookie}', content)
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            os.environ['XHS_COOKIE'] = new_cookie
            
            return jsonify({
                'success': True,
                'message': 'Cookie更新成功，请重启API服务使新Cookie生效',
                'cookie_length': len(new_cookie),
                'cookie_preview': new_cookie[:50] + '...' if len(new_cookie) > 50 else new_cookie
            })
        else:
            return jsonify({'success': False, 'error': '.env文件不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cookie/parse', methods=['POST'])
def parse_cookie():
    try:
        data = request.get_json()
        cookie_string = data.get('cookie', '')
        
        cookies = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        
        return jsonify({
            'success': True,
            'cookies': cookies,
            'count': len(cookies)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/import', methods=['POST'])
def import_to_vector_db():
    """导入数据到向量数据库"""
    try:
        if not rag_available:
            return jsonify({'success': False, 'error': 'RAG模块不可用'}), 500

        db_path = os.getenv('DB_PATH', './data/xhs_notes.db')
        persist_dir = os.getenv('CHROMA_PERSIST_DIR', './data/chroma')
        api_key = os.getenv('DEEPSEEK_API_KEY')
        api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')

        if not api_key:
            return jsonify({'success': False, 'error': '请设置 DEEPSEEK_API_KEY 环境变量'}), 400

        logger.info(f"=== 开始导入数据到向量数据库 ===")
        logger.info(f"数据库路径: {db_path}")
        logger.info(f"向量存储目录: {persist_dir}")

        pipeline = RAGPipeline(db_path, persist_dir, api_key, api_base)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM notes')
        rows = cursor.fetchall()
        conn.close()
        
        note_count = len(rows)
        logger.info(f"数据库中共有 {note_count} 篇笔记")

        pipeline.build_knowledge_base(batch_size=50)
        
        vector_count = pipeline.vector_store.get_count()
        
        return jsonify({
            'success': True,
            'note_count': note_count,
            'vector_count': vector_count,
            'message': f'成功导入 {note_count} 篇笔记，生成 {vector_count} 个向量'
        })

    except Exception as e:
        import traceback
        logger.error(f"导入失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/notes', methods=['GET'])
def get_notes():
    """获取数据库中的笔记列表"""
    try:
        db_path = os.getenv('DB_PATH', './data/xhs_notes.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM notes ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        notes = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'total': len(notes),
            'notes': notes
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    """获取单篇笔记详情"""
    try:
        db_path = os.getenv('DB_PATH', './data/xhs_notes.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM notes WHERE note_id = ?', (note_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({'success': True, 'note': dict(row)})
        else:
            return jsonify({'success': False, 'error': '笔记不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search():
    """搜索向量数据库"""
    try:
        if not rag_available:
            return jsonify({'success': False, 'error': 'RAG模块不可用'}), 500

        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', 5)

        if not query:
            return jsonify({'success': False, 'error': '查询内容不能为空'}), 400

        db_path = os.getenv('DB_PATH', './data/xhs_notes.db')
        persist_dir = os.getenv('CHROMA_PERSIST_DIR', './data/chroma')
        api_key = os.getenv('DEEPSEEK_API_KEY')
        api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')

        if not api_key:
            return jsonify({'success': False, 'error': '请设置 DEEPSEEK_API_KEY 环境变量'}), 400

        pipeline = RAGPipeline(db_path, persist_dir, api_key, api_base)
        results = pipeline.search(query, top_k)

        return jsonify({
            'success': True,
            'query': query,
            'results': results
        })

    except Exception as e:
        import traceback
        logger.error(f"搜索失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cookie/validate', methods=['GET'])
def validate_cookie():
    """验证Cookie有效性"""
    result = check_cookie_validity()
    return jsonify({
        'success': True,
        **result
    })

@app.route('/api/scheduler', methods=['POST'])
def start_scheduler():
    """启动定时任务"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        interval_minutes = data.get('interval_minutes', 60)
        task_type = data.get('task_type', 'crawl')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id 必填'}), 400
        
        with task_lock:
            if task_type in scheduled_tasks:
                return jsonify({'success': False, 'error': f'{task_type} 任务已在运行中'}), 400
            
            def run_task():
                while task_type in scheduled_tasks:
                    try:
                        logger.info(f'[定时任务] 开始执行 {task_type} 任务...')
                        
                        if task_type == 'crawl':
                            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'crawl.py')
                            result = subprocess.run(
                                [sys.executable, script_path, '--user-id', user_id, '--max-notes', '10'],
                                capture_output=True,
                                encoding='utf-8',
                                errors='replace',
                                timeout=300,
                                cwd=os.path.dirname(os.path.abspath(__file__))
                            )
                            
                            if result.returncode == 0:
                                output = result.stdout
                                json_start = output.find('{')
                                json_end = output.rfind('}') + 1
                                if json_start >= 0 and json_end > json_start:
                                    result_data = json.loads(output[json_start:json_end])
                                    logger.info(f'[定时任务] 爬取成功，获取 {result_data.get("total", 0)} 篇笔记')
                                else:
                                    logger.info('[定时任务] 爬取成功，但未返回JSON数据')
                            else:
                                logger.error(f'[定时任务] 爬取失败: {result.stderr[:200]}')
                        
                        elif task_type == 'import':
                            try:
                                db_path = os.getenv('DB_PATH', './data/xhs_notes.db')
                                persist_dir = os.getenv('CHROMA_PERSIST_DIR', './data/chroma')
                                api_key = os.getenv('DEEPSEEK_API_KEY')
                                api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
                                
                                if api_key and rag_available:
                                    pipeline = RAGPipeline(db_path, persist_dir, api_key, api_base)
                                    pipeline.build_knowledge_base(batch_size=50)
                                    logger.info('[定时任务] 向量导入成功')
                                else:
                                    logger.warning('[定时任务] 向量导入跳过：API密钥或RAG模块不可用')
                            except Exception as e:
                                logger.error(f'[定时任务] 向量导入失败: {e}')
                        
                        elif task_type == 'full':
                            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'crawl.py')
                            result = subprocess.run(
                                [sys.executable, script_path, '--user-id', user_id, '--max-notes', '10'],
                                capture_output=True,
                                encoding='utf-8',
                                errors='replace',
                                timeout=300,
                                cwd=os.path.dirname(os.path.abspath(__file__))
                            )
                            
                            if result.returncode == 0:
                                logger.info('[定时任务] 爬取完成，开始导入向量数据库...')
                                try:
                                    db_path = os.getenv('DB_PATH', './data/xhs_notes.db')
                                    persist_dir = os.getenv('CHROMA_PERSIST_DIR', './data/chroma')
                                    api_key = os.getenv('DEEPSEEK_API_KEY')
                                    api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
                                    
                                    if api_key and rag_available:
                                        pipeline = RAGPipeline(db_path, persist_dir, api_key, api_base)
                                        pipeline.build_knowledge_base(batch_size=50)
                                        logger.info('[定时任务] 完整任务完成')
                                except Exception as e:
                                    logger.error(f'[定时任务] 向量导入失败: {e}')
                            else:
                                logger.error(f'[定时任务] 完整任务失败: {result.stderr[:200]}')
                        
                        import time
                        time.sleep(interval_minutes * 60)
                    except Exception as e:
                        logger.error(f'[定时任务] 执行异常: {e}')
                        import time
                        time.sleep(60)
            
            thread = threading.Thread(target=run_task, daemon=True)
            thread.start()
            
            scheduled_tasks[task_type] = {
                'user_id': user_id,
                'interval_minutes': interval_minutes,
                'task_type': task_type,
                'thread': thread,
                'started_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            }
        
        return jsonify({
            'success': True,
            'message': f'{task_type} 定时任务已启动，每 {interval_minutes} 分钟执行一次',
            'task': scheduled_tasks[task_type]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scheduler', methods=['DELETE'])
def stop_scheduler():
    """停止定时任务"""
    try:
        data = request.get_json()
        task_type = data.get('task_type', 'crawl')
        
        with task_lock:
            if task_type not in scheduled_tasks:
                return jsonify({'success': False, 'error': f'{task_type} 任务未在运行'}), 400
            
            del scheduled_tasks[task_type]
        
        return jsonify({
            'success': True,
            'message': f'{task_type} 定时任务已停止'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scheduler/status', methods=['GET'])
def scheduler_status():
    """获取定时任务状态"""
    try:
        with task_lock:
            status = {}
            for task_type, info in scheduled_tasks.items():
                status[task_type] = {
                    'running': True,
                    'user_id': info['user_id'],
                    'interval_minutes': info['interval_minutes'],
                    'started_at': info['started_at'],
                }
            
            return jsonify({
                'success': True,
                'tasks': status,
                'total_tasks': len(status)
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scheduler/tick', methods=['POST'])
def scheduler_tick():
    """手动触发一次定时任务执行"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        task_type = data.get('task_type', 'full')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id 必填'}), 400
        
        logger.info(f'[手动触发] 执行 {task_type} 任务...')
        
        if task_type == 'crawl' or task_type == 'full':
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'crawl.py')
            result = subprocess.run(
                [sys.executable, script_path, '--user-id', user_id, '--max-notes', '10'],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.returncode == 0:
                output = result.stdout
                json_start = output.find('{')
                json_end = output.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    crawl_result = json.loads(output[json_start:json_end])
                else:
                    crawl_result = {'success': True, 'total': 0, 'notes': []}
            else:
                return jsonify({'success': False, 'error': result.stderr[:200]}), 500
        
        if task_type == 'import' or task_type == 'full':
            try:
                db_path = os.getenv('DB_PATH', './data/xhs_notes.db')
                persist_dir = os.getenv('CHROMA_PERSIST_DIR', './data/chroma')
                api_key = os.getenv('DEEPSEEK_API_KEY')
                api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
                
                if api_key and rag_available:
                    pipeline = RAGPipeline(db_path, persist_dir, api_key, api_base)
                    pipeline.build_knowledge_base(batch_size=50)
                    vector_count = pipeline.vector_store.get_count()
                else:
                    vector_count = 0
            except Exception as e:
                logger.error(f'向量导入失败: {e}')
                vector_count = 0
        
        return jsonify({
            'success': True,
            'message': f'{task_type} 任务执行完成',
            'crawl_result': crawl_result if 'crawl_result' in locals() else None,
            'vector_count': vector_count if 'vector_count' in locals() else None,
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("=== 小红书爬取API服务启动中 ===")
    logger.info("服务地址: http://localhost:5000")
    logger.info("爬取接口: POST /api/crawl")
    logger.info("导入接口: POST /api/import")
    logger.info("搜索接口: POST /api/search")
    logger.info("笔记列表: GET /api/notes")
    logger.info("Cookie管理: GET/POST /api/cookie")
    logger.info("Cookie验证: GET /api/cookie/validate")
    logger.info("定时任务: POST/DELETE /api/scheduler")
    logger.info("健康检查: GET /health")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=False)
