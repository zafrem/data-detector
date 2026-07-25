# 빠른 시작 가이드

## 기본 사용법

### 라이브러리 API

```python
from datadetector import Engine, load_registry

# 특정 파일에서 패턴 로드
registry = load_registry(paths=["patterns/common.yml", "patterns/kr.yml"])
# 또는 디렉토리에서 모든 패턴 로드
registry = load_registry(paths=["patterns/"])

engine = Engine(registry)

# 검증
is_valid = engine.validate("010-1234-5678", "kr/mobile_01")
print(is_valid)  # True

# PII 찾기 (로드된 모든 패턴 검색)
results = engine.find("My phone: 01012345678, email: test@example.com")
for match in results.matches:
    print(f"Found {match.category} at position {match.start}-{match.end}")

# 수정
redacted = engine.redact(
    "SSN: 900101-1234567",
    namespaces=["kr"],
    strategy="mask"
)
print(redacted.redacted_text)
```

### CLI 사용법

```bash
# 텍스트에서 PII 찾기
data-detector find --ns kr/mobile --file sample.txt

# PII 수정
data-detector redact --in input.log --out redacted.log --ns kr us

# 서버 시작
data-detector serve --port 8080 --config config.yml
```

### REST API

서버 시작:
```bash
data-detector serve --port 8080
```

API 사용:
```bash
# PII 찾기
curl -X POST http://localhost:8080/find \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "namespaces": ["kr"]}'

# 검증
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "ns_id": "kr/mobile"}'

# 수정
curl -X POST http://localhost:8080/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "My SSN is 900101-1234567", "namespaces": ["kr"]}'

# 상태 확인
curl http://localhost:8080/health
```

## 다음 단계

- [패턴 구조](patterns.md) - 패턴 정의 방법 배우기
- [설정](configuration.md) - 서버 및 레지스트리 설정
- [사용자 정의 패턴](custom-patterns.md) - 자신만의 패턴 만들기
- [검증 함수](verification.md) - 사용자 정의 검증 로직 추가
