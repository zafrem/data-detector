# RAG 安全 - 快速入门指南

> **快速摘要**：在 5 分钟内开始使用 RAG 系统的三层 PII 保护。

---

## 📋 目录

- [概述](#概述)
- [快速入门](#快速入门)
- [核心概念](#核心概念)
- [示例](#示例)
- [脱敏策略](#脱敏策略)
- [配置](#配置)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)
- [相关文档](#相关文档)

---

## 概述

### 什么是 RAG 安全？

RAG 安全为检索增强生成系统提供**三层 PII 保护**。它在 RAG 管道的每个阶段扫描和清理敏感信息：用户查询、文档存储和 LLM 响应。

**主要功能：**
- ✅ 三层保护（输入 → 存储 → 输出）
- ✅ 多种脱敏策略（MASK、FAKE、TOKENIZE、HASH）
- ✅ 基于 YAML 的配置
- ✅ 快速性能（每个文档 < 15ms）
- ✅ 可逆令牌化以供授权访问
- ✅ REST API 就绪

**用例：**
- 客户支持聊天机器人
- 内部知识库
- 公共文档搜索
- 合规驱动的 RAG 系统

---

## 快速入门

### 安装

```bash
pip install data-detector
```

### 基本示例（3 行）

```python
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

# 初始化
registry = load_registry()
engine = Engine(registry)
security = RAGSecurityMiddleware(engine)

# 扫描查询（第 1 层）
result = await security.scan_query("Email john@example.com about order")
print(f"Safe query: {result.sanitized_text}")
# 输出: "Safe query: Email [EMAIL] about order"
```

### 完整示例（全部 3 层）

```python
import asyncio
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

async def main():
    # 初始化
    registry = load_registry()
    engine = Engine(registry)
    security = RAGSecurityMiddleware(engine)

    # 第 1 层：输入扫描
    query = "Status for customer john@example.com?"
    input_result = await security.scan_query(query, namespaces=["comm"])

    if input_result.blocked:
        return "Query blocked"

    print(f"✓ Safe query: {input_result.sanitized_text}")

    # 第 2 层：存储扫描
    document = "Customer: john@example.com, Phone: 555-0123"
    doc_result = await security.scan_document(document, namespaces=["comm"])

    print(f"✓ Safe for vector DB: {doc_result.sanitized_text}")

    # 存储到向量数据库
    # vector_db.add(doc_result.sanitized_text)

    # 第 3 层：输出扫描
    llm_response = "The email is john@example.com"
    output_result = await security.scan_response(llm_response, namespaces=["comm"])

    if output_result.blocked:
        print("⚠ Response blocked due to PII leak")
    else:
        print(f"✓ Safe response: {output_result.sanitized_text}")

asyncio.run(main())
```

**预期输出：**
```
✓ Safe query: Status for customer [EMAIL]?
✓ Safe for vector DB: Customer: [EMAIL], Phone: [PHONE]
⚠ Response blocked due to PII leak
```

---

## 核心概念

### 三层架构

```
用户查询
    ↓
┌─────────────────────────┐
│ 第 1 层：输入           │  ← RAG 之前扫描查询
│ 动作：清理              │
└─────────────────────────┘
    ↓ (安全查询)
┌─────────────────────────┐
│ 向量数据库搜索          │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 第 2 层：存储           │  ← 索引之前扫描文档
│ 动作：令牌化            │
└─────────────────────────┘
    ↓ (清理后的文档)
┌─────────────────────────┐
│ LLM 处理                │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 第 3 层：输出           │  ← 返回之前扫描响应
│ 动作：阻止              │
└─────────────────────────┘
    ↓
安全响应
```

### 安全策略

每层都有可配置的安全策略：

```python
from datadetector.rag_models import SecurityPolicy, SecurityAction, SecurityLayer

policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    action=SecurityAction.SANITIZE,  # block | sanitize | warn | allow
    severity_threshold=SeverityLevel.MEDIUM,
    redaction_strategy=RedactionStrategy.FAKE
)
```

---

## 示例

### 示例 1：阻止敏感查询

**场景：** 拒绝包含高严重性 PII 的查询（例如 SSN）。

```python
from datadetector.rag_models import SecurityPolicy, SecurityAction, SecurityLayer, SeverityLevel

# 创建严格的阻止策略
strict_policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    action=SecurityAction.BLOCK,
    severity_threshold=SeverityLevel.HIGH
)

# 应用策略
security.update_policy(SecurityLayer.INPUT, strict_policy)

# 使用敏感查询测试
result = await security.scan_query("Process SSN 123-45-6789", namespaces=["us"])

print(f"Blocked: {result.blocked}")
print(f"Reason: {result.reason}")
```

**输出：**
```
Blocked: True
Reason: Query contains 1 high-severity PII matches
```

### 示例 2：清理向量数据库的文档

**场景：** 在索引之前使用 FAKE 数据从文档中删除 PII。

```python
from datadetector.models import RedactionStrategy
from datadetector.rag_models import SecurityPolicy, SecurityLayer

# 使用 FAKE 策略的策略（更适合嵌入）
storage_policy = SecurityPolicy(
    layer=SecurityLayer.STORAGE,
    action=SecurityAction.SANITIZE,
    redaction_strategy=RedactionStrategy.FAKE
)

security.update_policy(SecurityLayer.STORAGE, storage_policy)

# 扫描文档
document = """
Customer: John Doe
Email: john@example.com
Phone: 555-0123
"""

result = await security.scan_document(document, namespaces=["comm"])

print(f"Original:\n{document}")
print(f"\nSanitized:\n{result.sanitized_text}")

# 存储到向量数据库
# vector_db.add(result.sanitized_text)
```

**输出：**
```
Original:
Customer: John Doe
Email: john@example.com
Phone: 555-0123

Sanitized:
Customer: John Doe
Email: fake123@example.com
Phone: 555-9876
```

### 示例 3：可逆令牌化

**场景：** 为内部系统使用可逆令牌。

```python
from datadetector.tokenization import SecureTokenizer

tokenizer = SecureTokenizer(engine)

# 令牌化文档
document = "Email: john@example.com, SSN: 123-45-6789"
sanitized, token_map = tokenizer.tokenize_with_map(document, namespaces=["comm", "us"])

print(f"Tokenized: {sanitized}")
print(f"Token map: {token_map.tokens}")

# 在向量数据库中存储清理后的内容
# vector_db.add(sanitized)

# 安全存储令牌映射（加密）
# secure_db.save(token_map, encrypted=True)

# 稍后，如果授权则反向
detokenized = tokenizer.detokenize(sanitized, token_map)
print(f"Detokenized: {detokenized}")
```

**输出：**
```
Tokenized: Email: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]
Token map: {'[TOKEN:comm:email:0]': 'john@example.com', '[TOKEN:us:ssn:1]': '123-45-6789'}
Detokenized: Email: john@example.com, SSN: 123-45-6789
```

---

## 脱敏策略

### 策略比较

| 策略 | 速度 | 可逆 | 最适合 | 示例 |
|----------|-------|------------|----------|---------|
| **MASK** | ⚡ 最快 | ❌ 否 | 输出阻止 | `***@***.com` |
| **FAKE** | ⚡ 快 | ❌ 否 | 存储（RAG） | `fake@example.com` |
| **TOKENIZE** | ⚡ 快 | ✅ 是 | 合规 | `[TOKEN:0]` |
| **HASH** | ⚡ 快 | ❌ 否 | 分析 | `[HASH:a1b2c3]` |

### MASK 策略

```python
from datadetector.models import RedactionStrategy

result = engine.redact(
    "Email: john@example.com",
    strategy=RedactionStrategy.MASK
)
print(result.redacted_text)
# 输出: "Email: ***@***.com"
```

**优点：** 简单、快速
**缺点：** 嵌入效果差、不自然

### FAKE 策略

```python
result = engine.redact(
    "Email: john@example.com",
    strategy=RedactionStrategy.FAKE
)
print(result.redacted_text)
# 输出: "Email: fake123@example.com"
```

**优点：** 自然、更好的嵌入
**缺点：** 稍慢、需要 faker 库

### TOKENIZE 策略

```python
from datadetector.tokenization import SecureTokenizer

tokenizer = SecureTokenizer(engine)
sanitized, token_map = tokenizer.tokenize_with_map("Email: john@example.com")
print(sanitized)
# 输出: "Email: [TOKEN:comm:email:0]"

# 可以反向
original = tokenizer.detokenize(sanitized, token_map)
print(original)
# 输出: "Email: john@example.com"
```

**优点：** 可逆、安全
**缺点：** 需要令牌映射存储

### HASH 策略

```python
result = engine.redact(
    "Email: john@example.com",
    strategy=RedactionStrategy.HASH
)
print(result.redacted_text)
# 输出: "Email: [HASH:a1b2c3d4e5f6]"
```

**优点：** 最大安全性、单向
**缺点：** 不可逆、用户体验差

---

## 配置

### YAML 配置

编辑 `config/rag_security_policy.yml`：

```yaml
# 输入层
input_layer:
  enabled: true
  action: sanitize
  redaction_strategy: fake  # ← 选择: mask | fake | tokenize | hash
  namespaces:
    - comm
    - us

# 存储层
storage_layer:
  enabled: true
  action: sanitize
  redaction_strategy: tokenize  # ← 选择: mask | fake | tokenize | hash
  preserve_format: true

# 输出层
output_layer:
  enabled: true
  action: block
  redaction_strategy: mask  # ← 选择: mask | fake | tokenize | hash
  severity_threshold: high
```

### 加载配置

```python
from datadetector import load_rag_policy

# 从 YAML 加载
policy_config = load_rag_policy("config/rag_security_policy.yml")

# 使用加载的策略创建中间件
security = RAGSecurityMiddleware(
    engine,
    input_policy=policy_config.get_input_policy(),
    storage_policy=policy_config.get_storage_policy(),
    output_policy=policy_config.get_output_policy()
)
```

### REST API 配置

```bash
# 启动服务器
data-detector serve --port 8080

# 使用 API
curl -X POST http://localhost:8080/rag/scan-query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Email john@example.com",
    "action": "sanitize",
    "namespaces": ["comm"]
  }'
```

---

## 最佳实践

### 1. 每层使用不同的策略

**这样做：**
```python
# ✅ 优化的配置
input_policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    redaction_strategy=RedactionStrategy.FAKE  # 自然查询
)

storage_policy = SecurityPolicy(
    layer=SecurityLayer.STORAGE,
    redaction_strategy=RedactionStrategy.TOKENIZE  # 可逆
)

output_policy = SecurityPolicy(
    layer=SecurityLayer.OUTPUT,
    redaction_strategy=RedactionStrategy.MASK  # 快速阻止
)
```

**原因：** 每层都有不同的要求。输入/存储受益于自然文本，输出需要快速阻止。

### 2. 限制命名空间以提高性能

**这样做：**
```python
# ✅ 仅扫描相关模式
result = await security.scan_query(
    query,
    namespaces=["comm"]  # 仅电子邮件/电话
)
```

**不要这样做：**
```python
# ❌ 不必要地扫描所有模式
result = await security.scan_query(query)  # 所有命名空间
```

**原因：** 仅扫描相关命名空间快 2-3 倍。

### 3. 安全存储令牌映射

**这样做：**
```python
# ✅ 加密和分离存储
from cryptography.fernet import Fernet

cipher = Fernet(encryption_key)
encrypted = cipher.encrypt(json.dumps(token_map.tokens).encode())

# 存储在单独的安全数据库中
secure_db.save(doc_id, encrypted, access_level="admin_only")
```

**不要这样做：**
```python
# ❌ 在向量数据库中存储未加密
vector_db.add({
    'text': sanitized,
    'token_map': token_map.tokens  # 不要！
})
```

**原因：** 令牌映射包含原始 PII，必须加密和访问控制。

---

## 故障排除

### 问题："FakeDataGenerator not available"

**症状：**
- 使用 FAKE 策略时出现警告
- 回退到 MASK 策略

**解决方案：**
```bash
pip install faker
```

**说明：** FAKE 策略需要 `faker` 库来生成真实数据。

### 问题：性能慢

**症状：**
- 响应时间 > 50ms
- CPU 使用率高

**解决方案：**
```python
# 仅用于检测时使用 stop_on_first_match
result = await security.scan_query(
    query,
    namespaces=["comm"],  # 限制命名空间
    stop_on_first_match=True  # 快 2-3 倍
)
```

**说明：** 扫描所有命名空间中的所有模式较慢。限制为相关模式。

### 问题：令牌映射存储

**症状：**
- "Token map not found" 错误
- 无法去令牌化

**解决方案：**
```python
# 确保在去令牌化之前保存令牌映射
sanitized, token_map = tokenizer.tokenize_with_map(text)

# 保存令牌映射
secure_db.save(doc_id, encrypt(token_map.tokens))

# 稍后，在去令牌化之前检索
retrieved_map = decrypt(secure_db.get(doc_id))
detokenized = tokenizer.detokenize(sanitized, TokenMap(tokens=retrieved_map))
```

**说明：** 必须明确保存和检索令牌映射以进行去令牌化。

---

## 相关文档

**核心文档：**
- [安装指南](installation.md) - 开始使用 data-detector
- [架构](RAG_SECURITY_ARCHITECTURE.md) - 详细的系统架构

**RAG 安全：**
- [RAG 安全架构](RAG_SECURITY_ARCHITECTURE.md) - 完整的架构指南
- [RAG 集成](rag-integration.md) - 框架集成指南
- [令牌映射存储](TOKEN_MAP_STORAGE.md) - 安全令牌存储指南

**高级主题：**
- [自定义模式](custom-patterns.md) - 创建自定义 PII 模式
- [验证函数](verification.md) - 添加验证逻辑

---

## 支持

- 📖 **完整文档**：[RAG 安全架构](RAG_SECURITY_ARCHITECTURE.md)
- 💻 **示例**：运行 `examples/rag_quickstart.py`
- ⚙️ **配置**：编辑 `config/rag_security_policy.yml`
- 🐛 **问题**：[GitHub Issues](https://github.com/yourusername/data-detector/issues)
- 💬 **讨论**：[GitHub Discussions](https://github.com/yourusername/data-detector/discussions)

---

**最后更新：** 2025-11-29 | **版本：** 0.0.2
