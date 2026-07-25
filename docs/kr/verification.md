# 검증 함수

## 개요

검증 함수는 정규식 매칭 후 추가 검증을 제공합니다. 체크섬, 검증 알고리즘 또는 정규식만으로는 표현할 수 없는 복잡한 비즈니스 로직이 있는 패턴에 유용합니다.

## 작동 방식

1. 정규식 패턴이 텍스트와 일치
2. `verification`이 지정되면 일치된 값이 검증 함수로 전달됨
3. 정규식 **및** 검증이 모두 통과해야만 일치가 유효한 것으로 간주됨

## 내장 검증 함수

### IBAN Mod-97

Mod-97 알고리즘을 사용하여 국제 은행 계좌 번호를 검증합니다.

```yaml
- id: iban_01
  location: co
  category: iban
  pattern: '[A-Z]{2}\d{2}[A-Z0-9]{11,30}'
  verification: iban_mod97
```

예제:
```python
from datadetector.verification import iban_mod97

print(iban_mod97("GB82WEST12345698765432"))  # True (유효)
print(iban_mod97("GB82WEST12345698765433"))  # False (잘못된 체크 디지트)
```

### Luhn 알고리즘

Luhn 체크섬 알고리즘을 사용하여 번호를 검증합니다 (신용카드, 일부 국가 ID).

```yaml
- id: credit_card_visa_01
  location: co
  category: credit_card
  pattern: '4[0-9]{12}(?:[0-9]{3})?'
  verification: luhn
```

예제:
```python
from datadetector.verification import luhn

print(luhn("4532015112830366"))  # True (유효한 Visa)
print(luhn("4532015112830367"))  # False (잘못된 체크 디지트)
```

## 사용자 정의 검증 함수 생성

### 1. 함수 정의

```python
def custom_checksum(value: str) -> bool:
    """
    사용자 정의 검증 로직.

    Args:
        value: 정규식에서 일치된 문자열

    Returns:
        유효하면 True, 그렇지 않으면 False
    """
    # 예제: 숫자 합계가 짝수여야 함
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0
```

### 2. 함수 등록

```python
from datadetector.verification import register_verification_function

register_verification_function("custom_checksum", custom_checksum)
```

### 3. 패턴에서 참조

```yaml
patterns:
  - id: custom_id_01
    location: myorg
    category: other
    pattern: 'CID-\d{4}'
    verification: custom_checksum  # 이름으로 참조
```

### 4. 코드에서 사용

```python
from datadetector import Engine, load_registry
from datadetector.verification import register_verification_function

# 사용자 정의 함수 등록
def custom_checksum(value: str) -> bool:
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0

register_verification_function("custom_checksum", custom_checksum)

# 패턴 로드 (등록 후여야 함)
registry = load_registry(paths=["patterns/custom.yml"])
engine = Engine(registry)

# 검증
result = engine.validate("CID-1234", "myorg/custom_id_01")  # True (1+2+3+4=10, 짝수)
result = engine.validate("CID-1235", "myorg/custom_id_01")  # False (1+2+3+5=11, 홀수)
```

## 고급 예제

### 예제 1: ISBN-10 검증

```python
def isbn10_check(value: str) -> bool:
    """ISBN-10 체크 디지트 검증."""
    digits = [int(c) if c.isdigit() else 10 for c in value if c.isdigit() or c == 'X']
    if len(digits) != 10:
        return False
    checksum = sum((10 - i) * digit for i, digit in enumerate(digits))
    return checksum % 11 == 0

register_verification_function("isbn10", isbn10_check)
```

패턴:
```yaml
- id: isbn10_01
  location: intl
  category: other
  description: 체크 디지트 검증이 있는 ISBN-10
  pattern: '(?:\d{9}[\dX]|\d-\d{3}-\d{5}-[\dX])'
  verification: isbn10
```

### 예제 2: 사용자 정의 비즈니스 로직

```python
def valid_department_code(value: str) -> bool:
    """허용된 부서에 대해 부서 코드 검증."""
    allowed_depts = {'ENG', 'SLS', 'MKT', 'HR', 'FIN'}
    dept = value.split('-')[0]
    return dept in allowed_depts

register_verification_function("dept_code", valid_department_code)
```

패턴:
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

### 예제 3: 날짜 범위 검증

```python
from datetime import datetime

def valid_date_range(value: str) -> bool:
    """날짜가 허용된 범위 내에 있는지 확인."""
    try:
        # 형식 YYYY-MM-DD 가정
        date = datetime.strptime(value, '%Y-%m-%d')
        start = datetime(2020, 1, 1)
        end = datetime(2030, 12, 31)
        return start <= date <= end
    except ValueError:
        return False

register_verification_function("date_range", valid_date_range)
```

## 관리 함수

### 검증 함수 가져오기

```python
from datadetector.verification import get_verification_function

func = get_verification_function("iban_mod97")
if func:
    print(func("GB82WEST12345698765432"))
```

### 함수 등록 해제

```python
from datadetector.verification import unregister_verification_function

result = unregister_verification_function("custom_checksum")
print(result)  # 제거되면 True, 찾지 못하면 False
```

### 사용 가능한 함수 나열

```python
from datadetector.verification import VERIFICATION_FUNCTIONS

print(list(VERIFICATION_FUNCTIONS.keys()))
# ['iban_mod97', 'luhn', ...]
```

## 모범 사례

1. **함수를 순수하게 유지**: 검증 함수는 상태 비저장 및 결정론적이어야 함
2. **오류를 우아하게 처리**: 잘못된 입력에 대해 `False`를 반환하고 예외를 발생시키지 않음
3. **성능 최적화**: 검증은 모든 일치에서 실행되므로 빠르게 유지
4. **철저히 문서화**: docstring에서 검증 로직 설명
5. **광범위하게 테스트**: 검증 함수에 대한 단위 테스트 작성
6. **조기 등록**: 패턴 로드 전에 사용자 정의 함수 등록
7. **의미 있는 이름 사용**: 명확하고 설명적인 함수 이름 선택

## 검증 테스트

```python
# 독립 실행형 테스트
from datadetector.verification import iban_mod97

assert iban_mod97("GB82WEST12345698765432") == True
assert iban_mod97("GB82WEST12345698765433") == False

# 엔진과 함께 테스트
from datadetector import Engine, load_registry

registry = load_registry(paths=["patterns/common.yml"])
engine = Engine(registry)

# 유효한 IBAN - 정규식 및 검증 모두 통과
result = engine.validate("GB82WEST12345698765432", "co/iban_01")
assert result.is_valid == True

# 잘못된 IBAN - 정규식은 통과하지만 검증 실패
result = engine.validate("GB82WEST12345698765433", "co/iban_01")
assert result.is_valid == False
```

## 패턴 파일의 예제

패턴이 로드될 때 검증이 자동으로 적용됩니다:

```yaml
patterns:
  # 검증이 있는 IBAN
  - id: iban_01
    pattern: '[A-Z]{2}\d{2}[A-Z0-9]{11,30}'
    verification: iban_mod97
    examples:
      match: ["GB82WEST12345698765432"]  # 유효한 IBAN
      nomatch:
        - "GB82WEST1234569876543"  # 너무 짧음
        - "ABCD1234567890123456"   # 잘못된 체크 디지트

  # Luhn이 있는 신용카드
  - id: visa_card_01
    pattern: '4[0-9]{15}'
    verification: luhn
    examples:
      match: ["4532015112830366"]   # 유효한 Visa
      nomatch: ["4532015112830367"]  # 잘못된 체크 디지트
```

예제 검증은 검증을 자동으로 고려하므로 검증에 실패한 패턴은 정규식과 일치하더라도 `nomatch` 테스트를 통과하지 못합니다.
