# RAG 보안 통합 가이드

> **간단 요약**: 3계층 보안 아키텍처를 사용하여 RAG (검색 증강 생성) 시스템을 PII 유출로부터 보호하는 완전한 가이드.

---

## 📋 목차

- [개요](#개요)
- [빠른 시작](#빠른-시작)
- [핵심 개념](#핵심-개념)
- [API 참조](#api-참조)
- [통합 예제](#통합-예제)
- [보안 정책](#보안-정책)
- [모범 사례](#모범-사례)
- [성능 최적화](#성능-최적화)
- [문제 해결](#문제-해결)
- [관련 문서](#관련-문서)

---

## 개요

RAG 시스템은 사용자 쿼리를 처리하고, 관련 문서를 검색하며, LLM을 사용하여 응답을 생성합니다. 각 단계는 PII 유출 위험을 제시합니다:

- **사용자 쿼리**에 민감한 정보가 포함될 수 있음
- **검색된 문서**가 데이터베이스의 PII를 노출할 수 있음
- **LLM 응답**이 실수로 민감한 데이터를 유출할 수 있음

data-detector는 RAG 파이프라인을 보호하기 위한 **3계층 보호**를 제공합니다.

---

## 빠른 시작

### 설치

```bash
pip install data-detector
```

### 기본 사용법

```python
import asyncio
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

async def main():
    # 초기화
    registry = load_registry()
    engine = Engine(registry)
    security = RAGSecurityMiddleware(engine)

    # 1계층: 사용자 쿼리 스캔
    query = "What's the email for john@example.com?"
    result = await security.scan_query(query, namespaces=["comm"])

    if result.blocked:
        return "민감한 내용으로 인해 쿼리가 차단되었습니다"

    # 정리된 쿼리 사용
    sanitized_query = result.sanitized_text

    # 2계층: 인덱싱 전에 문서 스캔
    document = "Customer john@example.com, SSN: 123-45-6789"
    doc_result = await security.scan_document(document)

    # 벡터 DB에 정리된 버전 저장
    vector_db.add(doc_result.sanitized_text)

    # 나중에 역변환을 위해 토큰 맵을 안전하게 저장
    if doc_result.token_map:
        secure_storage.save(doc_result.token_map)

    # 3계층: LLM 응답 스캔
    llm_response = "Customer SSN is 123-45-6789"
    output_result = await security.scan_response(llm_response)

    if output_result.blocked:
        return "[응답 차단됨: 민감한 정보 포함]"

    return output_result.sanitized_text

asyncio.run(main())
```

---

## 핵심 개념

### 3계층 보안 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    RAG 파이프라인                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  사용자 쿼리                                             │
│       │                                                 │
│       ▼                                                 │
│  ┌──────────────────────────────────────┐              │
│  │  1계층: 입력 차단                    │              │
│  │  • PII 쿼리 스캔                     │              │
│  │  • RAG 전에 차단 또는 정리           │              │
│  │  • 민감한 쿼리 방지                  │              │
│  └────────────┬─────────────────────────┘              │
│               │                                         │
│               ▼                                         │
│  ┌──────────────────────────────────────┐              │
│  │  벡터 DB / 문서 검색                 │              │
│  └────────────┬─────────────────────────┘              │
│               │                                         │
│               ▼                                         │
│  ┌──────────────────────────────────────┐              │
│  │  2계층: 저장소 차단                  │              │
│  │  • 인덱싱 전에 문서 스캔             │              │
│  │  • PII 토큰화 (역변환 가능)          │              │
│  │  • 벡터 DB에 정리된 상태로 저장      │              │
│  └────────────┬─────────────────────────┘              │
│               │                                         │
│               ▼                                         │
│  ┌──────────────────────────────────────┐              │
│  │  LLM 처리                            │              │
│  └────────────┬─────────────────────────┘              │
│               │                                         │
│               ▼                                         │
│  ┌──────────────────────────────────────┐              │
│  │  3계층: 출력 차단                    │              │
│  │  • LLM 응답 스캔                     │              │
│  │  • 유출된 PII 차단                   │              │
│  │  • 최종 사용자 보호                  │              │
│  └────────────┬─────────────────────────┘              │
│               │                                         │
│               ▼                                         │
│  사용자에게 안전한 응답                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## API 참조

### REST API 엔드포인트

서버 시작:

```bash
data-detector serve --port 8080
```

#### 1계층: 쿼리 스캔

**엔드포인트:** `POST /rag/scan-query`

**요청:**
```json
{
  "query": "What's the email for john@example.com?",
  "namespaces": ["comm"],
  "action": "sanitize",
  "severity_threshold": "medium"
}
```

**응답:**
```json
{
  "sanitized_text": "What's the email for [EMAIL]?",
  "blocked": false,
  "pii_detected": true,
  "match_count": 1,
  "action_taken": "sanitize",
  "reason": "Sanitized 1 PII matches"
}
```

#### 2계층: 문서 스캔

**엔드포인트:** `POST /rag/scan-document`

**요청:**
```json
{
  "document": "Customer: john@example.com, SSN: 123-45-6789",
  "namespaces": ["comm", "us"],
  "action": "sanitize",
  "use_tokenization": true
}
```

**응답:**
```json
{
  "sanitized_text": "Customer: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]",
  "blocked": false,
  "pii_detected": true,
  "match_count": 2,
  "action_taken": "sanitize",
  "token_map": {
    "[TOKEN:comm:email:0]": "john@example.com",
    "[TOKEN:us:ssn:1]": "123-45-6789"
  }
}
```

#### 3계층: 응답 스캔

**엔드포인트:** `POST /rag/scan-response`

**요청:**
```json
{
  "response": "The customer SSN is 123-45-6789",
  "namespaces": ["us"],
  "action": "block",
  "severity_threshold": "high"
}
```

**응답:**
```json
{
  "sanitized_text": "[응답 차단됨: 민감한 정보 포함]",
  "blocked": true,
  "pii_detected": true,
  "match_count": 1,
  "action_taken": "block",
  "reason": "Response contains 1 high-severity PII matches"
}
```

---

## 통합 예제

### LangChain 통합

```python
from langchain.chains import RetrievalQA
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

# 보안 초기화
registry = load_registry()
engine = Engine(registry)
security = RAGSecurityMiddleware(engine)

# LangChain 설정
qa_chain = RetrievalQA.from_chain_type(...)

async def secure_query(query: str) -> str:
    """PII 보호를 사용한 쿼리 처리."""
    # 1계층: 입력 스캔
    input_result = await security.scan_query(query)
    if input_result.blocked:
        return "[쿼리 차단됨]"

    # RAG 실행
    response = await qa_chain.ainvoke(input_result.sanitized_text)

    # 3계층: 출력 스캔
    output_result = await security.scan_response(response)
    if output_result.blocked:
        return "[응답 차단됨]"

    return output_result.sanitized_text
```

### LlamaIndex 통합

```python
from llama_index.core import VectorStoreIndex
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

# 초기화
registry = load_registry()
engine = Engine(registry)
security = RAGSecurityMiddleware(engine)

# 안전한 문서 인덱싱
async def add_documents_securely(documents: list[str]):
    """PII 보호를 사용한 문서 추가."""
    sanitized_docs = []

    for doc in documents:
        # 2계층: 저장소 스캔
        result = await security.scan_document(doc)
        if not result.blocked:
            sanitized_docs.append(result.sanitized_text)

            # 나중을 위해 토큰 맵 저장
            if result.token_map:
                token_storage.save(result.token_map)

    # 정리된 문서 인덱싱
    index = VectorStoreIndex.from_documents(sanitized_docs)
    return index
```

### FastAPI 통합

```python
from fastapi import FastAPI, HTTPException
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

app = FastAPI()

# 시작 시 한 번 초기화
registry = load_registry()
engine = Engine(registry)
security = RAGSecurityMiddleware(engine)

@app.post("/chat")
async def chat_endpoint(query: str):
    """안전한 챗 엔드포인트."""
    # 1계층: 입력 보호
    input_result = await security.scan_query(query)

    if input_result.blocked:
        raise HTTPException(400, "쿼리에 민감한 정보가 포함되어 있습니다")

    # 여기서 RAG 처리
    response = await process_rag(input_result.sanitized_text)

    # 3계층: 출력 보호
    output_result = await security.scan_response(response)

    if output_result.blocked:
        raise HTTPException(500, "PII로 인해 응답이 차단되었습니다")

    return {"response": output_result.sanitized_text}
```

---

## 보안 정책

### 정책 설정

```python
from datadetector.rag_models import SecurityPolicy, SecurityAction, SecurityLayer, SeverityLevel

# 엄격한 정책: 모두 차단
strict = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    action=SecurityAction.BLOCK,
    severity_threshold=SeverityLevel.HIGH
)

# 관대한 정책: 경고만
lenient = SecurityPolicy(
    layer=SecurityLayer.OUTPUT,
    action=SecurityAction.WARN,
    severity_threshold=SeverityLevel.CRITICAL
)

# 토큰화를 사용한 저장소 정책
storage = SecurityPolicy(
    layer=SecurityLayer.STORAGE,
    action=SecurityAction.SANITIZE,
    redaction_strategy=RedactionStrategy.TOKENIZE,
    preserve_format=True
)

# 정책 적용
security.update_policy(SecurityLayer.INPUT, strict)
security.update_policy(SecurityLayer.STORAGE, storage)
```

### 보안 동작

| 동작 | 동작 방식 | 사용 사례 |
|--------|----------|----------|
| `BLOCK` | 작업을 완전히 거부 | 중요 PII, 공개 엔드포인트 |
| `SANITIZE` | PII 제거/마스킹, 계속 진행 | 대부분의 RAG 작업 |
| `WARN` | 경고 로그, 통과 허용 | 내부 도구, 모니터링 |
| `ALLOW` | 수정 없음 | 테스트, 예외 엔드포인트 |

### 심각도 수준

| 수준 | 예제 | 권장사항 |
|-------|----------|----------------|
| `LOW` | 이메일 주소 | SANITIZE |
| `MEDIUM` | 전화번호 | SANITIZE |
| `HIGH` | 주민등록번호, 신용카드 | BLOCK |
| `CRITICAL` | 비밀번호, API 키 | BLOCK |

---

## 모범 사례

### 1. 계층별 정책

각 계층에 다른 정책 사용:

```python
# 입력: 관대하게, 사용자가 일부 PII로 쿼리해야 할 수 있음
input_policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    action=SecurityAction.SANITIZE,
    severity_threshold=SeverityLevel.MEDIUM
)

# 저장소: 역변환을 위해 토큰화
storage_policy = SecurityPolicy(
    layer=SecurityLayer.STORAGE,
    action=SecurityAction.SANITIZE,
    redaction_strategy=RedactionStrategy.TOKENIZE
)

# 출력: 엄격하게, PII 절대 유출하지 않음
output_policy = SecurityPolicy(
    layer=SecurityLayer.OUTPUT,
    action=SecurityAction.BLOCK,
    severity_threshold=SeverityLevel.HIGH
)
```

### 2. 안전한 토큰 저장

토큰 맵을 암호화하여 저장:

```python
from cryptography.fernet import Fernet

# 암호화 키 생성 (한 번만, 안전하게 저장)
key = Fernet.generate_key()
cipher = Fernet(key)

# 토큰 맵 암호화
import json
token_data = json.dumps(token_map.tokens)
encrypted = cipher.encrypt(token_data.encode())

# 안전한 데이터베이스에 저장
db.store(doc_id, encrypted)

# 나중에 권한이 있으면 복호화
decrypted = cipher.decrypt(encrypted)
token_map = json.loads(decrypted)
```

### 3. 모니터링 및 알림

모든 PII 감지 로그:

```python
import logging

logger = logging.getLogger("rag_security")

async def monitored_scan_query(query: str):
    result = await security.scan_query(query)

    if result.has_pii:
        logger.warning(
            f"쿼리에서 PII 감지",
            extra={
                "match_count": result.match_count,
                "action": result.action_taken.value,
                "blocked": result.blocked
            }
        )

    return result
```

### 4. 네임스페이스 타겟팅

관련 PII 유형만 스캔:

```python
# 고객 서비스 챗봇
result = await security.scan_query(
    query,
    namespaces=["comm", "us"]  # 이메일, 전화, SSN
)

# 국제 애플리케이션
result = await security.scan_query(
    query,
    namespaces=["comm", "us", "kr", "jp"]  # 다중 지역
)
```

---

## 성능 최적화

### 1. 대용량 문서에 스트리밍 사용

```python
from datadetector import StreamEngine

stream_engine = StreamEngine(engine, max_concurrent=10)

# 여러 문서를 동시에 처리
results = await stream_engine.scan_batch(
    documents,
    namespaces=["comm"],
    stop_on_first=True  # 감지만 필요한 경우 더 빠름
)
```

### 2. 첫 번째 일치에서 중지

이진 감지용 (PII 있음/없음):

```python
result = await security.scan_query(
    query,
    namespaces=["comm"],
    stop_on_first_match=True  # 첫 번째 PII 발견 후 중지
)

if result.has_pii:
    # PII 케이스 처리
    pass
```

### 3. 패턴 캐시

패턴은 시작 시 한 번 컴파일되고 캐시됨:

```python
# 애플리케이션 시작 시 한 번 로드
registry = load_registry()
engine = Engine(registry)
security = RAGSecurityMiddleware(engine)

# 요청 간에 재사용
app.state.security = security
```

### 4. 일괄 처리

여러 항목을 동시에 처리:

```python
import asyncio

async def process_documents_batch(documents: list[str]):
    tasks = [
        security.scan_document(doc, namespaces=["comm"])
        for doc in documents
    ]
    return await asyncio.gather(*tasks)
```

---

## 성능 벤치마크

60개 이상의 패턴으로 테스트 기준:

| 작업 | 텍스트 크기 | 지연 시간 (p95) | 처리량 |
|-----------|-----------|---------------|------------|
| 쿼리 스캔 | 256 chars | < 5ms | 1000+ RPS |
| 문서 스캔 | 1KB | < 10ms | 500+ RPS |
| 응답 스캔 | 512 chars | < 8ms | 750+ RPS |

*1 vCPU, 512MB RAM에서 테스트 실행*

---

## 문제 해결

### 문제: 높은 지연 시간

**증상:**
- 응답 시간 > 50ms
- 느린 쿼리 처리
- 높은 CPU 사용량

**해결책:**
```python
# 필요한 패턴으로 네임스페이스 축소
result = await security.scan_query(
    query,
    namespaces=["comm"],  # 이메일/전화만 스캔
    stop_on_first_match=True  # 빠른 감지
)

# 동시 처리 활성화
from datadetector import StreamEngine
stream_engine = StreamEngine(engine, max_concurrent=10)
results = await stream_engine.scan_batch(documents)
```

**설명:** 네임스페이스를 제한하고 stop-on-first-match를 사용하면 처리 시간이 크게 단축됩니다.

### 문제: 토큰 맵 저장

**증상:**
- 토큰 맵이 안전하지 않게 저장됨
- 원본 PII 검색 불가
- 저장 오류

**해결책:**
```python
from cryptography.fernet import Fernet

# 암호화된 데이터베이스 사용 (파일 시스템 아님)
key = Fernet.generate_key()
cipher = Fernet(key)

# 토큰 맵 암호화
encrypted = cipher.encrypt(json.dumps(token_map.tokens).encode())
secure_db.store(doc_id, encrypted)

# 토큰 만료 정책 구현
secure_db.store(doc_id, encrypted, ttl=86400)  # 24시간
```

**설명:** 토큰 맵은 접근 제어가 있는 별도의 안전한 데이터베이스에 암호화되어 저장되어야 합니다.

### 문제: 거짓 양성

**증상:**
- 민감하지 않은 데이터가 민감한 것으로 표시됨
- 합법적인 쿼리 과도 차단
- 잘못된 패턴 일치

**해결책:**
```python
# 심각도 임계값 조정
policy = SecurityPolicy(
    severity_threshold=SeverityLevel.HIGH  # 높은 심각도 PII만
)

# 패턴에 대한 검증 함수 사용
# custom-patterns.md에서 검증 함수 참조

# 도메인에 맞게 패턴 사용자 정의
# 패턴에 도메인별 제외 추가
```

**설명:** 심각도 임계값을 조정하고 검증 함수를 추가하면 보안을 유지하면서 거짓 양성을 줄입니다.

---

## 관련 문서

**핵심 문서:**
- [설치 가이드](installation.md) - data-detector 시작하기
- [API 참조](api-reference.md) - 완전한 API 문서

**RAG 보안:**
- [RAG 빠른 시작](RAG_QUICKSTART.md) - 5분 빠른 시작 가이드
- [RAG 보안 아키텍처](RAG_SECURITY_ARCHITECTURE.md) - 상세 아키텍처 가이드
- [토큰 맵 저장](TOKEN_MAP_STORAGE.md) - 안전한 토큰 저장 가이드

**고급 주제:**
- [사용자 정의 패턴](custom-patterns.md) - 도메인별 패턴 생성
- [성능 가이드](performance.md) - 고급 최적화 기법

---

## 지원

- 📖 **전체 문서**: [docs/](.)
- 💻 **예제**: [examples/](../examples/)
- 🐛 **이슈**: [GitHub Issues](https://github.com/yourusername/data-detector/issues)
- 💬 **토론**: [GitHub Discussions](https://github.com/yourusername/data-detector/discussions)
- 🔒 **보안**: security@example.com으로 보안 이슈 비공개 보고

---

**마지막 업데이트:** 2025-11-29 | **버전:** 0.0.2
