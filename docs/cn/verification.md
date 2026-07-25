# 验证函数

## 概述

验证函数在正则表达式匹配后提供额外的验证。它们对于具有校验和、验证算法或无法单独用正则表达式表达的复杂业务逻辑的模式非常有用。

## 工作原理

1. 正则表达式模式匹配文本
2. 如果指定了 `verification`，则将匹配的值传递给验证函数
3. 只有当正则表达式**和**验证都通过时，匹配才被视为有效

## 内置验证函数

### IBAN Mod-97

使用 Mod-97 算法验证国际银行账号。

```yaml
- id: iban_01
  location: co
  category: iban
  pattern: '[A-Z]{2}\d{2}[A-Z0-9]{11,30}'
  verification: iban_mod97
```

示例：
```python
from datadetector.verification import iban_mod97

print(iban_mod97("GB82WEST12345698765432"))  # True（有效）
print(iban_mod97("GB82WEST12345698765433"))  # False（无效校验位）
```

### Luhn 算法

使用 Luhn 校验和算法验证号码（信用卡、某些国家身份证）。

```yaml
- id: credit_card_visa_01
  location: co
  category: credit_card
  pattern: '4[0-9]{12}(?:[0-9]{3})?'
  verification: luhn
```

示例：
```python
from datadetector.verification import luhn

print(luhn("4532015112830366"))  # True（有效 Visa）
print(luhn("4532015112830367"))  # False（无效校验位）
```

## 创建自定义验证函数

### 1. 定义您的函数

```python
def custom_checksum(value: str) -> bool:
    """
    自定义验证逻辑。

    Args:
        value: 来自正则表达式的匹配字符串

    Returns:
        如果有效则为 True，否则为 False
    """
    # 示例：数字之和必须为偶数
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0
```

### 2. 注册函数

```python
from datadetector.verification import register_verification_function

register_verification_function("custom_checksum", custom_checksum)
```

### 3. 在模式中引用

```yaml
patterns:
  - id: custom_id_01
    location: myorg
    category: other
    pattern: 'CID-\d{4}'
    verification: custom_checksum  # 按名称引用
```

### 4. 在代码中使用

```python
from datadetector import Engine, load_registry
from datadetector.verification import register_verification_function

# 注册自定义函数
def custom_checksum(value: str) -> bool:
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0

register_verification_function("custom_checksum", custom_checksum)

# 加载模式（必须在注册之后）
registry = load_registry(paths=["patterns/custom.yml"])
engine = Engine(registry)

# 验证
result = engine.validate("CID-1234", "myorg/custom_id_01")  # True（1+2+3+4=10，偶数）
result = engine.validate("CID-1235", "myorg/custom_id_01")  # False（1+2+3+5=11，奇数）
```

## 高级示例

### 示例 1：ISBN-10 验证

```python
def isbn10_check(value: str) -> bool:
    """验证 ISBN-10 校验位。"""
    digits = [int(c) if c.isdigit() else 10 for c in value if c.isdigit() or c == 'X']
    if len(digits) != 10:
        return False
    checksum = sum((10 - i) * digit for i, digit in enumerate(digits))
    return checksum % 11 == 0

register_verification_function("isbn10", isbn10_check)
```

模式：
```yaml
- id: isbn10_01
  location: intl
  category: other
  description: 带校验位验证的 ISBN-10
  pattern: '(?:\d{9}[\dX]|\d-\d{3}-\d{5}-[\dX])'
  verification: isbn10
```

### 示例 2：自定义业务逻辑

```python
def valid_department_code(value: str) -> bool:
    """针对允许的部门验证部门代码。"""
    allowed_depts = {'ENG', 'SLS', 'MKT', 'HR', 'FIN'}
    dept = value.split('-')[0]
    return dept in allowed_depts

register_verification_function("dept_code", valid_department_code)
```

模式：
```yaml
- id: dept_employee_id_01
  location: acme
  category: other
  pattern: '[A-Z]{3}-\d{6}'
  verification: dept_code
  examples:
    match: ["ENG-123456", "SLS-999999"]
    nomatch: ["XXX-123456", "ENG-12345"]
```

### 示例 3：日期范围验证

```python
from datetime import datetime

def valid_date_range(value: str) -> bool:
    """检查日期是否在允许的范围内。"""
    try:
        # 假设格式为 YYYY-MM-DD
        date = datetime.strptime(value, '%Y-%m-%d')
        start = datetime(2020, 1, 1)
        end = datetime(2030, 12, 31)
        return start <= date <= end
    except ValueError:
        return False

register_verification_function("date_range", valid_date_range)
```

## 管理函数

### 获取验证函数

```python
from datadetector.verification import get_verification_function

func = get_verification_function("iban_mod97")
if func:
    print(func("GB82WEST12345698765432"))
```

### 注销函数

```python
from datadetector.verification import unregister_verification_function

result = unregister_verification_function("custom_checksum")
print(result)  # 如果删除则为 True，如果未找到则为 False
```

### 列出可用函数

```python
from datadetector.verification import VERIFICATION_FUNCTIONS

print(list(VERIFICATION_FUNCTIONS.keys()))
# ['iban_mod97', 'luhn', ...]
```

## 最佳实践

1. **保持函数纯净**：验证函数应该是无状态且确定性的
2. **优雅地处理错误**：对于无效输入返回 `False`，不要抛出异常
3. **优化性能**：验证在每次匹配时运行，因此保持快速
4. **彻底记录**：在文档字符串中解释验证逻辑
5. **广泛测试**：为您的验证函数编写单元测试
6. **早期注册**：在加载模式之前注册自定义函数
7. **使用有意义的名称**：选择清晰、描述性的函数名称

## 测试验证

```python
# 独立测试
from datadetector.verification import iban_mod97

assert iban_mod97("GB82WEST12345698765432") == True
assert iban_mod97("GB82WEST12345698765433") == False

# 使用引擎测试
from datadetector import Engine, load_registry

registry = load_registry(paths=["patterns/common.yml"])
engine = Engine(registry)

# 有效 IBAN - 通过正则表达式和验证
result = engine.validate("GB82WEST12345698765432", "co/iban_01")
assert result.is_valid == True

# 无效 IBAN - 通过正则表达式但验证失败
result = engine.validate("GB82WEST12345698765433", "co/iban_01")
assert result.is_valid == False
```

## 模式文件中的示例

加载模式时会自动应用验证：

```yaml
patterns:
  # 带验证的 IBAN
  - id: iban_01
    pattern: '[A-Z]{2}\d{2}[A-Z0-9]{11,30}'
    verification: iban_mod97
    examples:
      match: ["GB82WEST12345698765432"]  # 有效 IBAN
      nomatch:
        - "GB82WEST1234569876543"  # 太短
        - "ABCD1234567890123456"   # 无效校验位

  # 带 Luhn 的信用卡
  - id: visa_card_01
    pattern: '4[0-9]{15}'
    verification: luhn
    examples:
      match: ["4532015112830366"]   # 有效 Visa
      nomatch: ["4532015112830367"]  # 无效校验位
```

示例验证会自动考虑验证，因此验证失败的模式即使匹配正则表达式也不会通过 `nomatch` 测试。
