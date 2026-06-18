"""
Bug Collector - 代码错误检查和收集工具
"""

import os
import sys
import json
import traceback
from datetime import datetime
from typing import List, Dict, Any


class BugLogger:
    """错误日志记录器"""

    def __init__(self, log_path: str = './logs/bugs.log'):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def log_error(self, error_type: str, message: str, stack_trace: str = None):
        """记录错误日志"""
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(f'[{datetime.now().isoformat()}] {error_type}: {message}\n')
                if stack_trace:
                    f.write(f'  Stack Trace:\n{stack_trace}\n')
                f.write('-' * 80 + '\n')
        except Exception as e:
            print(f'日志写入失败: {e}')

    def log_exception(self, exception: Exception):
        """记录异常"""
        self.log_error(
            type(exception).__name__,
            str(exception),
            traceback.format_exc()
        )


class BugChecker:
    """代码静态分析检查器"""

    def check_encoding_issues(self, text: str) -> List[str]:
        """检查编码问题"""
        issues = []
        if not isinstance(text, str):
            return issues

        try:
            text.encode('gbk')
        except UnicodeEncodeError as e:
            issues.append(f'GBK编码错误: {e}')

        try:
            text.encode('ascii')
        except UnicodeEncodeError:
            issues.append('包含非ASCII字符')

        return issues

    def check_empty_values(self, data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """检查必填字段是否为空"""
        issues = []
        if not isinstance(data, dict):
            return issues

        for field in required_fields:
            if field not in data or not data[field]:
                issues.append(f'字段 "{field}" 为空或不存在')

        return issues

    def check_file_encoding(self, file_path: str) -> List[str]:
        """检查文件编码"""
        issues = []
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            try:
                content.decode('utf-8')
            except UnicodeDecodeError:
                issues.append(f'文件 {file_path} 不是UTF-8编码')

        except Exception as e:
            issues.append(f'无法读取文件 {file_path}: {e}')

        return issues

    def analyze_error_message(self, error_msg: str) -> Dict[str, Any]:
        """分析错误消息"""
        analysis = {
            'error_type': 'Unknown',
            'severity': 'medium',
            'possible_causes': [],
            'suggestions': []
        }

        if 'gbk' in error_msg.lower() and 'encode' in error_msg.lower():
            analysis['error_type'] = 'EncodingError'
            analysis['severity'] = 'high'
            analysis['possible_causes'].append('Windows默认GBK编码无法处理Unicode字符（如emoji）')
            analysis['suggestions'].append('在脚本开头添加: sys.stdout.reconfigure(encoding="utf-8")')
            analysis['suggestions'].append('使用UTF-8编码读写文件')

        elif 'decode' in error_msg.lower():
            analysis['error_type'] = 'DecodingError'
            analysis['severity'] = 'high'
            analysis['possible_causes'].append('文件编码与读取编码不匹配')
            analysis['suggestions'].append('确认文件实际编码')
            analysis['suggestions'].append('使用正确的编码打开文件')

        elif 'cookie' in error_msg.lower():
            analysis['error_type'] = 'CookieError'
            analysis['severity'] = 'high'
            analysis['possible_causes'].append('Cookie无效或已过期')
            analysis['possible_causes'].append('Cookie格式不正确')
            analysis['suggestions'].append('重新获取Cookie')
            analysis['suggestions'].append('检查Cookie是否完整')

        elif 'network' in error_msg.lower() or 'timeout' in error_msg.lower():
            analysis['error_type'] = 'NetworkError'
            analysis['severity'] = 'medium'
            analysis['possible_causes'].append('网络连接问题')
            analysis['possible_causes'].append('服务器响应超时')
            analysis['suggestions'].append('检查网络连接')
            analysis['suggestions'].append('增加超时时间')

        elif 'sqlite' in error_msg.lower() or 'database' in error_msg.lower():
            analysis['error_type'] = 'DatabaseError'
            analysis['severity'] = 'high'
            analysis['possible_causes'].append('数据库连接失败')
            analysis['possible_causes'].append('SQL语法错误')
            analysis['suggestions'].append('检查数据库文件路径')
            analysis['suggestions'].append('验证SQL语句')

        elif 'index out of range' in error_msg.lower():
            analysis['error_type'] = 'IndexError'
            analysis['severity'] = 'high'
            analysis['possible_causes'].append('列表索引越界')
            analysis['possible_causes'].append('空列表访问')
            analysis['suggestions'].append('添加边界检查')
            analysis['suggestions'].append('验证列表非空')

        elif 'keyerror' in error_msg.lower():
            analysis['error_type'] = 'KeyError'
            analysis['severity'] = 'high'
            analysis['possible_causes'].append('字典键不存在')
            analysis['suggestions'].append('使用dict.get()方法')
            analysis['suggestions'].append('验证键存在')

        elif 'typeerror' in error_msg.lower():
            analysis['error_type'] = 'TypeError'
            analysis['severity'] = 'high'
            analysis['possible_causes'].append('类型不匹配')
            analysis['suggestions'].append('检查变量类型')
            analysis['suggestions'].append('添加类型检查')

        return analysis


class BugReporter:
    """Bug报告生成器"""

    def __init__(self, logger: BugLogger = None):
        self.logger = logger or BugLogger()
        self.bugs: List[Dict[str, Any]] = []

    def add_bug(self, error_type: str, message: str, severity: str = 'medium',
                possible_causes: List[str] = None, suggestions: List[str] = None):
        """添加bug记录"""
        bug = {
            'id': len(self.bugs) + 1,
            'error_type': error_type,
            'message': message,
            'severity': severity,
            'possible_causes': possible_causes or [],
            'suggestions': suggestions or [],
            'reported_at': datetime.now().isoformat()
        }
        self.bugs.append(bug)
        self.logger.log_error(error_type, message)

    def generate_report(self) -> Dict[str, Any]:
        """生成bug报告"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_bugs': len(self.bugs),
            'high_severity': len([b for b in self.bugs if b['severity'] == 'high']),
            'medium_severity': len([b for b in self.bugs if b['severity'] == 'medium']),
            'low_severity': len([b for b in self.bugs if b['severity'] == 'low']),
            'bugs': self.bugs
        }
        return report

    def save_report(self, file_path: str = './logs/bug_report.json'):
        """保存报告到文件"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        report = self.generate_report()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def print_report(self):
        """打印报告"""
        report = self.generate_report()
        print(f'===== Bug Report ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")}) =====')
        print(f'Total Bugs: {report["total_bugs"]}')
        print(f'High: {report["high_severity"]}, Medium: {report["medium_severity"]}, Low: {report["low_severity"]}')
        print()

        for bug in self.bugs:
            print(f'[{bug["severity"].upper()}] Bug #{bug["id"]}: {bug["error_type"]}')
            print(f'  Message: {bug["message"]}')
            if bug['possible_causes']:
                print(f'  Possible Causes:')
                for cause in bug['possible_causes']:
                    print(f'    - {cause}')
            if bug['suggestions']:
                print(f'  Suggestions:')
                for suggestion in bug['suggestions']:
                    print(f'    - {suggestion}')
            print()


def analyze_error(error_msg: str) -> Dict[str, Any]:
    """分析错误消息并返回详细信息"""
    checker = BugChecker()
    analysis = checker.analyze_error_message(error_msg)

    reporter = BugReporter()
    reporter.add_bug(
        analysis['error_type'],
        error_msg,
        analysis['severity'],
        analysis['possible_causes'],
        analysis['suggestions']
    )

    return reporter.generate_report()


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='Bug Collector Tool')
    parser.add_argument('--analyze', type=str, help='分析错误消息')
    parser.add_argument('--check-encoding', type=str, help='检查文本编码')
    parser.add_argument('--generate-report', action='store_true', help='生成bug报告')
    parser.add_argument('--log-file', type=str, default='./logs/bugs.log', help='日志文件路径')

    args = parser.parse_args()

    if args.analyze:
        report = analyze_error(args.analyze)
        print(json.dumps(report, ensure_ascii=False, indent=2))

    elif args.check_encoding:
        checker = BugChecker()
        issues = checker.check_encoding_issues(args.check_encoding)
        if issues:
            print('发现编码问题:')
            for issue in issues:
                print(f'  - {issue}')
        else:
            print('未发现编码问题')

    elif args.generate_report:
        reporter = BugReporter(BugLogger(args.log_file))
        reporter.print_report()


if __name__ == '__main__':
    main()
