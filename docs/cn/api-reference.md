# API 参考

## Python API

### 加载模式

#### `load_registry(paths=None, validate_schema=True, validate_examples=True)`

从 YAML 文件加载模式到注册表中。

**参数：**
- `paths`（List[str]，可选）：文件或目录路径列表。如果为 None，则加载默认模式。
- `validate_schema`（bool）：是否针对 JSON 模式验证。默认值：True。
- `validate_examples`（bool）：是否针对模式验证示例。默认值：True。

**返回值：** `PatternRegistry`

**示例：**
```python
from datadetector import load_registry

# 从目录加载
registry = load_registry(paths=["patterns/"])

# 加载特定文件
registry = load_registry(paths=["patterns/common.yml", "patterns/kr.yml"])

# 不验证加载
registry = load_registry(
    paths=["patterns/"],
    validate_schema=False,
    validate_examples=False
)
```

### Engine 类

#### `Engine(registry, default_mask_char='*', hash_algorithm='sha256')`

用于 PII 检测、验证和脱敏的核心引擎。

**参数：**
- `registry`（PatternRegistry）：带有加载模式的注册表
- `default_mask_char`（str）：用于掩码的默认字符。默认值：'*'
- `hash_algorithm`（str）：用于哈希策略的哈希算法。默认值：'sha256'

#### `Engine.find(text, namespaces=None, allow_overlaps=False, include_matched_text=False)`

在文本中查找所有 PII 匹配项。

**参数：**
- `text`（str）：要搜索的文本
- `namespaces`（List[str]，可选）：要搜索的命名空间列表。如果为 None，则搜索所有。
- `allow_overlaps`（bool）：是否允许重叠匹配。默认值：False。
- `include_matched_text`（bool）：是否在结果中包含匹配的文本。默认值：False。

**返回值：** `FindResult`

**示例：**
```python
result = engine.find("Phone: 010-1234-5678, Email: test@example.com")
for match in result.matches:
    print(f"{match.category} at {match.start}-{match.end}")
```

#### `Engine.validate(text, ns_id)`

针对特定模式验证文本。

**参数：**
- `text`（str）：要验证的文本
- `ns_id`（str）：完整命名空间/id（例如，"kr/mobile_01"）

**返回值：** `ValidationResult`

**示例：**
```python
result = engine.validate("010-1234-5678", "kr/mobile_01")
print(result.is_valid)  # True 或 False
```

#### `Engine.redact(text, namespaces=None, strategy=None, allow_overlaps=False)`

从文本中脱敏 PII。

**参数：**
- `text`（str）：要脱敏的文本
- `namespaces`（List[str]，可选）：要搜索的命名空间列表。如果为 None，则搜索所有。
- `strategy`（RedactionStrategy，可选）：脱敏策略（mask/hash/tokenize）。默认值：mask。
- `allow_overlaps`（bool）：是否允许重叠匹配。默认值：False。

**返回值：** `RedactionResult`

**示例：**
```python
result = engine.redact(
    "SSN: 900101-1234567",
    namespaces=["kr"],
    strategy="mask"
)
print(result.redacted_text)
```

### 数据模型

#### `FindResult`

查找操作的结果。

**属性：**
- `text`（str）：原始文本
- `matches`（List[Match]）：找到的匹配列表
- `namespaces_searched`（List[str]）：搜索的命名空间
- `has_matches`（bool）：属性 - 如果找到任何匹配则为 True
- `match_count`（int）：属性 - 匹配数

#### `Match`

单个模式匹配结果。

**属性：**
- `ns_id`（str）：完整命名空间/id（例如，"kr/mobile_01"）
- `pattern_id`（str）：模式 ID
- `namespace`（str）：命名空间
- `category`（Category）：PII 类别
- `start`（int）：文本中的开始位置
- `end`（int）：文本中的结束位置
- `matched_text`（str，可选）：匹配的文本（如果策略允许）
- `mask`（str，可选）：掩码模板
- `severity`（Severity）：严重程度级别

#### `ValidationResult`

验证操作的结果。

**属性：**
- `text`（str）：已验证的文本
- `ns_id`（str）：使用的模式命名空间/id
- `is_valid`（bool）：文本是否有效
- `match`（Match，可选）：如果有效则为匹配详细信息

#### `RedactionResult`

脱敏操作的结果。

**属性：**
- `original_text`（str）：原始文本
- `redacted_text`（str）：脱敏 PII 后的文本
- `strategy`（RedactionStrategy）：使用的策略
- `matches`（List[Match]）：已脱敏的匹配
- `redaction_count`（int）：脱敏数

### 验证函数

#### `iban_mod97(value)`

使用 Mod-97 检查算法验证 IBAN。

**参数：**
- `value`（str）：IBAN 字符串

**返回值：** `bool`

#### `luhn(value)`

使用 Luhn 算法验证（mod-10 校验和）。

**参数：**
- `value`（str）：数字字符串

**返回值：** `bool`

#### `register_verification_function(name, func)`

注册自定义验证函数。

**参数：**
- `name`（str）：要注册的名称
- `func`（Callable[[str], bool]）：验证函数

#### `get_verification_function(name)`

按名称获取验证函数。

**参数：**
- `name`（str）：函数名称

**返回值：** `Callable[[str], bool]` 或 `None`

#### `unregister_verification_function(name)`

注销验证函数。

**参数：**
- `name`（str）：函数名称

**返回值：** `bool` - 如果删除则为 True，如果未找到则为 False

## REST API

### POST /find

在文本中查找 PII 匹配项。

**请求：**
```json
{
  "text": "My phone is 010-1234-5678",
  "namespaces": ["kr"],
  "allow_overlaps": false,
  "include_matched_text": false
}
```

**响应：**
```json
{
  "text": "My phone is 010-1234-5678",
  "matches": [
    {
      "ns_id": "kr/mobile_01",
      "pattern_id": "mobile_01",
      "namespace": "kr",
      "category": "phone",
      "start": 12,
      "end": 25,
      "matched_text": null,
      "severity": "high"
    }
  ],
  "namespaces_searched": ["kr"],
  "match_count": 1
}
```

### POST /validate

针对模式验证文本。

**请求：**
```json
{
  "text": "010-1234-5678",
  "ns_id": "kr/mobile_01"
}
```

**响应：**
```json
{
  "text": "010-1234-5678",
  "ns_id": "kr/mobile_01",
  "is_valid": true,
  "match": {
    "ns_id": "kr/mobile_01",
    "category": "phone",
    "start": 0,
    "end": 13
  }
}
```

### POST /redact

从文本中脱敏 PII。

**请求：**
```json
{
  "text": "My SSN is 900101-1234567",
  "namespaces": ["kr"],
  "strategy": "mask",
  "allow_overlaps": false
}
```

**响应：**
```json
{
  "original_text": "My SSN is 900101-1234567",
  "redacted_text": "My SSN is ***-****-****",
  "strategy": "mask",
  "matches": [...],
  "redaction_count": 1
}
```

### GET /health

健康检查端点。

**响应：**
```json
{
  "status": "healthy",
  "version": "0.0.1",
  "patterns_loaded": 150,
  "namespaces": ["kr", "us", "co"]
}
```

### GET /metrics

Prometheus 指标端点。

**响应：**（Prometheus 格式）
```
# HELP data_detector_requests_total Total requests
# TYPE data_detector_requests_total counter
data_detector_requests_total{method="find"} 1234
...
```

## CLI 参考

### data-detector find

在文本中查找 PII。

```bash
data-detector find [OPTIONS]
```

**选项：**
- `--text TEXT`：要搜索的文本
- `--file PATH`：要搜索的文件
- `--ns NAMESPACE`：要搜索的命名空间（可指定多个）
- `--output FORMAT`：输出格式（json/text）

**示例：**
```bash
data-detector find --text "010-1234-5678" --ns kr
data-detector find --file input.txt --ns kr us --output json
```

### data-detector validate

针对模式验证文本。

```bash
data-detector validate [OPTIONS]
```

**选项：**
- `--text TEXT`：要验证的文本
- `--ns-id NS_ID`：模式命名空间/id

**示例：**
```bash
data-detector validate --text "010-1234-5678" --ns-id kr/mobile_01
```

### data-detector redact

从文本中脱敏 PII。

```bash
data-detector redact [OPTIONS]
```

**选项：**
- `--in PATH`：输入文件
- `--out PATH`：输出文件
- `--ns NAMESPACE`：要搜索的命名空间
- `--strategy STRATEGY`：脱敏策略（mask/hash/tokenize）

**示例：**
```bash
data-detector redact --in input.log --out redacted.log --ns kr us
```

### data-detector serve

启动服务器。

```bash
data-detector serve [OPTIONS]
```

**选项：**
- `--port PORT`：服务器端口（默认值：8080）
- `--host HOST`：服务器主机（默认值：0.0.0.0）
- `--config PATH`：配置文件路径

**示例：**
```bash
data-detector serve --port 8080 --config config.yml
```
