import os, sys, subprocess, json, logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# 配置文件日志
log_file = os.path.join(os.path.dirname(__file__), 'crawl_debug.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

app = Flask(__name__)
CORS(app)

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
        
        logger.info(f"运行脚本: {script_path}")
        
        result = subprocess.run(
            [sys.executable, script_path, '--user-id', user_id, '--max-notes', str(max_notes)],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=300,
            cwd=base_dir
        )

        logger.info(f"returncode: {result.returncode}")
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
                    logger.info(f"成功返回 {len(result_data.get('notes', []))} 条笔记")
                    return jsonify(result_data)
            
            logger.info("未找到JSON数据")
            return jsonify({
                'success': True,
                'total': 0,
                'notes': [],
                'message': '爬取完成，但未返回JSON数据'
            })
        except json.JSONDecodeError as e:
            logger.info(f"JSON解析错误: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'无法解析爬虫输出: {str(e)}',
                'output': result.stdout[:500] if result.stdout else 'None'
            })

    except subprocess.TimeoutExpired:
        logger.info("爬取超时")
        return jsonify({'success': False, 'error': '爬取超时'}), 504
    except Exception as e:
        import traceback
        logger.info(f"错误: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    logger.info("=== 测试Flask爬取API ===")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=False)
