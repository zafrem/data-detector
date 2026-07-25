# 토큰 패턴 감지

이 가이드는 엔트로피 기반 검증을 사용하여 API 키, 비밀번호 및 기타 민감한 토큰을 식별하는 높은 엔트로피 토큰 감지 기능을 다룹니다.

## 개요

토큰 패턴은 다음을 결합하여 민감한 자격 증명과 비밀번호를 감지합니다:
1. **정규식 매칭** - 초기 패턴 매칭 (빠름)
2. **엔트로피 검증** - Shannon 엔트로피 계산 (정확함)
3. **우선순위 기반 검색** - 일반 패턴 전에 공급업체별 패턴 확인

이 접근 방식은 다음을 제공합니다:
- ✅ **높은 정확도** - 반복적인 문자열과 낮은 엔트로피 패턴 필터링
- ✅ **낮은 거짓 양성** - 엔트로피 임계값이 "aaaa..." 또는 "1234..." 일치 방지
- ✅ **빠른 성능** - 엔트로피 체크 전에 정규식으로 후보 좁힘
- ✅ **공급업체별 감지** - AWS, GitHub, Stripe 등 인식

## 빠른 시작

### Python API

```python
from datadetector import Engine, load_registry

# 토큰 패턴 로드
registry = load_registry(paths=["patterns/tokens.yml"])
engine = Engine(registry)

# 토큰 감지
text = "API Key: rk_test_4eC39HqLyjWDarjtT1zdp7dcEXAMPLE"
result = engine.find(text, namespaces=["comm"])

if result.has_matches:
    for match in result.matches:
        print(f"Found {match.pattern_id}: {match.category.value}")
```

### CLI

```bash
# 파일에서 토큰 감지
data-detector find --file secrets.log --patterns patterns/tokens.yml

# 빠른 감지 확인 (첫 번째 일치에서 중지)
data-detector find --file data.txt --patterns patterns/tokens.yml --first-only
```

## 지원하는 토큰 유형

### 공급업체별 토큰 (우선순위: 5-20)

| 패턴 | 예제 | 우선순위 | 검증 |
|---------|---------|----------|--------------|
| AWS Access Key | `AKIAIOSFODNN7EXAMPLE` | 10 | 형식만 |
| AWS Secret Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | 15 | 높은 엔트로피 |
| GitHub Token | `ghp_EXAMPLE1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P` | 10 | 높은 엔트로피 |
| Stripe-like API Key | `rk_test_4eC39HqLyjWDarjtT1zdp7dcEXAMPLE` | 10 | 높은 엔트로피 |
| Google API Key | `AIzaSyD-EXAMPLE9tN3R6X5Q8W7E4R2T1Y9U6I5O3P` | 10 | 형식만 |
| Slack Token | `xoxb-123456789012-1234567890123-AbCdEfGh` | 10 | 높은 엔트로피 |
| JWT Token | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJz...` | 20 | 형식만 |
| Private Key | `-----BEGIN RSA PRIVATE KEY-----` | 5 | 헤더 일치 |

### 일반 토큰 (우선순위: 90-95)

| 패턴 | 설명 | 최소 길이 | 엔트로피 |
|---------|-------------|------------|---------|
| Generic Token | 높은 엔트로피 영숫자 | 20+ 문자 | 4.0+ 비트/문자 |
| Generic API Key | 높은 엔트로피 영숫자 | 32+ 문자 | 4.0+ 비트/문자 |

## 작동 방식

### 1. 패턴 매칭 (정규식)

먼저, 정규식 패턴이 후보를 좁힙니다:

```yaml
- id: generic_token_01
  pattern: '[A-Za-z0-9_\-+/=.]{20,}'  # 20+ 문자, base64url 문자 집합
```

**일치:** `aBcD3fGh1JkLmN0pQrStUvW2x` (25 문자)
**건너뜀:** `short` (너무 짧음)

### 2. 엔트로피 검증

그런 다음, Shannon 엔트로피가 낮은 무작위성 문자열을 필터링합니다:

```python
def high_entropy_token(value: str) -> bool:
    """토큰 엔트로피 >= 4.0 비트/문자 검증"""

    # Shannon 엔트로피 계산
    entropy = -sum((count/length) * log2(count/length)
                   for count in char_counts.values())

    return entropy >= 4.0
```

**통과:** `aBcD3fGh1JkLmN0pQrStUvW2x` (엔트로피: 4.82)
**실패:** `aaaaaaaaaaaaaaaaaaaaaaaa` (엔트로피: 0.0)

### 3. 우선순위 기반 매칭

일반 패턴 전에 공급업체별 패턴이 확인됩니다:

```yaml
# 먼저 확인 (우선순위 10)
- id: stripe_key_01
  pattern: 'rk_(live|test)_[A-Za-z0-9]{24,}'
  priority: 10

# 마지막 확인 (우선순위 90)
- id: generic_token_01
  pattern: '[A-Za-z0-9_\-+/=.]{20,}'
  priority: 90
```

**결과:** Stripe 키는 `generic_token_01` 대신 `stripe_key_01`로 일치합니다

## 구성

### 사용자 정의 토큰 패턴 생성

`patterns/tokens.yml`에 추가:

```yaml
- id: my_api_token_01
  location: comm
  category: token
  description: My custom API token format
  pattern: 'myapp_[A-Za-z0-9]{40}'
  verification: high_entropy_token
  priority: 10
  mask: "[REDACTED_MY_TOKEN]"
  examples:
    match:
      - "myapp_aBcD3fGh1JkLmN0pQrStUvW2xY4zA5bC6dE7fG8hI9j"
    nomatch:
      - "myapp_short"
      - "myapp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  policy:
    store_raw: false
    action_on_match: redact
    severity: critical
```

### 엔트로피 임계값 조정

민감도를 조정하려면 `verification.py`를 수정하세요:

```python
def high_entropy_token(value: str) -> bool:
    # 높은 임계값 = 더 적은 일치 (더 엄격)
    min_entropy = 4.5  # 기본값: 4.0

    return entropy >= min_entropy
```

**임계값 가이드라인:**
- `3.5`: 관대함 (일부 패턴화된 문자열 포함 가능)
- `4.0`: 균형 (기본값, 권장)
- `4.5`: 엄격 (높은 무작위성 문자열만)
- `5.0`: 매우 엄격 (일부 유효한 토큰 놓칠 수 있음)

## 성능

### 벤치마크 결과

테스트: 100회 반복, 4개의 토큰이 있는 텍스트

| 모드 | 시간 | 속도 향상 |
|------|------|---------|
| 모든 일치 찾기 | 489ms | 1x |
| 첫 일치에서 중지 | 1.3ms | **377배 빠름** |

### 최적화 팁

1. **감지를 위해 `stop_on_first_match=True` 사용:**
   ```python
   has_tokens = engine.find(text, stop_on_first_match=True).has_matches
   ```

2. **적절한 우선순위 설정:**
   - 높은 우선순위 (0-10): 공급업체별 토큰
   - 낮은 우선순위 (90-95): 일반 대체

3. **필요한 패턴만 로드:**
   ```python
   registry = load_registry(paths=["patterns/tokens.yml"])
   # 토큰만 필요하면 모든 패턴 로드하지 않기
   ```

4. **특정 네임스페이스 사용:**
   ```python
   result = engine.find(text, namespaces=["comm"])  # 토큰 패턴만
   ```

## 일반적인 사용 사례

### 1. CI/CD에서 비밀 스캔

```python
def scan_for_secrets(file_path: str) -> bool:
    """파일에 비밀이 포함되어 있는지 빠르게 확인"""
    registry = load_registry(paths=["patterns/tokens.yml"])
    engine = Engine(registry)

    text = open(file_path).read()
    result = engine.find(text, stop_on_first_match=True)

    if result.has_matches:
        print(f"⚠️  Secret detected in {file_path}")
        return True
    return False
```

### 2. 로그 수정

```python
def redact_logs(log_text: str) -> str:
    """로그에서 토큰 수정"""
    registry = load_registry(paths=["patterns/tokens.yml"])
    engine = Engine(registry)

    result = engine.redact(log_text, namespaces=["comm"])
    return result.redacted_text
```

### 3. Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# 스테이지된 파일에서 토큰 스캔
for file in $(git diff --cached --name-only); do
    if data-detector find --file "$file" --patterns patterns/tokens.yml --first-only; then
        echo "❌ Secret detected in $file - commit blocked"
        exit 1
    fi
done

echo "✅ No secrets detected"
```

## API 참조

### Engine.find() 매개변수

```python
def find(
    text: str,
    namespaces: Optional[List[str]] = None,
    allow_overlaps: bool = False,
    include_matched_text: bool = False,
    stop_on_first_match: bool = False,  # 새로운: 조기 종료
) -> FindResult:
```

**매개변수:**
- `stop_on_first_match` (bool): 첫 번째 일치를 찾은 후 중지
  - 빠른 감지 확인에 사용
  - 모든 일치를 찾는 것보다 100-400배 빠름
  - 우선순위 순서로 패턴 확인

### CLI 옵션

```bash
data-detector find [OPTIONS]

옵션:
  --text TEXT              검색할 텍스트
  --file PATH              검색할 파일
  --patterns PATH          로드할 패턴 파일
  --ns NAMESPACE           검색할 네임스페이스
  --first-only             첫 일치에서 중지 (빠른 감지)
  --include-text           출력에 일치된 텍스트 포함
  --output [json|text]     출력 형식
```

## 문제 해결

### 거짓 양성

**문제:** 비밀이 아닌 것과 일치하는 일반 토큰

**해결책:** 엔트로피 임계값을 높이거나 공급업체별 패턴 사용

```python
# verification.py에서
min_entropy = 4.5  # 4.0에서 증가
```

### 거짓 음성

**문제:** 실제 토큰이 감지되지 않음

**해결책:** 엔트로피 임계값을 낮추거나 패턴 정규식 확인

```python
# verification.py에서
min_entropy = 3.5  # 4.0에서 감소
```

### 성능 문제

**문제:** 대용량 파일에서 느린 감지

**해결책:**
1. 감지 확인을 위해 `stop_on_first_match=True` 사용
2. 모든 패턴이 아닌 토큰 패턴만 로드
3. 일반적인 토큰을 먼저 확인하도록 적절한 우선순위 설정

## 보안 모범 사례

1. **일치된 토큰을 절대 로그하지 않기:**
   ```python
   result = engine.find(text, include_matched_text=False)  # 원시 텍스트 포함하지 않기
   ```

2. **로그에 수정 사용:**
   ```python
   redacted = engine.redact(log_text)
   logger.info(redacted.redacted_text)
   ```

3. **비밀이 있는 커밋 차단:**
   ```bash
   # Pre-commit hook
   data-detector find --file "$file" --first-only && exit 1
   ```

4. **정기적으로 스캔:**
   ```python
   # 주기적인 비밀 스캔
   for file in repository.files():
       if has_secrets(file):
           alert_security_team(file)
   ```

## 참고 자료

- [검증 함수](verification.md) - 사용자 정의 엔트로피 임계값
- [패턴 우선순위](patterns.md#priority) - 패턴 검색 순서
- [성능 최적화](performance.md) - 속도 팁
- [API 참조](api-reference.md) - 완전한 API 문서
