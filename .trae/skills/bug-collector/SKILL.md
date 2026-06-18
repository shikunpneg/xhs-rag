---
name: "bug-collector"
description: "检查和收集代码中的bug，记录错误日志，追踪异常信息。Invoke when user reports errors, bugs, or asks to check/collect bug information."
---

# Bug Collector Skill

## 功能概述

该skill用于检查和收集代码中的bug，提供以下功能：

1. **错误日志记录** - 捕获并记录运行时异常
2. **代码静态分析** - 检查常见bug模式
3. **异常追踪** - 详细记录错误堆栈信息
4. **Bug报告生成** - 汇总所有发现的问题

## 使用场景

- 用户报告运行时错误
- 用户遇到编码问题（如GBK编码错误）
- 用户请求检查代码中的bug
- 自动化测试失败时分析原因
- 需要收集和追踪异常信息

## 核心组件

### 1. BugLogger 类
用于记录错误日志到文件

```python
class BugLogger:
    def __init__(self, log_path='./logs/bugs.log'):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    def log_error(self, error_type, message, stack_trace=None):
        """记录错误日志"""
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now().isoformat()}] {error_type}: {message}\n')
            if stack_trace:
                f.write(f'  Stack Trace:\n{stack_trace}\n')
            f.write('-' * 80 + '\n')
```

### 2. BugChecker 类
用于静态分析代码中的常见bug

```python
class BugChecker:
    def check_encoding_issues(self, text):
        """检查编码问题"""
        issues = []
        try:
            text.encode('gbk')
        except UnicodeEncodeError as e:
            issues.append(f'GBK编码错误: {e}')
        return issues
    
    def check_empty_values(self, data, required_fields):
        """检查必填字段是否为空"""
        issues = []
        for field in required_fields:
            if field not in data or not data[field]:
                issues.append(f'字段 {field} 为空')
        return issues
```

### 3. BugReporter 类
用于生成bug报告

```python
class BugReporter:
    def generate_report(self, bugs):
        """生成bug报告"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_bugs': len(bugs),
            'bugs': bugs
        }
        return report
```

## 使用方法

### 在代码中集成

```python
from bug_collector import BugLogger, BugChecker

logger = BugLogger()
checker = BugChecker()

try:
    # 执行可能出错的代码
    result = some_function()
except Exception as e:
    logger.log_error(type(e).__name__, str(e), traceback.format_exc())
    # 检查可能的原因
    issues = checker.check_encoding_issues(str(e))
    if issues:
        logger.log_error('EncodingIssue', ', '.join(issues))
```

### 命令行使用

```bash
# 检查编码问题
python -m bug_collector check-encoding --text "包含emoji的文本🙄"

# 生成bug报告
python -m bug_collector generate-report --log ./logs/bugs.log
```

## 常见Bug类型

### 编码问题
- GBK无法编码Unicode字符（如emoji）
- 文件读写未指定UTF-8编码

### 数据验证问题
- 必填字段为空
- 数据类型不匹配
- 边界条件未处理

### 网络请求问题
- 请求超时未处理
- 响应解析失败
- Cookie过期或无效

### 数据库问题
- 连接失败
- 事务未提交
- 查询参数错误

## 最佳实践

1. **全局异常捕获** - 在关键入口添加try-except
2. **详细日志** - 记录完整的堆栈信息
3. **错误分类** - 按类型分类错误便于分析
4. **定期检查** - 定时运行静态分析工具
5. **用户反馈** - 收集用户报告的bug
