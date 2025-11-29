# RAG 보안 아키텍처

> **간단 요약**: 상세한 아키텍처, 수정 전략, 설정을 포함한 RAG 애플리케이션을 위한 3계층 PII 보호 시스템의 포괄적인 가이드.

---

## 📋 목차

- [개요](#개요)
- [아키텍처 개요](#아키텍처-개요)
- [핵심 개념](#핵심-개념)
- [수정 전략](#수정-전략)
- [설정](#설정)
- [API 통합](#api-통합)
- [모범 사례](#모범-사례)
- [문제 해결](#문제-해결)
- [관련 문서](#관련-문서)

---

## 개요

### RAG 보안 아키텍처란?

RAG 보안 아키텍처는 3계층 방어 전략을 통해 검색 증강 생성 시스템에 대한 포괄적인 PII 보호를 제공합니다. 각 계층은 RAG 파이프라인의 특정 보안 위험을 다룹니다: 사용자 입력, 문서 저장, LLM 출력.

**주요 기능:**
- ✅ 3계층 보안 (입력 → 저장 → 출력)
- ✅ 4가지 수정 전략 (MASK, FAKE, TOKENIZE, HASH)
- ✅ YAML 기반 설정
- ✅ 고성능 (문서당 < 15ms)
- ✅ 프레임워크 통합 (LangChain, LlamaIndex)
- ✅ REST API 지원

**사용 사례:**
- PII 보호가 있는 고객 지원 챗봇
- 규정 준수가 필요한 내부 지식 베이스
- 엄격한 보안이 있는 공개 문서 검색
- 다중 테넌트 RAG 시스템

---

## 아키텍처 개요

### 시스템 설계

```
┌─────────────────────────────────────────────────────────────────┐
│                  RAG 보안 아키텍처                              │
└─────────────────────────────────────────────────────────────────┘

                         사용자 쿼리
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  1계층: 입력 보안                       │
        │  ─────────────────────────               │
        │  • 사용자 쿼리 스캔                     │
        │  • 민감한 쿼리 차단/정리                │
        │  • 전략: FAKE 또는 MASK                 │
        │  • 빠른 응답: < 5ms                     │
        └──────────────┬──────────────────────────┘
                       │ (정리된 쿼리)
                       ▼
        ┌─────────────────────────────────────────┐
        │  벡터 DB 쿼리                           │
        │  • 정리된 쿼리 사용                     │
        │  • 정리된 문서 검색                     │
        └──────────────┬──────────────────────────┘
                       │
                       ▼
        ┌─────────────────────────────────────────┐
        │  2계층: 저장소 보안                     │
        │  ──────────────────────────             │
        │  • 인덱싱 전에 스캔                     │
        │  • 역변환성을 위해 토큰화               │
        │  • 또는 임베딩을 위해 FAKE 사용         │
        │  • 성능: 1KB당 < 10ms                   │
        └──────────────┬──────────────────────────┘
                       │ (정리된 문서)
                       ▼
        ┌─────────────────────────────────────────┐
        │  LLM 처리                               │
        │  • 정리된 컨텍스트 처리                 │
        │  • 응답 생성                            │
        └──────────────┬──────────────────────────┘
                       │
                       ▼
        ┌─────────────────────────────────────────┐
        │  3계층: 출력 보안                       │
        │  ─────────────────────────              │
        │  • LLM 응답 스캔                        │
        │  • 유출된 PII 엄격하게 차단             │
        │  • 전략: BLOCK 또는 MASK                │
        │  • 중요 보호 계층                       │
        └──────────────┬──────────────────────────┘
                       │
                       ▼
                  안전한 응답
```

### 구성 요소 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│              RAGSecurityMiddleware                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────┐ │
│  │ 입력 정책      │  │ 저장소 정책    │  │출력 정책  │ │
│  │                │  │                │  │           │ │
│  │ action:        │  │ action:        │  │action:    │ │
│  │   sanitize     │  │   sanitize     │  │  block    │ │
│  │ strategy:      │  │ strategy:      │  │strategy:  │ │
│  │   fake         │  │   tokenize     │  │  mask     │ │
│  │ threshold:     │  │ threshold:     │  │threshold: │ │
│  │   medium       │  │   low          │  │  high     │ │
│  └────────┬───────┘  └────────┬───────┘  └─────┬─────┘ │
│           │                   │                 │       │
│           └───────────────────┴─────────────────┘       │
│                              │                          │
└──────────────────────────────┼──────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Engine             │
                    │                      │
                    │  • 패턴 레지스트리   │
                    │  • 수정 로직         │
                    │  • Fake 생성기       │
                    │  • 토큰화기          │
                    └──────────────────────┘
```

---

## 핵심 개념

### 3계층 보안

### 1계층: 입력 보안

**목적**: RAG 시스템에 민감한 쿼리가 들어오는 것을 방지

**시점**: 쿼리가 처리되거나 벡터 DB로 전송되기 전

**전략 옵션**:
- **SANITIZE** (권장): PII 제거, 안전한 쿼리로 계속
- **BLOCK**: PII를 포함한 쿼리 거부
- **WARN**: 로그만 남기고 허용 (내부 도구용)

**예제**:
```python
# 원본 쿼리
"What's the order status for customer john@example.com?"

# 입력 계층 후 (FAKE 전략)
"What's the order status for customer fake123@example.com?"

# 결과: 처리하기 안전하고, 쿼리 구조 유지
```

**성능**: 쿼리당 < 5ms

### 2계층: 저장소 보안

**목적**: 인덱싱된 문서의 PII 보호

**시점**: 문서가 임베딩되어 벡터 DB에 저장되기 전

**전략 옵션**:
- **TOKENIZE** (역변환 가능): 토큰으로 교체, 매핑 안전하게 저장
- **FAKE** (의미론적): 더 나은 임베딩을 위해 현실적인 데이터로 교체
- **MASK**: 간단한 마스킹 (RAG에 권장하지 않음)

**예제 - 토큰화**:
```python
# 원본 문서
"Customer: john@example.com, SSN: 123-45-6789"

# 저장소 계층 후 (TOKENIZE 전략)
"Customer: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]"

# 토큰 맵 (별도로 저장, 암호화됨)
{
  "[TOKEN:comm:email:0]": "john@example.com",
  "[TOKEN:us:ssn:1]": "123-45-6789"
}
```

**예제 - Fake 데이터**:
```python
# 원본 문서
"Customer: john@example.com, Phone: 555-0123"

# 저장소 계층 후 (FAKE 전략)
"Customer: fake456@example.com, Phone: 555-9876"

# 임베딩에 더 좋음: 의미론적 구조 보존
```

**성능**: 1KB 문서당 < 10ms

### 3계층: 출력 보안

**목적**: 응답에서 PII 유출에 대한 최종 방어

**시점**: LLM이 응답을 생성한 후, 사용자에게 반환하기 전

**전략 옵션**:
- **BLOCK** (권장): PII를 포함한 응답 거부
- **SANITIZE**: 응답에서 PII 제거
- **WARN**: 유출된 PII 로그만 남기고 허용

**예제**:
```python
# LLM 생성 (PII 유출)
"The customer's email is john@example.com"

# 출력 계층 후 (BLOCK)
"[응답 차단됨: 민감한 정보 포함]"

# 사용자는 안전한 오류 메시지 수신
```

**성능**: 응답당 < 8ms

---

## 수정 전략

### 1. MASK 전략

**설명**: PII를 별표 또는 패턴별 마스크로 교체

**장점**:
- ⚡ 가장 빠름 (< 2ms 오버헤드)
- 🔒 간단하고 안전함
- 📝 이해하기 쉬움

**단점**:
- ❌ 의미론적 구조 손상
- ❌ 임베딩에 나쁨
- ❌ LLM에 부자연스러움

**예제**:
```python
"Email: john@example.com"
→ "Email: ***@***.***"

"SSN: 123-45-6789"
→ "SSN: ***-**-****"
```

**최적 사용처**:
- 출력 계층 (차단)
- 간단한 로깅
- 비-RAG 사용 사례

### 2. FAKE 전략

**설명**: PII를 현실적인 가짜 데이터로 교체

**장점**:
- ✅ 의미론적 구조 보존
- ✅ RAG에 더 나은 임베딩
- ✅ LLM 처리에 자연스러움
- ✅ 텍스트 흐름 유지

**단점**:
- ⏱️ 약간 느림 (3-5ms 오버헤드)
- 🔀 비결정적 (매번 다름)
- 📦 faker 라이브러리 필요

**예제**:
```python
"Email: john@example.com"
→ "Email: fake123@example.com"

"Phone: 555-0123"
→ "Phone: 555-9876"

"SSN: 123-45-6789"
→ "SSN: 987-65-4321"
```

**최적 사용처**:
- 저장소 계층 (문서 인덱싱)
- 입력 계층 (쿼리 정리)
- RAG 시스템 (임베딩)

### 3. TOKENIZE 전략

**설명**: 역변환 가능한 토큰으로 교체

**장점**:
- 🔄 역변환 가능 (권한이 있으면 마스크 해제 가능)
- 🔒 안전 (맵 없이는 토큰이 의미 없음)
- 📊 감사 추적 가능

**단점**:
- 💾 안전한 토큰 맵 저장 필요
- 🔐 키 관리 복잡성
- 📝 텍스트에 부자연스러운 토큰

**예제**:
```python
"Email: john@example.com, SSN: 123-45-6789"
→ "Email: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]"

# 토큰 맵 안전하게 저장
{
  "[TOKEN:comm:email:0]": "john@example.com",
  "[TOKEN:us:ssn:1]": "123-45-6789"
}
```

**최적 사용처**:
- 저장소 계층 (역변환 필요 시)
- 감사 요구사항
- 규정 준수 필요

### 4. HASH 전략

**설명**: 암호화 해시로 교체

**장점**:
- 🔒 역변환 불가능 (최대 보안)
- 🔑 동일 입력 → 동일 해시
- ✅ 노출 없이 검증 가능

**단점**:
- ❌ 역변환 불가능 (데이터 손실)
- ❌ 임베딩에 부자연스러움
- ❌ UX 나쁨

**예제**:
```python
"Email: john@example.com"
→ "Email: [HASH:a1b2c3d4e5f6g7h8]"
```

**최적 사용처**:
- 최대 보안 시나리오
- 로깅/분석
- 단방향 익명화

---

## 설정

### YAML 설정 파일

**위치**: `config/rag_security_policy.yml`

### 기본 설정

```yaml
# 입력 계층 - 사용자 쿼리
input_layer:
  enabled: true
  action: sanitize  # block | sanitize | warn | allow
  severity_threshold: medium
  redaction_strategy: fake  # 선택: mask | fake | tokenize | hash
  namespaces:
    - comm  # 이메일, 전화, URL
    - us    # SSN, 신용카드
  log_matches: true

# 저장소 계층 - 문서 인덱싱
storage_layer:
  enabled: true
  action: sanitize
  severity_threshold: low
  redaction_strategy: fake  # 선택: mask | fake | tokenize | hash
  namespaces:
    - comm
    - us
  preserve_format: true
  log_matches: true

# 출력 계층 - LLM 응답
output_layer:
  enabled: true
  action: block
  severity_threshold: high
  redaction_strategy: mask  # 선택: mask | fake | tokenize | hash
  namespaces:
    - comm
    - us
  log_matches: true
```

### 설정 로드

```python
from datadetector import Engine, load_registry, load_rag_policy
from datadetector.rag_middleware import RAGSecurityMiddleware

# 패턴 로드 및 엔진 생성
registry = load_registry()
engine = Engine(registry)

# YAML에서 RAG 보안 정책 로드
policy_config = load_rag_policy("config/rag_security_policy.yml")

# 로드된 정책으로 미들웨어 생성
middleware = RAGSecurityMiddleware(
    engine,
    input_policy=policy_config.get_input_policy(),
    storage_policy=policy_config.get_storage_policy(),
    output_policy=policy_config.get_output_policy(),
)

# 미들웨어 사용
result = await middleware.scan_query("What's john@example.com's status?")
```

### 사전 설정 구성

#### 공개 챗봇 (엄격)
```yaml
input_layer:
  action: sanitize
  redaction_strategy: fake  # 쿼리 구조 보존
storage_layer:
  action: sanitize
  redaction_strategy: fake  # 더 나은 임베딩
output_layer:
  action: block  # 엄격한 차단
  severity_threshold: medium
```

#### 내부 도구 (관대)
```yaml
input_layer:
  action: warn  # 허용하지만 로그
  redaction_strategy: mask
storage_layer:
  action: sanitize
  redaction_strategy: tokenize  # 역변환 가능
output_layer:
  action: sanitize
  severity_threshold: high
```

#### 최대 보안
```yaml
input_layer:
  action: block
  severity_threshold: low
storage_layer:
  action: block
  severity_threshold: low
output_layer:
  action: block
  severity_threshold: low
```

---

## API 통합

### REST API

**서버 시작**:
```bash
data-detector serve --port 8080
```

**1계층: 쿼리 스캔**
```bash
curl -X POST http://localhost:8080/rag/scan-query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Email john@example.com about order",
    "action": "sanitize",
    "namespaces": ["comm"]
  }'
```

**응답**:
```json
{
  "sanitized_text": "Email fake123@example.com about order",
  "blocked": false,
  "pii_detected": true,
  "match_count": 1,
  "action_taken": "sanitize"
}
```

### Python 라이브러리

```python
import asyncio
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

async def secure_rag_pipeline(query: str, documents: list):
    # 초기화
    registry = load_registry()
    engine = Engine(registry)
    security = RAGSecurityMiddleware(engine)

    # 1계층: 입력
    input_result = await security.scan_query(query)
    if input_result.blocked:
        return "쿼리 차단됨"

    # 2계층: 저장소 (인덱싱 중)
    sanitized_docs = []
    for doc in documents:
        doc_result = await security.scan_document(doc)
        if not doc_result.blocked:
            sanitized_docs.append(doc_result.sanitized_text)

    # ... RAG 처리 ...

    # 3계층: 출력
    llm_response = "..."  # LLM에서
    output_result = await security.scan_response(llm_response)

    if output_result.blocked:
        return "[응답 차단됨]"

    return output_result.sanitized_text
```

---

## 모범 사례

### 성능 최적화

### 벤치마크

| 작업 | 텍스트 크기 | 전략 | 지연 시간 (p95) |
|-----------|-----------|----------|-----------------|
| 입력 스캔 | 256 chars | FAKE | < 5ms |
| 입력 스캔 | 256 chars | MASK | < 3ms |
| 문서 스캔 | 1KB | FAKE | < 15ms |
| 문서 스캔 | 1KB | TOKENIZE | < 10ms |
| 응답 스캔 | 512 chars | BLOCK | < 8ms |

### 최적화 팁

**1. 계층별로 적절한 전략 사용**
```python
# 필요한 곳에서 속도 최적화
input_policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    redaction_strategy=RedactionStrategy.FAKE  # 약간의 오버헤드 OK
)

output_policy = SecurityPolicy(
    layer=SecurityLayer.OUTPUT,
    redaction_strategy=RedactionStrategy.MASK  # 가장 빠름
)
```

**2. 네임스페이스 제한**
```python
# 관련 PII 유형만 스캔
await security.scan_query(
    query,
    namespaces=["comm"]  # 이메일/전화만, 모든 패턴 아님
)
```

**3. 대용량에 스트리밍 사용**
```python
from datadetector import StreamEngine

stream_engine = StreamEngine(engine, max_concurrent=10)

# 여러 문서를 동시에 처리
results = await stream_engine.scan_batch(documents)
```

**4. 첫 번째 일치에서 중지**
```python
# 이진 감지용 (PII 있음 예/아니오)
result = await security.scan_query(
    query,
    stop_on_first_match=True  # 더 빠름
)
```

### 사용 사례 예제

#### 1. 고객 지원 챗봇

**요구사항**:
- 사용자가 고객 이메일/전화로 쿼리
- 지식 베이스에 PII 있음
- 응답에서 PII 유출하면 안 됨

**설정**:
```yaml
input_layer:
  action: sanitize
  redaction_strategy: fake  # 쿼리 의미론 보존

storage_layer:
  action: sanitize
  redaction_strategy: tokenize  # 필요시 역변환 가능

output_layer:
  action: block  # 엄격
  severity_threshold: medium
```

#### 2. 내부 지식 베이스

**요구사항**:
- 내부 사용자가 접근 필요
- 문서에 PII 포함
- 업무를 위해 일부 PII가 필요할 수 있음

**설정**:
```yaml
input_layer:
  action: warn  # 허용하지만 로그

storage_layer:
  action: sanitize
  redaction_strategy: tokenize  # 역변환 가능

output_layer:
  action: sanitize
  severity_threshold: high
  allow_detokenization: true  # 권한 있는 사용자용
```

#### 3. 공개 문서 검색

**요구사항**:
- 공개 접근
- 최대 보안
- PII 존재하면 안 됨

**설정**:
```yaml
input_layer:
  action: block
  severity_threshold: low

storage_layer:
  action: block  # PII 문서 인덱싱하지 않음
  severity_threshold: low

output_layer:
  action: block
  severity_threshold: low
```

---

## 문제 해결

### 문제: 느린 성능

**증상:**
- 높은 지연 시간 (> 50ms)
- 느린 문서 처리
- CPU 병목현상

**해결책:**
```python
# 관련 네임스페이스로 제한
result = await security.scan_query(
    query,
    namespaces=["comm"],  # 이메일/전화만
    stop_on_first_match=True  # 더 빠름
)

# 일괄 처리에 스트리밍 사용
from datadetector import StreamEngine
stream = StreamEngine(engine, max_concurrent=10)
results = await stream.scan_batch(documents)
```

**설명:** 네임스페이스를 제한하고 동시 처리를 사용하면 성능이 크게 향상됩니다.

### 문제: 설정이 로드되지 않음

**증상:**
- YAML 설정이 적용되지 않음
- 기본 정책 사용
- 설정 오류

**해결책:**
```python
from datadetector import load_rag_policy

# 명시적으로 설정 로드
policy_config = load_rag_policy("config/rag_security_policy.yml")

# 정책이 로드되었는지 확인
print(f"입력 정책: {policy_config.get_input_policy()}")
print(f"저장소 정책: {policy_config.get_storage_policy()}")
print(f"출력 정책: {policy_config.get_output_policy()}")
```

**설명:** YAML 파일 경로가 올바른지 확인하고 미들웨어를 만들기 전에 설정이 명시적으로 로드되었는지 확인하세요.

### 문제: 응답에서 PII 유출

**증상:**
- LLM 응답에 원본 PII 포함
- 출력 계층이 차단하지 않음
- 토큰 역토큰화가 잘못 발생

**해결책:**
```python
# 엄격한 출력 정책 사용
output_policy = SecurityPolicy(
    layer=SecurityLayer.OUTPUT,
    action=SecurityAction.BLOCK,  # 엄격한 차단
    severity_threshold=SeverityLevel.MEDIUM
)

security.update_policy(SecurityLayer.OUTPUT, output_policy)

# 모든 응답 스캔
output_result = await security.scan_response(llm_response)
if output_result.blocked:
    return "[응답 차단됨]"  # 절대 원본 반환하지 않음
```

**설명:** 출력 계층은 PII 유출을 방지하기 위해 적절한 심각도 임계값과 함께 BLOCK 동작을 사용해야 합니다.

---

## 관련 문서

**핵심 문서:**
- [설치 가이드](installation.md) - data-detector 시작하기
- [아키텍처](ARCHITECTURE.md) - 시스템 설계 개요

**RAG 보안:**
- [RAG 빠른 시작](RAG_QUICKSTART.md) - 5분 빠른 시작 가이드
- [RAG 통합](rag-integration.md) - 완전한 통합 가이드
- [토큰 맵 저장](TOKEN_MAP_STORAGE.md) - 안전한 토큰 저장 가이드

**고급 주제:**
- [사용자 정의 패턴](custom-patterns.md) - 사용자 정의 PII 패턴 생성
- [검증 함수](verification.md) - 검증 로직 추가
- [성능 최적화](performance.md) - 고급 최적화

---

## 지원

- 📖 **문서**: [RAG 통합 가이드](rag-integration.md)
- 💻 **예제**: `examples/rag_quickstart.py` 실행
- ⚙️ **설정**: `config/rag_security_policy.yml` 편집
- 🐛 **이슈**: [GitHub Issues](https://github.com/yourusername/data-detector/issues)
- 💬 **토론**: [GitHub Discussions](https://github.com/yourusername/data-detector/discussions)
- 🔒 **보안**: security@example.com으로 비공개 보고

---

**마지막 업데이트:** 2025-11-29 | **버전:** 0.0.2
