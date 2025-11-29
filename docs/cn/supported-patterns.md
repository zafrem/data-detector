# 支持的模式

## 概述

data-detector 包含用于跨多个国家和类别检测 PII 的内置模式。

**总模式数**：60+
**位置**：7 个（通用、KR、US、TW、JP、CN、IN）

## 通用/国际（location: co）

### 电子邮件和网络
- `email_01` - 电子邮件地址（RFC 5322 简化版）
- `ipv4_01` - IPv4 地址
- `ipv6_01` - IPv6 地址（简化版）
- `url_01` - 带 http/https 协议的 URL

### 信用卡
- `credit_card_visa_01` - Visa 信用卡
- `credit_card_mastercard_01` - MasterCard 信用卡
- `credit_card_amex_01` - American Express 信用卡
- `credit_card_discover_01` - Discover 信用卡
- `credit_card_jcb_01` - JCB 信用卡
- `credit_card_diners_01` - Diners Club 信用卡

### IBAN（带 Mod-97 验证）
- `iban_01` - 通用 IBAN（所有国家）
- `iban_ad_01` - 安道尔
- `iban_al_01` - 阿尔巴尼亚
- `iban_at_01` - 奥地利
- `iban_de_01` - 德国
- `iban_fr_01` - 法国
- `iban_gb_01` - 英国
- `iban_it_01` - 意大利
- `iban_nl_01` - 荷兰
- `iban_es_01` - 西班牙

## 韩国（location: kr）

### 电话号码
- `mobile_01` - 移动电话号码（010/011/016-019）
- `landline_01` - 固定电话号码（02/031-055/061-064）

### 国家身份证
- `rrn_01` - 居民登记号（주민등록번호）
- `business_registration_01` - 企业注册号（사업자등록번호）
- `corporate_registration_01` - 公司注册号（법인등록번호）
- `passport_01` - 护照号码
- `driver_license_01` - 驾驶执照号码

### 金融
- `bank_account_01` - 银行账号

### 姓名
- `korean_name_01` - 韩国姓名（韩文）

## 美国（location: us）

### 国家身份证
- `ssn_01` - 社会安全号（SSN）
- `ein_01` - 雇主识别号
- `itin_01` - 个人纳税人识别号

### 电话和位置
- `phone_01` - 电话号码（带区号）
- `zipcode_01` - 邮政编码（5 位数和 ZIP+4）

### 文件
- `passport_01` - 护照号码
- `driver_license_ca_01` - 加利福尼亚驾驶执照
- `medicare_01` - Medicare 受益人标识符

## 台湾（location: tw）

### 电话号码
- `mobile_01` - 移动电话号码
- `landline_01` - 固定电话号码

### 身份证和文件
- `national_id_01` - 国民身份证（身分證字號）
- `passport_01` - 护照号码
- `business_id_01` - 企业统一编号（統一編號）

### 姓名
- `chinese_name_01` - 繁体中文姓名

## 日本（location: jp）

### 电话号码
- `mobile_01` - 移动电话号码
- `landline_01` - 固定电话号码

### 身份证和文件
- `my_number_01` - My Number（个人号码）
- `passport_01` - 护照号码
- `driver_license_01` - 驾驶执照号码
- `zipcode_01` - 邮政编码

### 金融
- `bank_account_01` - 银行账号

### 姓名
- `japanese_name_hiragana_01` - 日本姓名（平假名）
- `japanese_name_katakana_01` - 日本姓名（片假名）
- `japanese_name_kanji_01` - 日本姓名（汉字）

## 中国（location: cn）

### 电话号码
- `mobile_01` - 移动电话号码
- `landline_01` - 固定电话号码

### 身份证和文件
- `national_id_01` - 国民身份证（18 位数）
- `passport_01` - 护照号码
- `social_credit_01` - 统一社会信用代码

### 金融
- `bank_card_01` - 银行卡号

### 姓名
- `chinese_name_01` - 简体中文姓名

## 印度（location: in）

### 电话号码
- `mobile_01` - 移动电话号码
- `landline_01` - 固定电话号码

### 身份证和文件
- `aadhaar_01` - Aadhaar 号码
- `pan_01` - PAN（永久账号）
- `passport_01` - 护照号码
- `voter_id_01` - 选民身份证（EPIC）
- `driving_license_01` - 驾驶执照

### 位置和金融
- `pincode_01` - PIN 码
- `ifsc_01` - IFSC 代码
- `gst_01` - GST 号码

### 姓名
- `indian_name_01` - 印度姓名（拉丁文）

## 类别

模式按以下类别组织：

- **phone** - 电话号码
- **ssn** - 社会安全号
- **rrn** - 居民登记号
- **email** - 电子邮件地址
- **bank** - 银行账号
- **passport** - 护照号码
- **address** - 实际地址
- **credit_card** - 信用卡号
- **ip** - IP 地址
- **iban** - 国际银行账号
- **name** - 个人姓名
- **other** - 其他 PII 类型

## 严重程度级别

- **low** - IP 地址、URL
- **medium** - 电子邮件地址、姓名
- **high** - 电话号码、国家身份证、IBAN
- **critical** - 信用卡、SSN、RRN、银行账户

## 使用模式

### 按命名空间查找
```python
# 仅搜索韩国模式
result = engine.find(text, namespaces=["kr"])

# 搜索多个命名空间
result = engine.find(text, namespaces=["kr", "us", "co"])
```

### 按特定模式查找
```python
# 针对特定模式验证
result = engine.validate("010-1234-5678", "kr/mobile_01")
```

### 查找所有模式
```python
# 搜索所有加载的模式
result = engine.find(text)
```

## 模式准确性

### 带验证
具有验证函数的模式（例如，IBAN、带 Luhn 的信用卡）具有更高的准确性：
- **IBAN 模式**：~99% 准确度（Mod-97 验证）
- **信用卡模式**：可以添加 Luhn 验证

### 仅正则表达式
没有验证的模式仅依赖于正则表达式匹配：
- **电话号码**：仅格式验证
- **身份证**：格式和长度验证

要提高准确性，请考虑为您的用例添加自定义验证函数。

## 添加新模式

有关添加您自己的模式的说明，请参见[自定义模式](custom-patterns.md)。
