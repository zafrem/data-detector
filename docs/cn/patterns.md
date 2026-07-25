# 模式结构

## 模式文件格式

模式在 YAML 文件中定义，具有以下结构：

```yaml
namespace: kr
description: Korean (South Korea) PII patterns

patterns:
  - id: mobile_01              # 必需：带 2 位后缀的模式 ID
    location: kr               # 必需：位置标识符（kr、us、comm 等）
    category: phone            # 必需：PII 类别
    description: Korean mobile phone number (010/011/016/017/018/019)
    pattern: '01[016-9]-?\d{3,4}-?\d{4}'  # 必需：正则表达式模式
    flags: [IGNORECASE]        # 可选：正则表达式标志
    mask: "***-****-****"      # 可选：默认掩码模板
    verification: iban_mod97   # 可选：验证函数名称
    examples:                  # 可选但推荐
      match: ["010-1234-5678", "01012345678"]
      nomatch: ["012-999-9999"]
    policy:                    # 可选：隐私和操作策略
      store_raw: false
      action_on_match: redact
      severity: high
    metadata:                  # 可选：附加元数据
      note: "Additional information"
```

## 必需字段

- **`id`**：带 2 位后缀的唯一标识符（例如，`mobile_01`、`ssn_02`）
- **`location`**：位置/地区代码（2-4 个小写字母：`kr`、`us`、`comm`、`intl`）
- **`category`**：PII 类别，来自：`phone`、`ssn`、`rrn`、`email`、`bank`、`passport`、`address`、`credit_card`、`ip`、`iban`、`name`、`other`
- **`pattern`**：用于匹配的正则表达式模式

## 可选字段

### Flags
要应用的正则表达式标志：
- `IGNORECASE` - 不区分大小写的匹配
- `MULTILINE` - `^` 和 `$` 匹配行边界
- `DOTALL` - `.` 匹配换行符
- `UNICODE` - Unicode 匹配
- `VERBOSE` - 允许正则表达式中的注释

### Mask
用于脱敏的默认掩码模板（例如，`"***-****-****"`）

### Verification
正则表达式匹配后要应用的验证函数名称。有关详细信息，请参见[验证函数](verification.md)。

内置验证函数：
- `iban_mod97` - IBAN Mod-97 校验和
- `luhn` - Luhn 算法（信用卡等）

### Examples
用于模式验证的测试用例：
- `match` - 应该匹配模式的示例
- `nomatch` - 不应匹配的示例

### Policy
隐私和操作配置：
- `store_raw`（布尔值）- 是否可以存储原始匹配文本
- `action_on_match`（字符串）- 操作：`redact`、`report`、`tokenize`、`ignore`
- `severity`（字符串）- 严重程度级别：`low`、`medium`、`high`、`critical`

### Metadata
作为键值对的任意附加数据。

## 位置代码

`location` 字段标识地理或类别范围：

- **`co`** - 通用/国际模式
- **`kr`** - 韩国
- **`us`** - 美国
- **`tw`** - 台湾（中华民国）
- **`jp`** - 日本
- **`cn`** - 中国（中华人民共和国）
- **`in`** - 印度
- **`eu`** - 欧盟（未来）
- **`intl`** - 国际（多地区）

**注意**：模式文件可以有任何名称。系统使用 `location` 字段来组织模式。

## 模式命名最佳实践

- **ID 格式**：`{name}_{NN}`，其中 NN 是 2 位数字（例如，`mobile_01`、`mobile_02`）
- **位置代码**：使用 2-4 个小写字母（例如，`kr`、`us`、`comm`、`myorg`）
- **版本控制**：为模式变体增加数字后缀（例如，`ssn_01`、`ssn_02`）
