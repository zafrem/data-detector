# 快速入门指南

## 基本用法

### 库 API

```python
from datadetector import Engine, load_registry

# 从特定文件加载模式
registry = load_registry(paths=["patterns/common.yml", "patterns/kr.yml"])
# 或从目录加载所有模式
registry = load_registry(paths=["patterns/"])

engine = Engine(registry)

# 验证
is_valid = engine.validate("010-1234-5678", "kr/mobile_01")
print(is_valid)  # True

# 查找 PII（搜索所有加载的模式）
results = engine.find("My phone: 01012345678, email: test@example.com")
for match in results.matches:
    print(f"Found {match.category} at position {match.start}-{match.end}")

# 脱敏
redacted = engine.redact(
    "SSN: 900101-1234567",
    namespaces=["kr"],
    strategy="mask"
)
print(redacted.redacted_text)
```

### CLI 用法

```bash
# 在文本中查找 PII
data-detector find --ns kr/mobile --file sample.txt

# 脱敏 PII
data-detector redact --in input.log --out redacted.log --ns kr us

# 启动服务器
data-detector serve --port 8080 --config config.yml
```

### REST API

启动服务器：
```bash
data-detector serve --port 8080
```

使用 API：
```bash
# 查找 PII
curl -X POST http://localhost:8080/find \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "namespaces": ["kr"]}'

# 验证
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "ns_id": "kr/mobile"}'

# 脱敏
curl -X POST http://localhost:8080/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "My SSN is 900101-1234567", "namespaces": ["kr"]}'

# 健康检查
curl http://localhost:8080/health
```

## 后续步骤

- [模式结构](patterns.md) - 了解如何定义模式
- [配置](configuration.md) - 配置服务器和注册表
- [自定义模式](custom-patterns.md) - 创建您自己的模式
- [验证函数](verification.md) - 添加自定义验证逻辑
