import os, sys, subprocess, json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

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

        print("\n=== 开始爬取账号:", user_id)
        print("目标数量:", max_notes)
        sys.stdout.flush()

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

        print(f"returncode: {result.returncode}")
        if result.stdout:
            print(f"stdout ({len(result.stdout)} bytes): {result.stdout[:200]}")
        if result.stderr:
            print(f"stderr: {result.stderr[:200]}")
        sys.stdout.flush()

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
        except json.JSONDecodeError as e:
            return jsonify({
                'success': False,
                'error': f'无法解析爬虫输出: {str(e)}',
                'output': result.stdout[:500] if result.stdout else 'None'
            })

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': '爬取超时'}), 504
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        sys.stdout.flush()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("=== 测试Flask爬取API ===")
    print("服务地址: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=False)
