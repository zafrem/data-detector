# YAML 유틸리티 문서

`yaml_utils` 모듈은 패턴 파일을 생성하고 관리하기 위한 포괄적인 YAML 파일 읽기/쓰기 유틸리티를 제공합니다.

## 목차

- [개요](#개요)
- [기본 YAML 작업](#기본-yaml-작업)
- [패턴 파일 관리](#패턴-파일-관리)
- [API 참조](#api-참조)
- [예제](#예제)

## 개요

YAML 유틸리티는 두 가지 주요 클래스를 제공합니다:

1. **`YAMLHandler`** - 일반 YAML 읽기/쓰기 작업
2. **`PatternFileHandler`** - 패턴 파일에 대한 전문화된 작업

또한, 일반적인 작업을 위한 편의 함수도 제공됩니다.

## 기본 YAML 작업

### YAML 파일 읽기

```python
from datadetector import read_yaml

# YAML 파일 읽기
data = read_yaml("config.yml")
print(data)
```

클래스를 직접 사용:

```python
from datadetector.utils.yaml_utils import YAMLHandler

data = YAMLHandler.read_yaml("config.yml")
```

### YAML 파일 쓰기

```python
from datadetector import write_yaml

data = {
    "namespace": "custom",
    "description": "My custom patterns",
    "patterns": []
}

# 새 파일 쓰기 (존재하면 실패)
write_yaml("my_patterns.yml", data)

# 기존 파일 덮어쓰기
write_yaml("my_patterns.yml", data, overwrite=True)

# 정렬된 키로 쓰기
write_yaml("my_patterns.yml", data, sort_keys=True)
```

### YAML 파일 업데이트

```python
from datadetector import update_yaml

# 기존 데이터와 병합 (기본값)
updated_data = update_yaml("config.yml", {"new_key": "new_value"})

# 전체 내용 교체
updated_data = update_yaml("config.yml", {"new_key": "new_value"}, merge=False)
```

## 패턴 파일 관리

### 패턴 파일 생성

```python
from datadetector import PatternFileHandler

# 새 패턴 파일 생성
PatternFileHandler.create_pattern_file(
    file_path="my_patterns.yml",
    namespace="custom",
    description="My custom patterns for emails and phones",
    patterns=[
        {
            "id": "custom_email_01",
            "location": "custom",
            "category": "email",
            "description": "Custom email pattern",
            "pattern": r"[a-zA-Z0-9._%+-]+@company\.com",
            "mask": "***@company.com",
            "policy": {
                "store_raw": False,
                "action_on_match": "redact",
                "severity": "high"
            }
        }
    ]
)
```

### 패턴 추가

```python
from datadetector import PatternFileHandler

# 새 패턴 정의
new_pattern = {
    "id": "custom_phone_01",
    "location": "custom",
    "category": "phone",
    "description": "Internal phone format",
    "pattern": r"\d{4}-\d{4}",
    "mask": "****-****",
    "examples": {
        "match": ["1234-5678", "9999-0000"],
        "nomatch": ["123-4567", "12345678"]
    },
    "policy": {
        "store_raw": False,
        "action_on_match": "redact",
        "severity": "medium"
    }
}

# 기존 파일에 추가
PatternFileHandler.add_pattern_to_file("my_patterns.yml", new_pattern)
```

### 패턴 업데이트

```python
from datadetector import PatternFileHandler

# 패턴의 특정 필드 업데이트
PatternFileHandler.update_pattern_in_file(
    file_path="my_patterns.yml",
    pattern_id="custom_email_01",
    updates={
        "pattern": r"[a-zA-Z0-9._%+-]+@(company|enterprise)\.com",
        "description": "Updated email pattern with multiple domains"
    }
)
```

### 패턴 제거

```python
from datadetector import PatternFileHandler

# ID로 패턴 제거
success = PatternFileHandler.remove_pattern_from_file(
    file_path="my_patterns.yml",
    pattern_id="custom_email_01"
)

if success:
    print("Pattern removed successfully")
else:
    print("Pattern not found")
```

### 패턴 조회

```python
from datadetector import PatternFileHandler

# 특정 패턴 가져오기
pattern = PatternFileHandler.get_pattern_from_file(
    file_path="my_patterns.yml",
    pattern_id="custom_email_01"
)

if pattern:
    print(f"Pattern: {pattern['pattern']}")
    print(f"Category: {pattern['category']}")

# 파일의 모든 패턴 ID 나열
pattern_ids = PatternFileHandler.list_patterns_in_file("my_patterns.yml")
print(f"Found {len(pattern_ids)} patterns:")
for pid in pattern_ids:
    print(f"  - {pid}")
```

## API 참조

### YAMLHandler

#### `read_yaml(file_path: Union[str, Path]) -> Dict[str, Any]`

YAML 파일을 읽고 내용을 딕셔너리로 반환합니다.

**매개변수:**
- `file_path`: YAML 파일 경로

**반환값:**
- YAML 내용을 포함하는 딕셔너리

**예외:**
- `FileNotFoundError`: 파일이 존재하지 않는 경우
- `ValueError`: YAML이 유효하지 않거나 딕셔너리가 아닌 경우

---

#### `write_yaml(file_path: Union[str, Path], data: Dict[str, Any], overwrite: bool = False, sort_keys: bool = False) -> None`

딕셔너리를 YAML 파일에 씁니다.

**매개변수:**
- `file_path`: 출력 YAML 파일 경로
- `data`: 작성할 딕셔너리
- `overwrite`: True이면 기존 파일을 덮어씁니다 (기본값: False)
- `sort_keys`: True이면 딕셔너리 키를 알파벳 순으로 정렬합니다 (기본값: False)

**예외:**
- `FileExistsError`: 파일이 존재하고 overwrite=False인 경우
- `ValueError`: data가 딕셔너리가 아닌 경우

---

#### `update_yaml(file_path: Union[str, Path], updates: Dict[str, Any], merge: bool = True) -> Dict[str, Any]`

기존 YAML 파일을 새 데이터로 업데이트합니다.

**매개변수:**
- `file_path`: YAML 파일 경로
- `updates`: 적용할 업데이트가 있는 딕셔너리
- `merge`: True이면 기존 데이터와 병합합니다. False이면 완전히 교체합니다 (기본값: True)

**반환값:**
- 업데이트된 딕셔너리

**예외:**
- `FileNotFoundError`: 파일이 존재하지 않는 경우

---

### PatternFileHandler

#### `create_pattern_file(file_path: Union[str, Path], namespace: str, description: str, patterns: Optional[List[Dict[str, Any]]] = None, overwrite: bool = False) -> None`

새 패턴 YAML 파일을 생성합니다.

**매개변수:**
- `file_path`: 출력 파일 경로
- `namespace`: 패턴 네임스페이스
- `description`: 패턴 파일 설명
- `patterns`: 패턴 정의 목록 (선택 사항)
- `overwrite`: True이면 기존 파일을 덮어씁니다 (기본값: False)

---

#### `add_pattern_to_file(file_path: Union[str, Path], pattern: Dict[str, Any]) -> None`

기존 패턴 파일에 패턴을 추가합니다.

**매개변수:**
- `file_path`: 패턴 파일 경로
- `pattern`: 추가할 패턴 정의 (다음을 포함해야 함: id, location, category, pattern, policy)

**예외:**
- `FileNotFoundError`: 파일이 존재하지 않는 경우
- `ValueError`: 패턴에 필수 필드가 없는 경우

---

#### `remove_pattern_from_file(file_path: Union[str, Path], pattern_id: str) -> bool`

패턴 파일에서 패턴을 제거합니다.

**매개변수:**
- `file_path`: 패턴 파일 경로
- `pattern_id`: 제거할 패턴의 ID

**반환값:**
- 패턴이 제거되면 `True`, 찾지 못하면 `False`

---

#### `update_pattern_in_file(file_path: Union[str, Path], pattern_id: str, updates: Dict[str, Any]) -> bool`

패턴 파일의 패턴을 업데이트합니다.

**매개변수:**
- `file_path`: 패턴 파일 경로
- `pattern_id`: 업데이트할 패턴의 ID
- `updates`: 업데이트할 필드의 딕셔너리

**반환값:**
- 패턴이 업데이트되면 `True`, 찾지 못하면 `False`

---

#### `get_pattern_from_file(file_path: Union[str, Path], pattern_id: str) -> Optional[Dict[str, Any]]`

패턴 파일에서 특정 패턴을 가져옵니다.

**매개변수:**
- `file_path`: 패턴 파일 경로
- `pattern_id`: 검색할 패턴의 ID

**반환값:**
- 찾으면 패턴 딕셔너리, 그렇지 않으면 `None`

---

#### `list_patterns_in_file(file_path: Union[str, Path]) -> List[str]`

패턴 파일의 모든 패턴 ID를 나열합니다.

**매개변수:**
- `file_path`: 패턴 파일 경로

**반환값:**
- 패턴 ID 목록

---

### 편의 함수

```python
from datadetector import read_yaml, write_yaml, update_yaml

# 이것들은 YAMLHandler 메서드에 대한 단축키입니다
data = read_yaml("file.yml")
write_yaml("file.yml", data, overwrite=True)
updated = update_yaml("file.yml", {"key": "value"})
```

## 예제

### 예제 1: 완전한 패턴 파일 생성

```python
from datadetector import PatternFileHandler

# 패턴 정의
patterns = [
    {
        "id": "employee_id_01",
        "location": "company",
        "category": "identifier",
        "description": "Employee ID format",
        "pattern": r"EMP-\d{6}",
        "mask": "EMP-******",
        "examples": {
            "match": ["EMP-123456", "EMP-999999"],
            "nomatch": ["EMP-12345", "EMPLOYEE-123456"]
        },
        "policy": {
            "store_raw": False,
            "action_on_match": "redact",
            "severity": "medium"
        }
    },
    {
        "id": "department_code_01",
        "location": "company",
        "category": "identifier",
        "description": "Department code",
        "pattern": r"DEPT-[A-Z]{3}",
        "mask": "DEPT-***",
        "policy": {
            "store_raw": True,
            "action_on_match": "report",
            "severity": "low"
        }
    }
]

# 파일 생성
PatternFileHandler.create_pattern_file(
    file_path="company_patterns.yml",
    namespace="company",
    description="Company-specific patterns for internal use",
    patterns=patterns
)
```

### 예제 2: 패턴 일괄 업데이트

```python
from datadetector import PatternFileHandler

# 모든 패턴 가져오기
pattern_ids = PatternFileHandler.list_patterns_in_file("company_patterns.yml")

# 모든 패턴에 대해 심각도 업데이트
for pattern_id in pattern_ids:
    PatternFileHandler.update_pattern_in_file(
        "company_patterns.yml",
        pattern_id,
        {"policy": {"severity": "high"}}
    )
```

### 예제 3: 패턴 파일 복제 및 수정

```python
from datadetector import read_yaml, write_yaml

# 기존 패턴 파일 읽기
original = read_yaml("patterns/kr.yml")

# 네임스페이스 및 설명 수정
modified = {
    "namespace": "kr_extended",
    "description": f"{original['description']} - Extended version",
    "patterns": original["patterns"]
}

# 새 패턴 추가
new_pattern = {
    "id": "custom_kr_01",
    "location": "kr",
    "category": "other",
    "pattern": r"custom_pattern",
    "policy": {"store_raw": False, "action_on_match": "redact", "severity": "low"}
}
modified["patterns"].append(new_pattern)

# 새 파일에 쓰기
write_yaml("patterns/kr_extended.yml", modified)
```

### 예제 4: 패턴 형식 마이그레이션

```python
from datadetector import read_yaml, write_yaml

# 이전 형식 읽기
old_patterns = read_yaml("old_patterns.yml")

# 새 형식으로 변환
new_patterns = {
    "namespace": old_patterns["namespace"],
    "description": old_patterns.get("description", "Migrated patterns"),
    "patterns": []
}

for old_pattern in old_patterns["patterns"]:
    new_pattern = {
        "id": old_pattern["id"],
        "location": old_pattern.get("location", old_patterns["namespace"]),
        "category": old_pattern["category"],
        "pattern": old_pattern["regex"],  # 필드 이름 변경
        "mask": old_pattern.get("mask", "***"),
        "policy": {
            "store_raw": old_pattern.get("store_raw", False),
            "action_on_match": old_pattern.get("action", "redact"),
            "severity": old_pattern.get("severity", "medium")
        }
    }
    new_patterns["patterns"].append(new_pattern)

# 새 형식 쓰기
write_yaml("new_patterns.yml", new_patterns)
```

### 예제 5: 패턴 파일 검증

```python
from datadetector import PatternFileHandler, read_yaml

def validate_pattern_file(file_path):
    """패턴 파일 구조 검증."""
    try:
        data = read_yaml(file_path)

        # 필수 최상위 필드 확인
        required_fields = ["namespace", "description", "patterns"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            print(f"❌ Missing required fields: {missing}")
            return False

        # 각 패턴 확인
        pattern_fields = ["id", "location", "category", "pattern", "policy"]
        for i, pattern in enumerate(data["patterns"]):
            missing = [f for f in pattern_fields if f not in pattern]
            if missing:
                print(f"❌ Pattern {i}: Missing fields: {missing}")
                return False

        print(f"✅ Pattern file is valid!")
        print(f"   Namespace: {data['namespace']}")
        print(f"   Patterns: {len(data['patterns'])}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# 검증
validate_pattern_file("my_patterns.yml")
```

## 오류 처리

모든 함수는 명확한 오류 메시지를 제공합니다:

```python
from datadetector import PatternFileHandler

try:
    # FileNotFoundError를 발생시킵니다
    PatternFileHandler.add_pattern_to_file("nonexistent.yml", {...})
except FileNotFoundError as e:
    print(f"File not found: {e}")

try:
    # ValueError를 발생시킵니다 (필수 필드 누락)
    PatternFileHandler.add_pattern_to_file("my_patterns.yml", {"id": "test"})
except ValueError as e:
    print(f"Invalid pattern: {e}")

try:
    # FileExistsError를 발생시킵니다 (기본값 overwrite=False)
    PatternFileHandler.create_pattern_file("existing.yml", "test", "Test")
except FileExistsError as e:
    print(f"File exists: {e}")
```

## 패턴 로딩과의 통합

패턴 파일을 생성한 후에는 엔진과 함께 로드합니다:

```python
from datadetector import Engine, load_registry

# 사용자 정의 패턴 로드
registry = load_registry(paths=["my_patterns.yml", "company_patterns.yml"])

# 엔진 생성
engine = Engine(registry)

# 패턴 사용
result = engine.find("Check employee EMP-123456", namespaces=["company"])
print(f"Found {result.match_count} matches")
```

## 모범 사례

1. **생성 또는 수정 후 패턴 파일을 항상 검증**
2. **규칙을 따라 설명적인 패턴 ID 사용**: `<type>_<number>` (예: `email_01`)
3. **패턴에 예제를 포함**하여 정규식 정확성 검증
4. **데이터 민감도에 따라 적절한 심각도 수준 설정**
5. **기본적으로 `overwrite=False` 사용**하여 우발적인 데이터 손실 방지
6. **패턴을 일괄 업데이트하기 전에 백업 유지**
7. **프로덕션에 배포하기 전에 엔진으로 패턴 테스트**

## 로깅

YAML 유틸리티는 Python의 로깅 모듈을 사용합니다:

```python
import logging

# YAML 작업에 대한 디버그 로깅 활성화
logging.basicConfig(level=logging.DEBUG)

from datadetector import PatternFileHandler

# 다음을 로그합니다: "Successfully wrote YAML file: my_patterns.yml"
PatternFileHandler.create_pattern_file(...)
```

---

자세한 정보는 다음을 참조하십시오:
- [아키텍처](./ARCHITECTURE.md) - 시스템 아키텍처 및 설계 개요
- [패턴 스키마 문서](../schemas/pattern-schema.json)
- [Engine API 문서](./engine.md)
- [테스트 문서](../TESTING.md)
