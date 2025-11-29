# RAG 보안 - 빠른 시작 가이드

> **간단 요약**: RAG 시스템을 위한 3계층 PII 보호를 5분 안에 시작하세요.

---

## 📋 목차

- [개요](#개요)
- [빠른 시작](#빠른-시작)
- [핵심 개념](#핵심-개념)
- [예제](#예제)
- [수정 전략](#수정-전략)
- [설정](#설정)
- [모범 사례](#모범-사례)
- [문제 해결](#문제-해결)
- [관련 문서](#관련-문서)

---

## 개요

### RAG 보안이란?

RAG 보안은 검색 증강 생성(Retrieval-Augmented Generation) 시스템을 위한 **3계층 PII 보호**를 제공합니다. RAG 파이프라인의 모든 단계에서 민감한 정보를 스캔하고 정리합니다: 사용자 쿼리, 문서 저장, LLM 응답.

**주요 기능:**
- ✅ 3계층 보호 (입력 → 저장 → 출력)
- ✅ 다양한 수정 전략 (MASK, FAKE, TOKENIZE, HASH)
- ✅ YAML 기반 설정
- ✅ 빠른 성능 (문서당 < 15ms)
- ✅ 권한 있는 접근을 위한 역변환 가능한 토큰화
- ✅ REST API 지원

**사용 사례:**
- 고객 지원 챗봇
- 내부 지식 베이스
- 공개 문서 검색
- 규정 준수가 필요한 RAG 시스템

---

## 빠른 시작

### 설치

```bash
pip install data-detector
```

### 기본 예제 (3줄)

```python
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

# 초기화
registry = load_registry()
engine = Engine(registry)
security = RAGSecurityMiddleware(engine)

# 쿼리 스캔 (1계층)
result = await security.scan_query("Email john@example.com about order")
print(f"안전한 쿼리: {result.sanitized_text}")
# 출력: "안전한 쿼리: Email [EMAIL] about order"
```

### 완전한 예제 (3계층 모두)

```python
import asyncio
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

async def main():
    # 초기화
    registry = load_registry()
    engine = Engine(registry)
    security = RAGSecurityMiddleware(engine)

    # 1계층: 입력 스캔
    query = "Status for customer john@example.com?"
    input_result = await security.scan_query(query, namespaces=["comm"])

    if input_result.blocked:
        return "쿼리가 차단되었습니다"

    print(f"✓ 안전한 쿼리: {input_result.sanitized_text}")

    # 2계층: 저장소 스캔
    document = "Customer: john@example.com, Phone: 555-0123"
    doc_result = await security.scan_document(document, namespaces=["comm"])

    print(f"✓ 벡터 DB용 안전한 문서: {doc_result.sanitized_text}")

    # 벡터 DB에 저장
    # vector_db.add(doc_result.sanitized_text)

    # 3계층: 출력 스캔
    llm_response = "The email is john@example.com"
    output_result = await security.scan_response(llm_response, namespaces=["comm"])

    if output_result.blocked:
        print("⚠ PII 유출로 인해 응답이 차단되었습니다")
    else:
        print(f"✓ 안전한 응답: {output_result.sanitized_text}")

asyncio.run(main())
```

**예상 출력:**
```
✓ 안전한 쿼리: Status for customer [EMAIL]?
✓ 벡터 DB용 안전한 문서: Customer: [EMAIL], Phone: [PHONE]
⚠ PII 유출로 인해 응답이 차단되었습니다
```

---

## 핵심 개념

### 3계층 아키텍처

```
사용자 쿼리
    ↓
┌─────────────────────────┐
│ 1계층: 입력             │  ← RAG 전에 쿼리 스캔
│ 동작: SANITIZE          │
└─────────────────────────┘
    ↓ (안전한 쿼리)
┌─────────────────────────┐
│ 벡터 DB 검색            │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 2계층: 저장소           │  ← 인덱싱 전에 문서 스캔
│ 동작: TOKENIZE          │
└─────────────────────────┘
    ↓ (정리된 문서)
┌─────────────────────────┐
│ LLM 처리                │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 3계층: 출력             │  ← 반환 전에 응답 스캔
│ 동작: BLOCK             │
└─────────────────────────┘
    ↓
안전한 응답
```

### 보안 정책

각 계층은 설정 가능한 보안 정책을 가집니다:

```python
from datadetector.rag_models import SecurityPolicy, SecurityAction, SecurityLayer

policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    action=SecurityAction.SANITIZE,  # block | sanitize | warn | allow
    severity_threshold=SeverityLevel.MEDIUM,
    redaction_strategy=RedactionStrategy.FAKE
)
```

---

## 예제

### 예제 1: 민감한 쿼리 차단

**시나리오:** 높은 심각도의 PII를 포함한 쿼리 거부 (예: 주민등록번호).

```python
from datadetector.rag_models import SecurityPolicy, SecurityAction, SecurityLayer, SeverityLevel

# 엄격한 차단 정책 생성
strict_policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    action=SecurityAction.BLOCK,
    severity_threshold=SeverityLevel.HIGH
)

# 정책 적용
security.update_policy(SecurityLayer.INPUT, strict_policy)

# 민감한 쿼리로 테스트
result = await security.scan_query("Process SSN 123-45-6789", namespaces=["us"])

print(f"차단됨: {result.blocked}")
print(f"이유: {result.reason}")
```

**출력:**
```
차단됨: True
이유: Query contains 1 high-severity PII matches
```

### 예제 2: 벡터 DB용 문서 정리

**시나리오:** FAKE 데이터를 사용하여 인덱싱 전에 문서에서 PII 제거.

```python
from datadetector.models import RedactionStrategy
from datadetector.rag_models import SecurityPolicy, SecurityLayer

# FAKE 전략을 사용한 정책 (임베딩에 더 좋음)
storage_policy = SecurityPolicy(
    layer=SecurityLayer.STORAGE,
    action=SecurityAction.SANITIZE,
    redaction_strategy=RedactionStrategy.FAKE
)

security.update_policy(SecurityLayer.STORAGE, storage_policy)

# 문서 스캔
document = """
Customer: John Doe
Email: john@example.com
Phone: 555-0123
"""

result = await security.scan_document(document, namespaces=["comm"])

print(f"원본:\n{document}")
print(f"\n정리됨:\n{result.sanitized_text}")

# 벡터 DB에 저장
# vector_db.add(result.sanitized_text)
```

**출력:**
```
원본:
Customer: John Doe
Email: john@example.com
Phone: 555-0123

정리됨:
Customer: John Doe
Email: fake123@example.com
Phone: 555-9876
```

### 예제 3: 역변환을 사용한 토큰화

**시나리오:** 내부 시스템을 위한 역변환 가능한 토큰 사용.

```python
from datadetector.tokenization import SecureTokenizer

tokenizer = SecureTokenizer(engine)

# 문서 토큰화
document = "Email: john@example.com, SSN: 123-45-6789"
sanitized, token_map = tokenizer.tokenize_with_map(document, namespaces=["comm", "us"])

print(f"토큰화됨: {sanitized}")
print(f"토큰 맵: {token_map.tokens}")

# 벡터 DB에 정리된 버전 저장
# vector_db.add(sanitized)

# 토큰 맵을 안전하게 저장 (암호화됨)
# secure_db.save(token_map, encrypted=True)

# 나중에 권한이 있으면 역변환
detokenized = tokenizer.detokenize(sanitized, token_map)
print(f"역토큰화됨: {detokenized}")
```

**출력:**
```
토큰화됨: Email: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]
토큰 맵: {'[TOKEN:comm:email:0]': 'john@example.com', '[TOKEN:us:ssn:1]': '123-45-6789'}
역토큰화됨: Email: john@example.com, SSN: 123-45-6789
```

---

## 수정 전략

### 전략 비교

| 전략 | 속도 | 역변환 가능 | 최적 사용처 | 예제 |
|----------|-------|------------|----------|------------|
| **MASK** | ⚡ 가장 빠름 | ❌ 아니요 | 출력 차단 | `***@***.com` |
| **FAKE** | ⚡ 빠름 | ❌ 아니요 | 저장소 (RAG) | `fake@example.com` |
| **TOKENIZE** | ⚡ 빠름 | ✅ 예 | 규정 준수 | `[TOKEN:0]` |
| **HASH** | ⚡ 빠름 | ❌ 아니요 | 분석 | `[HASH:a1b2c3]` |

### MASK 전략

```python
from datadetector.models import RedactionStrategy

result = engine.redact(
    "Email: john@example.com",
    strategy=RedactionStrategy.MASK
)
print(result.redacted_text)
# 출력: "Email: ***@***.com"
```

**장점:** 간단하고 빠름
**단점:** 임베딩에 나쁘고, 부자연스러움

### FAKE 전략

```python
result = engine.redact(
    "Email: john@example.com",
    strategy=RedactionStrategy.FAKE
)
print(result.redacted_text)
# 출력: "Email: fake123@example.com"
```

**장점:** 자연스럽고, 더 나은 임베딩
**단점:** 약간 느리고, faker 라이브러리 필요

### TOKENIZE 전략

```python
from datadetector.tokenization import SecureTokenizer

tokenizer = SecureTokenizer(engine)
sanitized, token_map = tokenizer.tokenize_with_map("Email: john@example.com")
print(sanitized)
# 출력: "Email: [TOKEN:comm:email:0]"

# 역변환 가능
original = tokenizer.detokenize(sanitized, token_map)
print(original)
# 출력: "Email: john@example.com"
```

**장점:** 역변환 가능, 안전
**단점:** 토큰 맵 저장 필요

### HASH 전략

```python
result = engine.redact(
    "Email: john@example.com",
    strategy=RedactionStrategy.HASH
)
print(result.redacted_text)
# 출력: "Email: [HASH:a1b2c3d4e5f6]"
```

**장점:** 최대 보안, 단방향
**단점:** 역변환 불가, UX 나쁨

---

## 설정

### YAML 설정

`config/rag_security_policy.yml` 편집:

```yaml
# 입력 계층
input_layer:
  enabled: true
  action: sanitize
  redaction_strategy: fake  # ← 선택: mask | fake | tokenize | hash
  namespaces:
    - comm
    - us

# 저장소 계층
storage_layer:
  enabled: true
  action: sanitize
  redaction_strategy: tokenize  # ← 선택: mask | fake | tokenize | hash
  preserve_format: true

# 출력 계층
output_layer:
  enabled: true
  action: block
  redaction_strategy: mask  # ← 선택: mask | fake | tokenize | hash
  severity_threshold: high
```

### 설정 로드

```python
from datadetector import load_rag_policy

# YAML에서 로드
policy_config = load_rag_policy("config/rag_security_policy.yml")

# 로드된 정책으로 미들웨어 생성
security = RAGSecurityMiddleware(
    engine,
    input_policy=policy_config.get_input_policy(),
    storage_policy=policy_config.get_storage_policy(),
    output_policy=policy_config.get_output_policy()
)
```

### REST API 설정

```bash
# 서버 시작
data-detector serve --port 8080

# API 사용
curl -X POST http://localhost:8080/rag/scan-query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Email john@example.com",
    "action": "sanitize",
    "namespaces": ["comm"]
  }'
```

---

## 모범 사례

### 1. 계층별로 다른 전략 사용

**이렇게 하세요:**
```python
# ✅ 최적화된 설정
input_policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    redaction_strategy=RedactionStrategy.FAKE  # 자연스러운 쿼리
)

storage_policy = SecurityPolicy(
    layer=SecurityLayer.STORAGE,
    redaction_strategy=RedactionStrategy.TOKENIZE  # 역변환 가능
)

output_policy = SecurityPolicy(
    layer=SecurityLayer.OUTPUT,
    redaction_strategy=RedactionStrategy.MASK  # 빠른 차단
)
```

**이유:** 각 계층은 다른 요구사항이 있습니다. 입력/저장소는 자연스러운 텍스트가 필요하고, 출력은 빠른 차단이 필요합니다.

### 2. 성능을 위해 네임스페이스 제한

**이렇게 하세요:**
```python
# ✅ 관련 패턴만 스캔
result = await security.scan_query(
    query,
    namespaces=["comm"]  # 이메일/전화만
)
```

**이렇게 하지 마세요:**
```python
# ❌ 모든 패턴을 불필요하게 스캔
result = await security.scan_query(query)  # 모든 네임스페이스
```

**이유:** 관련 네임스페이스만 스캔하는 것이 2-3배 빠릅니다.

### 3. 토큰 맵을 안전하게 저장

**이렇게 하세요:**
```python
# ✅ 암호화하고 분리된 저장소 사용
from cryptography.fernet import Fernet

cipher = Fernet(encryption_key)
encrypted = cipher.encrypt(json.dumps(token_map.tokens).encode())

# 별도의 안전한 데이터베이스에 저장
secure_db.save(doc_id, encrypted, access_level="admin_only")
```

**이렇게 하지 마세요:**
```python
# ❌ 벡터 DB에 암호화되지 않은 상태로 저장
vector_db.add({
    'text': sanitized,
    'token_map': token_map.tokens  # 하지 마세요!
})
```

**이유:** 토큰 맵은 원본 PII를 포함하므로 암호화되고 접근 제어되어야 합니다.

---

## 문제 해결

### 문제: "FakeDataGenerator not available"

**증상:**
- FAKE 전략 사용 시 경고
- MASK 전략으로 폴백

**해결책:**
```bash
pip install faker
```

**설명:** FAKE 전략은 현실적인 데이터 생성을 위해 `faker` 라이브러리가 필요합니다.

### 문제: 느린 성능

**증상:**
- 응답 시간 > 50ms
- 높은 CPU 사용량

**해결책:**
```python
# 감지만을 위해 stop_on_first_match 사용
result = await security.scan_query(
    query,
    namespaces=["comm"],  # 네임스페이스 제한
    stop_on_first_match=True  # 2-3배 빠름
)
```

**설명:** 모든 네임스페이스의 모든 패턴을 스캔하는 것은 느립니다. 관련 패턴으로 제한하세요.

### 문제: 토큰 맵 저장

**증상:**
- "Token map not found" 오류
- 역토큰화 불가

**해결책:**
```python
# 역토큰화 전에 토큰 맵이 저장되었는지 확인
sanitized, token_map = tokenizer.tokenize_with_map(text)

# 토큰 맵 저장
secure_db.save(doc_id, encrypt(token_map.tokens))

# 나중에 역토큰화 전에 검색
retrieved_map = decrypt(secure_db.get(doc_id))
detokenized = tokenizer.detokenize(sanitized, TokenMap(tokens=retrieved_map))
```

**설명:** 토큰 맵은 역토큰화를 위해 명시적으로 저장하고 검색해야 합니다.

---

## 관련 문서

**핵심 문서:**
- [설치 가이드](installation.md) - data-detector 시작하기
- [아키텍처](RAG_SECURITY_ARCHITECTURE.md) - 상세 시스템 아키텍처

**RAG 보안:**
- [RAG 보안 아키텍처](RAG_SECURITY_ARCHITECTURE.md) - 완전한 아키텍처 가이드
- [RAG 통합](rag-integration.md) - 프레임워크 통합 가이드
- [토큰 맵 저장](TOKEN_MAP_STORAGE.md) - 안전한 토큰 저장 가이드

**고급 주제:**
- [사용자 정의 패턴](custom-patterns.md) - 사용자 정의 PII 패턴 생성
- [검증 함수](verification.md) - 검증 로직 추가

---

## 지원

- 📖 **전체 문서**: [RAG 보안 아키텍처](RAG_SECURITY_ARCHITECTURE.md)
- 💻 **예제**: `examples/rag_quickstart.py` 실행
- ⚙️ **설정**: `config/rag_security_policy.yml` 편집
- 🐛 **이슈**: [GitHub Issues](https://github.com/yourusername/data-detector/issues)
- 💬 **토론**: [GitHub Discussions](https://github.com/yourusername/data-detector/discussions)

---

**마지막 업데이트:** 2025-11-29 | **버전:** 0.0.2
