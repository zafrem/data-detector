# 사용자 정의 패턴 생성

## 개요

조직 특정 또는 사용자 정의 데이터 형식을 감지하기 위해 자신만의 패턴을 추가할 수 있습니다.

## 단계

### 1. YAML 파일 생성

`patterns/` 디렉토리에 파일을 생성합니다 (파일 이름은 임의):

```yaml
namespace: custom
description: Custom organization patterns

patterns:
  - id: employee_id_01
    location: myorg     # 조직/위치 코드
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

### 2. 사용자 정의 패턴으로 로드

```python
from datadetector import load_registry, Engine

# 특정 파일 로드
registry = load_registry(paths=["patterns/custom.yml"])

# 또는 전체 디렉토리 로드 (모든 .yml/.yaml 파일 포함)
registry = load_registry(paths=["patterns/"])

engine = Engine(registry)

# 패턴 사용
result = engine.validate("EMP-123456", "custom/employee_id_01")
print(result.is_valid)  # True
```

## 예제

### 예제 1: 사용자 정의 ID 형식

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

### 예제 2: 검증이 있는 사용자 정의 ID

```yaml
namespace: cp
description: Company patterns with verification

patterns:
  - id: custom_id_01
    location: acme
    category: other
    description: Custom ID with checksum
    pattern: 'CID-\d{4}'
    verification: custom_checksum  # 사용자 정의 함수 참조
    examples:
      match: ["CID-1234"]
      nomatch: ["CID-12345"]
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
```

그런 다음 검증 함수를 등록합니다:

```python
from datadetector.verification import register_verification_function

def custom_checksum(value: str) -> bool:
    """사용자 정의 체크섬: 숫자 합계가 짝수여야 함."""
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0

# 패턴 로드 전에 등록
register_verification_function("custom_checksum", custom_checksum)

# 이제 패턴 로드
registry = load_registry(paths=["patterns/custom.yml"])
engine = Engine(registry)
```

### 예제 3: 조직 특정 이메일 도메인

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

## 모범 사례

1. **패턴 테스트**: 항상 `match` 및 `nomatch` 케이스와 함께 `examples`를 포함
2. **특정 패턴 사용**: 거짓 양성을 피하기 위해 패턴을 가능한 한 구체적으로 만들기
3. **잘 문서화**: 각 패턴에 대해 명확한 설명 작성
4. **적절한 심각도 선택**: 데이터 민감도에 따라 심각도 설정
5. **검증 고려**: 체크섬이 있거나 검증된 ID의 경우 검증 함수 추가
6. **일관된 명명 사용**: 패턴 ID에 대해 `{name}_{NN}` 형식 따르기
7. **네임스페이스별 구성**: 관련 패턴을 동일한 네임스페이스로 그룹화
