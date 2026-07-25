# 创建自定义模式

## 概述

您可以添加自己的模式来检测特定于组织或自定义的数据格式。

## 步骤

### 1. 创建 YAML 文件

在 `patterns/` 目录中创建文件（任意文件名）：

```yaml
namespace: custom
description: Custom organization patterns

patterns:
  - id: employee_id_01
    location: myorg     # 您的组织/位置代码
    category: other
    description: Employee ID format
    pattern: 'EMP-\d{6}'
    mask: "EMP-******"
    examples:
      match: ["EMP-123456", "EMP-999999"]
      nomatch: ["EMP-12345", "TEMP-123456"]
    policy:
      store_raw: false
      action_on_match: redact
      severity: high
```

### 2. 使用自定义模式加载

```python
from datadetector import load_registry, Engine

# 加载特定文件
registry = load_registry(paths=["patterns/custom.yml"])

# 或加载整个目录（包括所有 .yml/.yaml 文件）
registry = load_registry(paths=["patterns/"])

engine = Engine(registry)

# 使用模式
result = engine.validate("EMP-123456", "custom/employee_id_01")
print(result.is_valid)  # True
```

## 示例

### 示例 1：自定义 ID 格式

```yaml
namespace: cp
description: Company-specific patterns

patterns:
  - id: project_code_01
    location: acme
    category: other
    description: ACME project code format (PROJ-YYYY-NNN)
    pattern: 'PROJ-\d{4}-\d{3}'
    mask: "PROJ-****-***"
    examples:
      match: ["PROJ-2024-001", "PROJ-2025-999"]
      nomatch: ["PROJ-24-001", "PROJECT-2024-001"]
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
```

### 示例 2：带验证的自定义 ID

```yaml
namespace: cp
description: Company patterns with verification

patterns:
  - id: custom_id_01
    location: acme
    category: other
    description: Custom ID with checksum
    pattern: 'CID-\d{4}'
    verification: custom_checksum  # 对自定义函数的引用
    examples:
      match: ["CID-1234"]
      nomatch: ["CID-12345"]
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
```

然后注册验证函数：

```python
from datadetector.verification import register_verification_function

def custom_checksum(value: str) -> bool:
    """自定义校验和：数字之和必须为偶数。"""
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0

# 在加载模式之前注册
register_verification_function("custom_checksum", custom_checksum)

# 现在加载模式
registry = load_registry(paths=["patterns/custom.yml"])
engine = Engine(registry)
```

### 示例 3：特定于组织的电子邮件域

```yaml
namespace: cp
description: Company email patterns

patterns:
  - id: company_email_01
    location: acme
    category: email
    description: ACME company email addresses
    pattern: '[a-zA-Z0-9._%+-]+@acme\.(com|org|net)'
    flags: [IGNORECASE]
    mask: "***@acme.***"
    examples:
      match:
        - "john.doe@acme.com"
        - "employee@acme.org"
      nomatch:
        - "test@example.com"
        - "user@acme.co.uk"
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
```

## 最佳实践

1. **测试您的模式**：始终包含带有 `match` 和 `nomatch` 案例的 `examples`
2. **使用特定模式**：使模式尽可能具体以避免误报
3. **良好文档**：为每个模式编写清晰的描述
4. **选择适当的严重程度**：根据数据敏感性设置严重程度
5. **考虑验证**：对于带校验和或验证的 ID，添加验证函数
6. **使用一致的命名**：遵循模式 ID 的 `{name}_{NN}` 格式
7. **按命名空间组织**：将相关模式分组在同一命名空间中

## 验证

在部署之前验证您的模式：

```bash
# 这将验证所有模式及其示例
python -c "from datadetector import load_registry; load_registry(paths=['patterns/'], validate_examples=True)"
```

## 加载模式

### 从特定文件加载：
```python
registry = load_registry(paths=[
    "patterns/common.yml",
    "patterns/custom.yml"
])
```

### 从目录加载：
```python
# 加载目录中的所有 .yml 和 .yaml 文件
registry = load_registry(paths=["patterns/"])
```

### 开发期间跳过验证：
```python
registry = load_registry(
    paths=["patterns/"],
    validate_schema=False,      # 跳过模式验证
    validate_examples=False     # 跳过示例验证
)
```
