# YAML 유틸리티 - 완전한 가이드

## 목차

1. [개요](#개요)
2. [설치](#설치)
3. [빠른 시작](#빠른-시작)
4. [API 참조](#api-참조)
5. [사용 예제](#사용-예제)
6. [모범 사례](#모범-사례)
7. [오류 처리](#오류-처리)
8. [고급 주제](#고급-주제)

---

## 개요

YAML 유틸리티 모듈 (`datadetector.utils.yaml_utils`)은 YAML 패턴 파일을 읽고, 쓰고, 관리하기 위한 포괄적인 도구 세트를 제공합니다. 두 가지 주요 클래스를 제공합니다:

- **`YAMLHandler`** - 범용 YAML 파일 작업
- **`PatternFileHandler`** - 전문화된 패턴 파일 관리

### YAML 유틸리티를 사용하는 이유는?

- ✅ **타입 안전** - 데이터 타입과 구조 검증
- ✅ **오류 방지** - 우발적인 덮어쓰기 방지
- ✅ **편리함** - 일반적인 작업을 위한 간단한 API
- ✅ **패턴 인식** - 패턴 파일 구조 이해
- ✅ **잘 테스트됨** - 100% 테스트 커버리지

---

## 설치

YAML 유틸리티는 data-detector 패키지에 포함되어 있습니다:

```bash
pip install data-detector
```

또는 소스에서 설치:

```bash
git clone https://github.com/yourusername/data-detector.git
cd data-detector
pip install -e .
```

---

## 빠른 시작

### 기본 YAML 작업

```python
from datadetector import read_yaml, write_yaml

# YAML 파일 읽기
data = read_yaml("config.yml")

# YAML 파일 쓰기
write_yaml("output.yml", {"key": "value"})

# 기존 파일 덮어쓰기
write_yaml("output.yml", {"key": "new_value"}, overwrite=True)
```

### 패턴 파일 작업

```python
from datadetector import PatternFileHandler

# 새 패턴 파일 생성
PatternFileHandler.create_pattern_file(
    file_path="my_patterns.yml",
    namespace="custom",
    description="My custom patterns"
)

# 패턴 추가
PatternFileHandler.add_pattern_to_file("my_patterns.yml", {
    "id": "email_01",
    "location": "custom",
    "category": "email",
    "pattern": r"[a-z]+@example\.com",
    "mask": "***@example.com",
    "policy": {
        "store_raw": False,
        "action_on_match": "redact",
        "severity": "medium"
    }
})

# 모든 패턴 나열
pattern_ids = PatternFileHandler.list_patterns_in_file("my_patterns.yml")
print(pattern_ids)  # ['email_01']
```

---

## API 참조

### YAMLHandler 클래스

#### `read_yaml(file_path: Union[str, Path]) -> Dict[str, Any]`

YAML 파일을 읽고 내용을 딕셔너리로 반환합니다.

**매개변수:**
- `file_path` - YAML 파일 경로 (문자열 또는 Path 객체)

**반환값:**
- YAML 내용을 포함하는 딕셔너리

**예외:**
- `FileNotFoundError` - 파일이 존재하지 않는 경우
- `ValueError` - YAML이 유효하지 않거나 딕셔너리가 아닌 경우

**예제:**
```python
from datadetector.utils.yaml_utils import YAMLHandler

data = YAMLHandler.read_yaml("patterns/kr.yml")
print(f"Namespace: {data['namespace']}")
print(f"Patterns: {len(data['patterns'])}")
```

---

#### `write_yaml(file_path: Union[str, Path], data: Dict[str, Any], overwrite: bool = False, sort_keys: bool = False) -> None`

딕셔너리를 YAML 파일에 씁니다.

**매개변수:**
- `file_path` - 출력 YAML 파일 경로
- `data` - 작성할 딕셔너리
- `overwrite` - True이면 기존 파일을 덮어씁니다 (기본값: False)
- `sort_keys` - True이면 딕셔너리 키를 알파벳 순으로 정렬합니다 (기본값: False)

**예외:**
- `FileExistsError` - 파일이 존재하고 overwrite=False인 경우
- `ValueError` - data가 딕셔너리가 아닌 경우

**예제:**
```python
from datadetector.utils.yaml_utils import YAMLHandler

# 디렉토리 구조 자동 생성
YAMLHandler.write_yaml(
    "output/subdir/config.yml",
    {"namespace": "test", "patterns": []},
    overwrite=True
)
```

---

#### `update_yaml(file_path: Union[str, Path], updates: Dict[str, Any], merge: bool = True) -> Dict[str, Any]`

기존 YAML 파일을 새 데이터로 업데이트합니다.

**매개변수:**
- `file_path` - YAML 파일 경로
- `updates` - 적용할 업데이트가 있는 딕셔너리
- `merge` - True이면 기존 데이터와 병합합니다. False이면 완전히 교체합니다 (기본값: True)

**반환값:**
- 업데이트된 딕셔너리

**예외:**
- `FileNotFoundError` - 파일이 존재하지 않는 경우

**예제:**
```python
from datadetector.utils.yaml_utils import YAMLHandler

# 기존 내용과 병합
updated = YAMLHandler.update_yaml(
    "config.yml",
    {"new_field": "new_value"},
    merge=True
)

# 전체 내용 교체
replaced = YAMLHandler.update_yaml(
    "config.yml",
    {"completely": "new"},
    merge=False
)
```

---

### PatternFileHandler 클래스

#### `create_pattern_file(file_path, namespace, description, patterns=None, overwrite=False)`

새 패턴 YAML 파일을 생성합니다.

**매개변수:**
- `file_path` - 출력 파일 경로
- `namespace` - 패턴 네임스페이스 (예: "custom", "company")
- `description` - 패턴 파일 설명
- `patterns` - 패턴 정의 목록 (선택 사항, 기본값: 빈 목록)
- `overwrite` - True이면 기존 파일을 덮어씁니다 (기본값: False)

**예제:**
```python
from datadetector import PatternFileHandler

PatternFileHandler.create_pattern_file(
    file_path="company_patterns.yml",
    namespace="company",
    description="Company-specific patterns",
    patterns=[
        {
            "id": "employee_id_01",
            "location": "company",
            "category": "other",
            "description": "Employee ID format",
            "pattern": r"EMP-\d{6}",
            "mask": "EMP-******",
            "policy": {
                "store_raw": False,
                "action_on_match": "redact",
                "severity": "medium"
            }
        }
    ]
)
```

---

#### `add_pattern_to_file(file_path, pattern)`

기존 패턴 파일에 패턴을 추가합니다.

**매개변수:**
- `file_path` - 패턴 파일 경로
- `pattern` - 패턴 정의 딕셔너리

**필수 패턴 필드:**
- `id` - 패턴 식별자 (일치해야 함: `[a-z_][a-z0-9_]*_\d{2}`)
- `location` - 위치/국가 코드
- `category` - 카테고리 (email, phone, ssn 등)
- `pattern` - 정규식 패턴
- `policy` - store_raw, action_on_match, severity가 있는 정책 구성

**예외:**
- `FileNotFoundError` - 파일이 존재하지 않는 경우
- `ValueError` - 패턴에 필수 필드가 없는 경우

**예제:**
```python
from datadetector import PatternFileHandler

new_pattern = {
    "id": "api_token_01",
    "location": "company",
    "category": "token",
    "description": "Internal API token",
    "pattern": r"TOK_[A-Z0-9]{40}",
    "mask": "TOK_" + "*" * 40,
    "examples": {
        "match": ["TOK_ABC123DEF456GHI789JKL012MNO345PQR678"],
        "nomatch": ["TOKEN_SHORT", "TOK-ABC123"]
    },
    "policy": {
        "store_raw": False,
        "action_on_match": "redact",
        "severity": "critical"
    }
}

PatternFileHandler.add_pattern_to_file("company_patterns.yml", new_pattern)
```

---

#### `remove_pattern_from_file(file_path, pattern_id) -> bool`

패턴 파일에서 패턴을 제거합니다.

**매개변수:**
- `file_path` - 패턴 파일 경로
- `pattern_id` - 제거할 패턴의 ID

**반환값:**
- 패턴이 제거되면 `True`, 찾지 못하면 `False`

**예제:**
```python
from datadetector import PatternFileHandler

# 패턴 제거
success = PatternFileHandler.remove_pattern_from_file(
    "company_patterns.yml",
    "employee_id_01"
)

if success:
    print("Pattern removed successfully")
else:
    print("Pattern not found")
```

---

#### `update_pattern_in_file(file_path, pattern_id, updates) -> bool`

패턴의 특정 필드를 업데이트합니다.

**매개변수:**
- `file_path` - 패턴 파일 경로
- `pattern_id` - 업데이트할 패턴의 ID
- `updates` - 업데이트할 필드의 딕셔너리

**반환값:**
- 패턴이 업데이트되면 `True`, 찾지 못하면 `False`

**예제:**
```python
from datadetector import PatternFileHandler

# 패턴 심각도 및 설명 업데이트
success = PatternFileHandler.update_pattern_in_file(
    "company_patterns.yml",
    "api_token_01",
    {
        "description": "Updated description",
        "policy": {
            "severity": "critical",
            "action_on_match": "tokenize"
        }
    }
)
```

---

#### `get_pattern_from_file(file_path, pattern_id) -> Optional[Dict[str, Any]]`

패턴 파일에서 특정 패턴을 검색합니다.

**매개변수:**
- `file_path` - 패턴 파일 경로
- `pattern_id` - 검색할 패턴의 ID

**반환값:**
- 찾으면 패턴 딕셔너리, 그렇지 않으면 `None`

**예제:**
```python
from datadetector import PatternFileHandler

pattern = PatternFileHandler.get_pattern_from_file(
    "company_patterns.yml",
    "api_token_01"
)

if pattern:
    print(f"Pattern: {pattern['pattern']}")
    print(f"Category: {pattern['category']}")
    print(f"Severity: {pattern['policy']['severity']}")
else:
    print("Pattern not found")
```

---

#### `list_patterns_in_file(file_path) -> List[str]`

패턴 파일의 모든 패턴 ID를 나열합니다.

**매개변수:**
- `file_path` - 패턴 파일 경로

**반환값:**
- 패턴 ID 목록

**예제:**
```python
from datadetector import PatternFileHandler

pattern_ids = PatternFileHandler.list_patterns_in_file("company_patterns.yml")

print(f"Found {len(pattern_ids)} patterns:")
for pid in pattern_ids:
    print(f"  - {pid}")
```

---

### 편의 함수

빠른 액세스를 위해 다음 모듈 수준 함수를 사용할 수 있습니다:

```python
from datadetector import read_yaml, write_yaml, update_yaml

# 읽기
data = read_yaml("file.yml")

# 쓰기
write_yaml("file.yml", data, overwrite=True)

# 업데이트
updated = update_yaml("file.yml", {"key": "value"})
```

이것들은 `YAMLHandler.read_yaml()`, `YAMLHandler.write_yaml()`, `YAMLHandler.update_yaml()`에 대한 단축키입니다.

---

## 사용 예제

### 예제 1: 완전한 패턴 파일 생성

```python
from datadetector import PatternFileHandler

# 여러 패턴 정의
patterns = [
    {
        "id": "credit_card_01",
        "location": "custom",
        "category": "credit_card",
        "description": "Credit card number",
        "pattern": r"\d{4}-\d{4}-\d{4}-\d{4}",
        "mask": "****-****-****-****",
        "verification": "luhn",  # Luhn 알고리즘 사용
        "policy": {
            "store_raw": False,
            "action_on_match": "redact",
            "severity": "critical"
        }
    },
    {
        "id": "phone_01",
        "location": "custom",
        "category": "phone",
        "description": "Phone number",
        "pattern": r"\d{3}-\d{3}-\d{4}",
        "mask": "***-***-****",
        "policy": {
            "store_raw": False,
            "action_on_match": "redact",
            "severity": "high"
        }
    }
]

# 파일 생성
PatternFileHandler.create_pattern_file(
    file_path="sensitive_data_patterns.yml",
    namespace="sensitive",
    description="Patterns for sensitive personal data",
    patterns=patterns
)

print("✅ Created pattern file with 2 patterns")
```

---

### 예제 2: 패턴 심각도 일괄 업데이트

```python
from datadetector import PatternFileHandler

# 모든 패턴 가져오기
pattern_ids = PatternFileHandler.list_patterns_in_file("company_patterns.yml")

# 모든 패턴에 대해 심각도 업데이트
for pattern_id in pattern_ids:
    # 현재 패턴 가져오기
    pattern = PatternFileHandler.get_pattern_from_file(
        "company_patterns.yml",
        pattern_id
    )

    # 카테고리에 따라 업데이트
    if pattern["category"] in ["credit_card", "ssn", "token"]:
        new_severity = "critical"
    else:
        new_severity = "high"

    # 업데이트 적용
    PatternFileHandler.update_pattern_in_file(
        "company_patterns.yml",
        pattern_id,
        {"policy": {"severity": new_severity}}
    )

    print(f"Updated {pattern_id} to {new_severity}")
```

---

### 예제 3: 패턴 파일 복제 및 수정

```python
from datadetector import read_yaml, write_yaml

# 원본 읽기
original = read_yaml("patterns/kr.yml")

# 수정된 버전 생성
modified = {
    "namespace": "kr_extended",
    "description": f"{original['description']} - Extended version",
    "patterns": original["patterns"].copy()
}

# 사용자 정의 패턴 추가
custom_patterns = [
    {
        "id": "custom_kr_phone_01",
        "location": "kr",
        "category": "phone",
        "pattern": r"070-\d{4}-\d{4}",
        "mask": "070-****-****",
        "policy": {
            "store_raw": False,
            "action_on_match": "redact",
            "severity": "medium"
        }
    }
]

modified["patterns"].extend(custom_patterns)

# 새 파일에 쓰기
write_yaml("patterns/kr_extended.yml", modified)

print(f"✅ Created extended pattern file with {len(modified['patterns'])} patterns")
```

---

### 예제 4: 패턴 파일 검증

```python
from datadetector import read_yaml, PatternFileHandler

def validate_pattern_file(file_path):
    """포괄적인 패턴 파일 검증."""
    errors = []
    warnings = []

    try:
        # 파일 읽기
        data = read_yaml(file_path)

        # 필수 최상위 필드 확인
        required_fields = ["namespace", "description", "patterns"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # 네임스페이스 형식 확인
        if "namespace" in data:
            if not data["namespace"].islower():
                warnings.append("Namespace should be lowercase")

        # 각 패턴 검증
        if "patterns" in data:
            pattern_fields = ["id", "location", "category", "pattern", "policy"]

            for i, pattern in enumerate(data["patterns"]):
                # 필수 필드 확인
                for field in pattern_fields:
                    if field not in pattern:
                        errors.append(f"Pattern {i}: Missing field '{field}'")

                # ID 형식 확인
                if "id" in pattern:
                    import re
                    if not re.match(r'^[a-z_][a-z0-9_]*_\d{2}$', pattern["id"]):
                        errors.append(
                            f"Pattern {i}: ID '{pattern['id']}' doesn't match "
                            "required format (e.g., 'email_01')"
                        )

                # 정책 구조 확인
                if "policy" in pattern:
                    policy_fields = ["store_raw", "action_on_match", "severity"]
                    for field in policy_fields:
                        if field not in pattern["policy"]:
                            errors.append(
                                f"Pattern {i}: Policy missing field '{field}'"
                            )

        # 결과 출력
        if errors:
            print("❌ Validation failed:")
            for error in errors:
                print(f"   ERROR: {error}")

        if warnings:
            print("⚠️  Warnings:")
            for warning in warnings:
                print(f"   WARNING: {warning}")

        if not errors and not warnings:
            print("✅ Pattern file is valid!")
            print(f"   Namespace: {data['namespace']}")
            print(f"   Patterns: {len(data.get('patterns', []))}")
            return True

        return len(errors) == 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# 검증 사용
validate_pattern_file("my_patterns.yml")
```

---

### 예제 5: 패턴 형식 마이그레이션

```python
from datadetector import read_yaml, write_yaml

def migrate_old_format(old_file, new_file):
    """이전 패턴 형식에서 새 형식으로 마이그레이션."""

    # 이전 형식 읽기
    old = read_yaml(old_file)

    # 새 형식으로 변환
    new = {
        "namespace": old["namespace"],
        "description": old.get("description", "Migrated patterns"),
        "patterns": []
    }

    for old_pattern in old["patterns"]:
        new_pattern = {
            "id": old_pattern["id"],
            "location": old_pattern.get("location", old["namespace"]),
            "category": old_pattern["category"],
            "pattern": old_pattern.get("regex", old_pattern.get("pattern")),
            "mask": old_pattern.get("mask", "***"),
            "policy": {
                "store_raw": old_pattern.get("store_raw", False),
                "action_on_match": old_pattern.get("action", "redact"),
                "severity": old_pattern.get("severity", "medium")
            }
        }

        # 선택적 필드 마이그레이션
        if "examples" in old_pattern:
            new_pattern["examples"] = old_pattern["examples"]

        if "verification" in old_pattern:
            new_pattern["verification"] = old_pattern["verification"]

        if "metadata" in old_pattern:
            new_pattern["metadata"] = old_pattern["metadata"]

        new["patterns"].append(new_pattern)

    # 새 형식 쓰기
    write_yaml(new_file, new)

    print(f"✅ Migrated {len(new['patterns'])} patterns")
    print(f"   From: {old_file}")
    print(f"   To: {new_file}")

# 마이그레이션 실행
migrate_old_format("old_patterns.yml", "new_patterns.yml")
```

---

### 예제 6: 동적 패턴 생성

```python
from datadetector import PatternFileHandler

def generate_ip_range_patterns(namespace="network", start_range=0, end_range=255):
    """IP 주소 범위에 대한 패턴 생성."""

    patterns = []

    # 각 범위에 대해 패턴 생성
    for i in range(start_range, end_range + 1, 10):
        pattern_id = f"ip_range_{i:03d}"

        pattern = {
            "id": pattern_id,
            "location": namespace,
            "category": "ip",
            "description": f"IP range {i}.x.x.x",
            "pattern": rf"{i}\.\d{{1,3}}\.\d{{1,3}}\.\d{{1,3}}",
            "mask": f"{i}.*.*.*",
            "policy": {
                "store_raw": False,
                "action_on_match": "report",
                "severity": "low"
            }
        }

        patterns.append(pattern)

    # 패턴 파일 생성
    PatternFileHandler.create_pattern_file(
        file_path=f"{namespace}_ip_patterns.yml",
        namespace=namespace,
        description=f"Auto-generated IP range patterns",
        patterns=patterns,
        overwrite=True
    )

    print(f"✅ Generated {len(patterns)} IP range patterns")

# 패턴 생성
generate_ip_range_patterns()
```

---

### 예제 7: 백업 및 복원

```python
from datadetector import read_yaml, write_yaml
import shutil
from datetime import datetime

def backup_pattern_file(file_path):
    """패턴 파일의 타임스탬프 백업 생성."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"

    # 읽기 및 쓰기 (YAML 형식 유지)
    data = read_yaml(file_path)
    write_yaml(backup_path, data)

    print(f"✅ Backup created: {backup_path}")
    return backup_path

def restore_pattern_file(backup_path, target_path):
    """백업에서 패턴 파일 복원."""

    data = read_yaml(backup_path)
    write_yaml(target_path, data, overwrite=True)

    print(f"✅ Restored from: {backup_path}")
    print(f"   To: {target_path}")

# 사용
backup = backup_pattern_file("important_patterns.yml")

# 나중에... 필요하면 복원
# restore_pattern_file(backup, "important_patterns.yml")
```

---

## 모범 사례

### 1. **수정 전에 항상 백업**

```python
from datadetector import read_yaml, write_yaml

# 수정 전에 백업 생성
backup_data = read_yaml("patterns.yml")
write_yaml("patterns.yml.backup", backup_data)

# 이제 안전하게 수정
# ...
```

### 2. **검증 사용**

```python
from datadetector import load_registry

# 생성 후 패턴 검증
try:
    registry = load_registry(
        paths=["my_patterns.yml"],
        validate_schema=True,
        validate_examples=True
    )
    print("✅ Patterns are valid")
except ValueError as e:
    print(f"❌ Validation failed: {e}")
```

### 3. **명명 규칙 따르기**

```python
# 좋은 패턴 ID
"email_01"
"phone_01"
"credit_card_visa_01"

# 나쁜 패턴 ID
"Email01"          # 소문자여야 함
"phone"            # 숫자 접미사 누락
"credit-card-01"   # 하이픈이 아닌 밑줄 사용
```

### 4. **예제 포함**

```python
pattern = {
    "id": "custom_id_01",
    "location": "custom",
    "category": "other",
    "pattern": r"ID-\d{8}",
    "mask": "ID-********",
    "examples": {  # 항상 예제 포함
        "match": ["ID-12345678", "ID-00000001"],
        "nomatch": ["ID-123", "ID12345678"]
    },
    "policy": {...}
}
```

### 5. **적절한 심각도 설정**

```python
# Critical - 즉각적인 보안 위험
"severity": "critical"  # 신용카드, SSN, 비밀번호

# High - 중요한 개인정보 문제
"severity": "high"      # 전화번호, 이메일, 주소

# Medium - 중간 민감도
"severity": "medium"    # 내부 ID, 비중요 PII

# Low - 낮은 민감도
"severity": "low"       # 공개 정보, 메타데이터
```

### 6. **설명적인 설명 사용**

```python
# 좋음
"description": "Employee ID in format EMP-NNNNNN where N is digit"

# 나쁨
"description": "Employee ID"
```

### 7. **배포 전에 패턴 테스트**

```python
from datadetector import Engine, load_registry

# 로드 및 테스트
registry = load_registry(paths=["my_patterns.yml"], validate_examples=False)
engine = Engine(registry)

# 샘플 데이터로 테스트
test_cases = [
    "Employee EMP-123456 called",
    "Contact: 010-1234-5678",
    "Email: test@example.com"
]

for text in test_cases:
    result = engine.find(text, namespaces=["custom"])
    print(f"Text: {text}")
    print(f"Matches: {result.match_count}")
```

---

## 오류 처리

### 일반적인 오류 및 해결책

#### FileNotFoundError

```python
from datadetector import read_yaml

try:
    data = read_yaml("nonexistent.yml")
except FileNotFoundError as e:
    print(f"File not found: {e}")
    # 기본 파일 생성
    write_yaml("nonexistent.yml", {"namespace": "default", "patterns": []})
```

#### FileExistsError

```python
from datadetector import write_yaml

try:
    write_yaml("existing.yml", data)
except FileExistsError:
    print("File exists. Use overwrite=True to replace")
    write_yaml("existing.yml", data, overwrite=True)
```

#### ValueError (유효하지 않은 YAML)

```python
from datadetector import read_yaml

try:
    data = read_yaml("invalid.yml")
except ValueError as e:
    print(f"Invalid YAML: {e}")
    # 파일을 수동으로 수정하거나 새로 생성
```

#### ValueError (필수 필드 누락)

```python
from datadetector import PatternFileHandler

try:
    PatternFileHandler.add_pattern_to_file("file.yml", {"id": "test"})
except ValueError as e:
    print(f"Invalid pattern: {e}")
    # 필수 필드 추가: location, category, pattern, policy
```

---

## 고급 주제

### 대용량 패턴 파일 작업

```python
from datadetector import read_yaml, write_yaml

# 대용량 파일 읽기
data = read_yaml("large_patterns.yml")

# 청크로 처리
chunk_size = 100
patterns = data["patterns"]

for i in range(0, len(patterns), chunk_size):
    chunk = patterns[i:i + chunk_size]

    # 청크 처리
    for pattern in chunk:
        # 패턴 수정
        pass

    # 진행 상황 쓰기
    if i % 500 == 0:
        print(f"Processed {i}/{len(patterns)} patterns")

# 다시 쓰기
write_yaml("large_patterns.yml", data, overwrite=True)
```

### 사용자 정의 검증 함수

```python
from datadetector import read_yaml

def validate_custom_requirements(file_path):
    """사용자 정의 검증 로직."""
    data = read_yaml(file_path)

    # 회사별 요구 사항
    for pattern in data["patterns"]:
        # 설명이 있어야 함
        if "description" not in pattern or len(pattern["description"]) < 10:
            raise ValueError(f"Pattern {pattern['id']}: Description too short")

        # 예제가 있어야 함
        if "examples" not in pattern:
            raise ValueError(f"Pattern {pattern['id']}: Missing examples")

        # Critical 패턴은 원시 데이터를 저장하면 안 됨
        if pattern["policy"]["severity"] == "critical":
            if pattern["policy"]["store_raw"]:
                raise ValueError(f"Pattern {pattern['id']}: Critical patterns cannot store raw data")

    print("✅ Custom validation passed")

validate_custom_requirements("company_patterns.yml")
```

### CI/CD와의 통합

```python
#!/usr/bin/env python3
"""패턴 파일에 대한 CI/CD 검증 스크립트."""

import sys
from pathlib import Path
from datadetector import load_registry, read_yaml

def validate_all_patterns(pattern_dir="patterns"):
    """디렉토리의 모든 패턴 파일 검증."""

    pattern_files = list(Path(pattern_dir).glob("*.yml"))

    if not pattern_files:
        print(f"❌ No pattern files found in {pattern_dir}")
        return False

    print(f"Validating {len(pattern_files)} pattern files...")

    errors = []

    for file in pattern_files:
        try:
            # 스키마 검증
            data = read_yaml(file)

            # 검증과 함께 로드
            registry = load_registry(
                paths=[str(file)],
                validate_schema=True,
                validate_examples=True
            )

            print(f"✅ {file.name}: {len(registry)} patterns")

        except Exception as e:
            errors.append(f"{file.name}: {str(e)}")
            print(f"❌ {file.name}: {str(e)}")

    if errors:
        print(f"\n❌ Validation failed with {len(errors)} errors")
        return False

    print(f"\n✅ All {len(pattern_files)} files validated successfully")
    return True

if __name__ == "__main__":
    success = validate_all_patterns()
    sys.exit(0 if success else 1)
```

---

## 참고 자료

- [아키텍처](./ARCHITECTURE.md) - 시스템 아키텍처 및 설계 개요
- [패턴 스키마](../schemas/pattern-schema.json) - 패턴 파일의 JSON 스키마
- [Engine API](./engine.md) - 감지 엔진과 함께 패턴 사용
- [검증 함수](./verification.md) - 사용자 정의 검증 로직
- [테스트 가이드](../TESTING.md) - 패턴 테스트

---

## 기여

버그를 발견했거나 기능 요청이 있나요? GitHub에서 이슈를 열어주세요!

---

**마지막 업데이트:** 2025-10-11
**버전:** 1.0.0
