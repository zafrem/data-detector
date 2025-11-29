# 토큰 맵 저장소 가이드

> **간단 요약**: RAG 시스템에서 역변환 가능한 PII 토큰화를 위한 안전한 토큰 맵 저장소.

---

## 📋 목차

- [개요](#개요)
- [빠른 시작](#빠른-시작)
- [핵심 개념](#핵심-개념)
- [예제](#예제)
- [저장소 옵션](#저장소-옵션)
- [보안 고려사항](#보안-고려사항)
- [모범 사례](#모범-사례)
- [문제 해결](#문제-해결)
- [관련 문서](#관련-문서)

---

## 개요

### 토큰 맵 저장소란?

토큰 맵 저장소는 토큰화된 PII 데이터(토큰)를 원본 값으로 다시 변환할 수 있게 하는 시스템입니다. 이는 규정 준수, 감사 추적, 권한 있는 사용자 접근이 필요한 RAG 시스템에 필수적입니다.

**주요 기능:**
- ✅ 역변환 가능한 토큰화 (토큰 → 원본 값)
- ✅ 안전한 암호화 저장소
- ✅ 역할 기반 접근 제어
- ✅ 감사 추적 기능
- ✅ TTL(Time-To-Live) 만료
- ✅ 벡터 DB와 분리된 저장소

**사용 사례:**
- 권한 있는 사용자가 원본 PII를 볼 수 있어야 하는 내부 시스템
- 규정 준수를 위한 감사 추적이 필요한 경우
- 민감한 데이터에 대한 선택적 접근이 필요한 경우
- 긴급 상황을 위한 PII 복구가 필요한 경우

---

## 빠른 시작

### 설치

```bash
pip install data-detector
```

### 기본 예제

```python
from datadetector import Engine, load_registry
from datadetector.tokenization import SecureTokenizer

# 엔진 초기화
registry = load_registry()
engine = Engine(registry)
tokenizer = SecureTokenizer(engine)

# 토큰화 (토큰 맵 생성)
text = "Customer email: john@example.com, SSN: 123-45-6789"
sanitized, token_map = tokenizer.tokenize_with_map(text, namespaces=["comm", "us"])

print(f"토큰화됨: {sanitized}")
# 출력: "Customer email: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]"

print(f"토큰 맵: {token_map.tokens}")
# 출력: {'[TOKEN:comm:email:0]': 'john@example.com', '[TOKEN:us:ssn:1]': '123-45-6789'}

# ⚠️ 중요: 토큰 맵을 안전한 별도 데이터베이스에 저장
# ❌ 벡터 DB에 저장하지 마세요
# ✅ 암호화된 별도 저장소에 저장

# 나중에 권한이 있으면 역토큰화
detokenized = tokenizer.detokenize(sanitized, token_map)
print(f"역토큰화됨: {detokenized}")
# 출력: "Customer email: john@example.com, SSN: 123-45-6789"
```

---

## 핵심 개념

### 토큰화 vs 해시

**토큰화 (역변환 가능):**
- ✅ 원본 값으로 다시 변환 가능
- ✅ 권한 있는 접근 가능
- ✅ 감사 추적
- ⚠️ 토큰 맵을 안전하게 저장해야 함

```python
# 토큰화 (역변환 가능)
sanitized, token_map = tokenizer.tokenize_with_map(text)
# → "[TOKEN:comm:email:0]"
# 토큰 맵: {'[TOKEN:comm:email:0]': 'john@example.com'}

# 나중에 역변환 가능
original = tokenizer.detokenize(sanitized, token_map)
# → "john@example.com"
```

**해시 (역변환 불가능):**
- ❌ 역변환 불가능 (영구적)
- ✅ 최대 보안
- ✅ 저장소 필요 없음
- ❌ 원본 데이터 손실

```python
# 해시 (역변환 불가능)
result = engine.redact(text, strategy=RedactionStrategy.HASH)
# → "[HASH:a1b2c3d4e5f6]"
# ❌ 원본 값으로 되돌릴 수 없음
```

### 저장소 분리 아키텍처

```
┌────────────────────────────────────────────────────────┐
│                   RAG 시스템                           │
├────────────────────────────────────────────────────────┤
│                                                        │
│  원본 문서                                             │
│  "Customer: john@example.com"                          │
│           │                                            │
│           ▼                                            │
│  ┌──────────────────┐                                 │
│  │   토큰화         │                                 │
│  └────┬─────────────┘                                 │
│       │                                                │
│       ├─────────────────┬────────────────────┐        │
│       │                 │                    │        │
│       ▼                 ▼                    ▼        │
│  정리된 텍스트      토큰 맵             문서 ID       │
│  "[TOKEN:0]"        {'[TOKEN:0]':       "doc_123"    │
│                     'john@...'}                       │
│       │                 │                    │        │
│       ▼                 ▼                    │        │
│  ┌──────────┐     ┌──────────┐              │        │
│  │ 벡터 DB  │     │ 암호화   │              │        │
│  │(공개)    │     └────┬─────┘              │        │
│  │• 빠름    │          │                    │        │
│  │• 검색됨  │          ▼                    ▼        │
│  └──────────┘     ┌──────────────────────────┐       │
│                   │ 안전한 토큰 저장소       │       │
│                   │ (제한된 접근)            │       │
│                   │ • 암호화됨               │       │
│                   │ • 접근 제어              │       │
│                   │ • 감사 로그              │       │
│                   └──────────────────────────┘       │
└────────────────────────────────────────────────────────┘
```

**핵심 원칙:**
1. **벡터 DB**: 정리된 텍스트만 저장 (빠른 검색)
2. **토큰 저장소**: 암호화된 토큰 맵 (제한된 접근)
3. **절대 섞지 마세요**: 토큰 맵을 벡터 DB에 저장하지 마세요

---

## 예제

### 예제 1: PostgreSQL을 사용한 기본 저장소

```python
import psycopg2
import json
from cryptography.fernet import Fernet
from datadetector import Engine, load_registry
from datadetector.tokenization import SecureTokenizer, TokenMap

# 암호화 키 생성 (한 번만, 안전하게 저장)
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

# 데이터베이스 연결
conn = psycopg2.connect("dbname=secure_tokens user=admin password=***")
cur = conn.cursor()

# 토큰 맵 테이블 생성
cur.execute("""
    CREATE TABLE IF NOT EXISTS token_maps (
        doc_id VARCHAR(255) PRIMARY KEY,
        encrypted_token_map TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        accessed_by VARCHAR(255),
        access_count INTEGER DEFAULT 0
    )
""")
conn.commit()

# 토큰화 및 저장
registry = load_registry()
engine = Engine(registry)
tokenizer = SecureTokenizer(engine)

document = "Customer: john@example.com, SSN: 123-45-6789"
doc_id = "doc_123"

# 토큰화
sanitized, token_map = tokenizer.tokenize_with_map(document, namespaces=["comm", "us"])

# 토큰 맵 암호화
token_map_json = json.dumps(token_map.tokens)
encrypted = cipher.encrypt(token_map_json.encode())

# 안전한 저장소에 저장
cur.execute(
    "INSERT INTO token_maps (doc_id, encrypted_token_map) VALUES (%s, %s)",
    (doc_id, encrypted.decode())
)
conn.commit()

# 벡터 DB에 정리된 텍스트 저장
# vector_db.add(doc_id, sanitized)

print(f"✅ 정리된 텍스트가 벡터 DB에 저장됨")
print(f"✅ 암호화된 토큰 맵이 안전한 DB에 저장됨")

# 나중에: 권한이 있으면 검색 및 역토큰화
def retrieve_and_detokenize(doc_id: str, user: str) -> str:
    """권한 있는 사용자를 위해 역토큰화."""

    # 권한 확인 (예제)
    if user not in ["admin", "compliance_officer"]:
        raise PermissionError("토큰 맵 접근 권한이 없습니다")

    # 암호화된 토큰 맵 검색
    cur.execute(
        "SELECT encrypted_token_map FROM token_maps WHERE doc_id = %s",
        (doc_id,)
    )
    result = cur.fetchone()

    if not result:
        raise ValueError(f"문서 {doc_id}에 대한 토큰 맵을 찾을 수 없습니다")

    # 토큰 맵 복호화
    encrypted = result[0].encode()
    decrypted = cipher.decrypt(encrypted)
    tokens = json.loads(decrypted)

    # 접근 로그
    cur.execute(
        "UPDATE token_maps SET accessed_by = %s, access_count = access_count + 1 WHERE doc_id = %s",
        (user, doc_id)
    )
    conn.commit()

    # 역토큰화
    token_map = TokenMap(tokens=tokens)
    # vector_db에서 정리된 텍스트 가져오기
    # sanitized = vector_db.get(doc_id)

    original = tokenizer.detokenize(sanitized, token_map)
    return original

# 사용
try:
    original_doc = retrieve_and_detokenize("doc_123", user="admin")
    print(f"✅ 역토큰화 성공: {original_doc}")
except PermissionError as e:
    print(f"❌ 접근 거부: {e}")
```

### 예제 2: Redis를 사용한 TTL 지원

```python
import redis
import json
from cryptography.fernet import Fernet
from datadetector.tokenization import SecureTokenizer, TokenMap

# Redis 연결
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# 암호화 설정
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

# 토큰 맵 저장 (24시간 TTL)
def save_token_map_with_ttl(doc_id: str, token_map: TokenMap, ttl_seconds: int = 86400):
    """TTL이 있는 토큰 맵 저장."""

    # 암호화
    token_map_json = json.dumps(token_map.tokens)
    encrypted = cipher.encrypt(token_map_json.encode())

    # TTL이 있는 Redis에 저장
    redis_client.setex(
        f"token_map:{doc_id}",
        ttl_seconds,
        encrypted
    )

    print(f"✅ 토큰 맵이 {ttl_seconds}초 TTL로 저장됨")

# 토큰 맵 검색
def get_token_map(doc_id: str) -> TokenMap:
    """토큰 맵 검색 및 복호화."""

    # Redis에서 가져오기
    encrypted = redis_client.get(f"token_map:{doc_id}")

    if not encrypted:
        raise ValueError(f"토큰 맵이 만료되었거나 존재하지 않습니다: {doc_id}")

    # 복호화
    decrypted = cipher.decrypt(encrypted)
    tokens = json.loads(decrypted)

    return TokenMap(tokens=tokens)

# 사용
registry = load_registry()
engine = Engine(registry)
tokenizer = SecureTokenizer(engine)

document = "Email: john@example.com"
sanitized, token_map = tokenizer.tokenize_with_map(document)

# 24시간 TTL로 저장
save_token_map_with_ttl("doc_456", token_map, ttl_seconds=86400)

# 나중에 검색
try:
    retrieved_map = get_token_map("doc_456")
    original = tokenizer.detokenize(sanitized, retrieved_map)
    print(f"✅ 역토큰화됨: {original}")
except ValueError as e:
    print(f"❌ 오류: {e}")
```

### 예제 3: AWS KMS를 사용한 엔터프라이즈 저장소

```python
import boto3
import json
from datadetector.tokenization import SecureTokenizer, TokenMap

# AWS KMS 클라이언트
kms_client = boto3.client('kms', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# DynamoDB 테이블
token_table = dynamodb.Table('TokenMaps')

# KMS 키 ID
kms_key_id = 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012'

def save_token_map_kms(doc_id: str, token_map: TokenMap, user_id: str):
    """AWS KMS를 사용하여 토큰 맵 저장."""

    # KMS로 토큰 맵 암호화
    token_map_json = json.dumps(token_map.tokens)

    response = kms_client.encrypt(
        KeyId=kms_key_id,
        Plaintext=token_map_json.encode()
    )

    encrypted_blob = response['CiphertextBlob']

    # DynamoDB에 저장
    token_table.put_item(
        Item={
            'doc_id': doc_id,
            'encrypted_token_map': encrypted_blob,
            'created_by': user_id,
            'created_at': int(time.time()),
            'access_level': 'admin_only'
        }
    )

    print(f"✅ 토큰 맵이 KMS 암호화로 저장됨")

def retrieve_token_map_kms(doc_id: str, user_id: str, user_role: str) -> TokenMap:
    """AWS KMS를 사용하여 토큰 맵 검색."""

    # DynamoDB에서 가져오기
    response = token_table.get_item(Key={'doc_id': doc_id})

    if 'Item' not in response:
        raise ValueError(f"토큰 맵을 찾을 수 없습니다: {doc_id}")

    item = response['Item']

    # 접근 제어
    if item['access_level'] == 'admin_only' and user_role != 'admin':
        raise PermissionError("관리자만 접근 가능")

    # KMS로 복호화
    encrypted_blob = item['encrypted_token_map']

    response = kms_client.decrypt(
        CiphertextBlob=encrypted_blob
    )

    decrypted = response['Plaintext'].decode()
    tokens = json.loads(decrypted)

    # 감사 로그
    log_access(doc_id, user_id, 'token_map_access')

    return TokenMap(tokens=tokens)

# 사용
registry = load_registry()
engine = Engine(registry)
tokenizer = SecureTokenizer(engine)

document = "SSN: 123-45-6789"
sanitized, token_map = tokenizer.tokenize_with_map(document, namespaces=["us"])

# KMS 암호화로 저장
save_token_map_kms("doc_789", token_map, user_id="user_123")

# 나중에 검색 (권한 확인 포함)
try:
    retrieved_map = retrieve_token_map_kms("doc_789", user_id="user_123", user_role="admin")
    original = tokenizer.detokenize(sanitized, retrieved_map)
    print(f"✅ 역토큰화됨: {original}")
except PermissionError as e:
    print(f"❌ 접근 거부: {e}")
```

### 예제 4: 완전한 RAG 시스템

```python
import asyncio
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware
from datadetector.tokenization import SecureTokenizer, TokenMap
from cryptography.fernet import Fernet
import json

# 암호화 설정
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

# 토큰 저장소 (간단한 딕셔너리, 실제로는 데이터베이스 사용)
token_storage = {}

class SecureRAGSystem:
    """토큰 맵 저장소가 있는 완전한 RAG 시스템."""

    def __init__(self):
        registry = load_registry()
        self.engine = Engine(registry)
        self.security = RAGSecurityMiddleware(self.engine)
        self.tokenizer = SecureTokenizer(self.engine)
        self.vector_db = {}  # 간단한 벡터 DB (실제로는 Pinecone/Weaviate 사용)

    async def index_document(self, doc_id: str, document: str, user_id: str) -> str:
        """토큰 맵을 안전하게 저장하면서 문서 인덱싱."""

        # 2계층: 문서 스캔 및 토큰화
        sanitized, token_map = self.tokenizer.tokenize_with_map(
            document,
            namespaces=["comm", "us"]
        )

        # 벡터 DB에 정리된 텍스트 저장
        self.vector_db[doc_id] = sanitized

        # 토큰 맵 암호화 및 안전하게 저장
        token_map_json = json.dumps(token_map.tokens)
        encrypted = cipher.encrypt(token_map_json.encode())
        token_storage[doc_id] = {
            'encrypted_map': encrypted,
            'created_by': user_id,
            'access_level': 'admin_only'
        }

        return sanitized

    async def query(self, query: str, user_id: str) -> str:
        """안전한 쿼리 처리."""

        # 1계층: 입력 스캔
        input_result = await self.security.scan_query(query, namespaces=["comm", "us"])

        if input_result.blocked:
            return "[쿼리 차단됨]"

        # 벡터 DB 검색 (정리된 텍스트로)
        # ... RAG 처리 ...

        llm_response = "고객 이메일은 [TOKEN:comm:email:0]입니다"

        # 3계층: 출력 스캔
        output_result = await self.security.scan_response(llm_response, namespaces=["comm"])

        if output_result.blocked:
            return "[응답 차단됨]"

        return output_result.sanitized_text

    def retrieve_original(self, doc_id: str, user_role: str) -> str:
        """권한 있는 사용자를 위해 원본 문서 검색."""

        # 접근 제어
        if doc_id not in token_storage:
            raise ValueError("문서를 찾을 수 없습니다")

        stored = token_storage[doc_id]
        if stored['access_level'] == 'admin_only' and user_role != 'admin':
            raise PermissionError("관리자만 접근 가능")

        # 토큰 맵 복호화
        encrypted = stored['encrypted_map']
        decrypted = cipher.decrypt(encrypted)
        tokens = json.loads(decrypted)
        token_map = TokenMap(tokens=tokens)

        # 정리된 텍스트 가져오기
        sanitized = self.vector_db[doc_id]

        # 역토큰화
        original = self.tokenizer.detokenize(sanitized, token_map)
        return original

# 사용
async def main():
    system = SecureRAGSystem()

    # 문서 인덱싱
    doc = "고객 이메일: john@example.com, SSN: 123-45-6789"
    sanitized = await system.index_document("doc_001", doc, user_id="indexer_1")
    print(f"✅ 인덱싱됨: {sanitized}")

    # 쿼리
    response = await system.query("고객 이메일이 무엇인가요?", user_id="user_1")
    print(f"✅ 응답: {response}")

    # 관리자로 원본 검색
    try:
        original = system.retrieve_original("doc_001", user_role="admin")
        print(f"✅ 원본 (관리자): {original}")
    except PermissionError as e:
        print(f"❌ 접근 거부: {e}")

    # 일반 사용자로 시도
    try:
        original = system.retrieve_original("doc_001", user_role="user")
        print(f"✅ 원본 (사용자): {original}")
    except PermissionError as e:
        print(f"❌ 접근 거부: {e}")

asyncio.run(main())
```

**출력:**
```
✅ 인덱싱됨: 고객 이메일: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]
✅ 응답: 고객 이메일은 [TOKEN:comm:email:0]입니다
✅ 원본 (관리자): 고객 이메일: john@example.com, SSN: 123-45-6789
❌ 접근 거부: 관리자만 접근 가능
```

---

## 저장소 옵션

### 옵션 비교

| 저장소 | 암호화 | TTL | 접근 제어 | 확장성 | 복잡성 |
|---------|----------|-----|-----------|-----------|-----------|
| **PostgreSQL** | ✅ 앱 수준 | ⚠️ 수동 | ✅ 테이블 수준 | ⭐⭐⭐ | 보통 |
| **Redis** | ✅ 앱 수준 | ✅ 네이티브 | ⚠️ 제한적 | ⭐⭐⭐⭐ | 낮음 |
| **MongoDB** | ✅ 앱 수준 | ✅ 네이티브 | ✅ 문서 수준 | ⭐⭐⭐⭐ | 보통 |
| **AWS DynamoDB** | ✅ 네이티브 | ✅ 네이티브 | ✅ IAM | ⭐⭐⭐⭐⭐ | 높음 |
| **Azure Key Vault** | ✅ 네이티브 | ✅ 네이티브 | ✅ RBAC | ⭐⭐⭐⭐⭐ | 높음 |

### 권장사항

**개발/테스트:**
- Redis (빠르고 간단함)
- PostgreSQL (개발자에게 익숙함)

**프로덕션:**
- AWS DynamoDB + KMS (확장 가능, 안전함)
- Azure Key Vault (엔터프라이즈 보안)
- PostgreSQL + 열 수준 암호화 (비용 효율적)

---

## 보안 고려사항

### 1. 암호화는 필수

**이렇게 하세요:**
```python
# ✅ 항상 저장 전에 암호화
from cryptography.fernet import Fernet

cipher = Fernet(encryption_key)
encrypted = cipher.encrypt(json.dumps(token_map.tokens).encode())
db.store(doc_id, encrypted)
```

**이렇게 하지 마세요:**
```python
# ❌ 절대 평문으로 저장하지 마세요
db.store(doc_id, json.dumps(token_map.tokens))
```

### 2. 저장소 분리

**이렇게 하세요:**
```python
# ✅ 별도 저장소
vector_db.add(doc_id, sanitized_text)  # 빠른 검색
secure_db.add(doc_id, encrypted_token_map)  # 제한된 접근
```

**이렇게 하지 마세요:**
```python
# ❌ 절대 섞지 마세요
vector_db.add(doc_id, {
    'text': sanitized_text,
    'token_map': token_map.tokens  # 위험!
})
```

### 3. 접근 제어

**이렇게 하세요:**
```python
# ✅ 역할 기반 접근 제어
def get_token_map(doc_id: str, user_role: str):
    if user_role not in ['admin', 'compliance']:
        raise PermissionError("접근 거부")
    # ... 토큰 맵 검색 ...
```

### 4. 감사 로깅

**이렇게 하세요:**
```python
# ✅ 모든 접근 로그
def log_token_access(doc_id: str, user_id: str, action: str):
    audit_log.write({
        'timestamp': datetime.now(),
        'doc_id': doc_id,
        'user_id': user_id,
        'action': action,
        'ip_address': request.remote_addr
    })
```

---

## 모범 사례

### 1. 키 관리

**이렇게 하세요:**
```python
# ✅ 키를 환경 변수나 키 관리 서비스에 저장
import os
encryption_key = os.environ['ENCRYPTION_KEY']

# 또는 AWS Secrets Manager 사용
import boto3
secrets = boto3.client('secretsmanager')
response = secrets.get_secret_value(SecretId='token_encryption_key')
encryption_key = response['SecretString']
```

**이렇게 하지 마세요:**
```python
# ❌ 코드에 키를 하드코딩하지 마세요
encryption_key = b'hardcoded_key_12345'  # 위험!
```

### 2. TTL 정책

**이렇게 하세요:**
```python
# ✅ 토큰 맵에 적절한 TTL 설정
save_token_map(doc_id, token_map, ttl=86400)  # 24시간

# 또는 문서 유형별 다른 TTL
if doc_type == "temporary":
    ttl = 3600  # 1시간
elif doc_type == "archived":
    ttl = 31536000  # 1년
```

### 3. 토큰 맵 검증

**이렇게 하세요:**
```python
# ✅ 역토큰화 전에 토큰 맵 검증
def validate_token_map(token_map: TokenMap) -> bool:
    """토큰 맵 형식 확인."""
    if not isinstance(token_map.tokens, dict):
        return False

    for token, value in token_map.tokens.items():
        if not token.startswith('[TOKEN:'):
            return False
        if not isinstance(value, str):
            return False

    return True

# 사용
if not validate_token_map(retrieved_map):
    raise ValueError("잘못된 토큰 맵 형식")
```

### 4. 오류 처리

**이렇게 하세요:**
```python
# ✅ 명확한 오류 메시지
try:
    token_map = get_token_map(doc_id)
except KeyError:
    logger.error(f"토큰 맵을 찾을 수 없습니다: {doc_id}")
    raise ValueError(f"문서 {doc_id}에 대한 토큰 맵이 존재하지 않습니다")
except PermissionError:
    logger.warning(f"토큰 맵 접근 거부: {doc_id}, 사용자: {user_id}")
    raise
```

---

## 문제 해결

### 문제: 토큰 맵을 찾을 수 없음

**증상:**
- "Token map not found" 오류
- 역토큰화 실패
- 키 오류

**해결책:**
```python
# 저장 전에 토큰 맵이 생성되었는지 확인
sanitized, token_map = tokenizer.tokenize_with_map(text)
if not token_map.tokens:
    logger.warning("PII가 발견되지 않아 토큰 맵이 비어있습니다")

# 역토큰화 전에 저장되었는지 확인
if doc_id not in token_storage:
    raise ValueError(f"문서 {doc_id}에 대한 토큰 맵이 저장되지 않았습니다")

# 토큰 맵 저장
save_token_map(doc_id, token_map)
```

**설명:** 토큰 맵은 생성 직후 명시적으로 저장해야 합니다.

### 문제: 복호화 오류

**증상:**
- "Decryption failed" 오류
- 잘못된 암호문
- 키 불일치

**해결책:**
```python
# 암호화와 복호화에 동일한 키를 사용하는지 확인
# ✅ 키를 영구 저장소에 보관
with open('encryption.key', 'rb') as f:
    encryption_key = f.read()

cipher = Fernet(encryption_key)

# 복호화 시도 전에 키 확인
try:
    decrypted = cipher.decrypt(encrypted_data)
except InvalidToken:
    logger.error("잘못된 암호화 키 또는 손상된 데이터")
    raise ValueError("토큰 맵을 복호화할 수 없습니다")
```

**설명:** 암호화 키는 일관되게 관리되어야 하며 애플리케이션 수명 동안 변경되어서는 안 됩니다.

### 문제: 접근 거부

**증상:**
- PermissionError
- 권한 없는 사용자 접근
- 역할 확인 실패

**해결책:**
```python
# 명확한 역할 기반 접근 제어 구현
ALLOWED_ROLES = ['admin', 'compliance_officer', 'security_team']

def check_access(user_role: str, required_level: str):
    """접근 권한 확인."""
    if required_level == 'admin_only' and user_role not in ALLOWED_ROLES:
        raise PermissionError(
            f"역할 '{user_role}'은(는) 토큰 맵 접근이 허용되지 않습니다. "
            f"필요한 역할: {ALLOWED_ROLES}"
        )

# 검색 전에 확인
check_access(user_role, access_level='admin_only')
token_map = retrieve_token_map(doc_id)
```

**설명:** 토큰 맵 검색 전에 역할 기반 접근 제어를 구현하세요.

---

## 관련 문서

**핵심 문서:**
- [설치 가이드](installation.md) - data-detector 시작하기
- [아키텍처](ARCHITECTURE.md) - 시스템 설계

**RAG 보안:**
- [RAG 빠른 시작](RAG_QUICKSTART.md) - 5분 빠른 시작
- [RAG 보안 아키텍처](RAG_SECURITY_ARCHITECTURE.md) - 상세 아키텍처
- [RAG 통합](rag-integration.md) - 프레임워크 통합

**고급 주제:**
- [사용자 정의 패턴](custom-patterns.md) - 사용자 정의 PII 패턴
- [검증 함수](verification.md) - 검증 로직

---

## 지원

- 📖 **전체 문서**: [docs/](.)
- 💻 **예제**: [examples/](../examples/)
- 🐛 **이슈**: [GitHub Issues](https://github.com/yourusername/data-detector/issues)
- 💬 **토론**: [GitHub Discussions](https://github.com/yourusername/data-detector/discussions)
- 🔒 **보안**: security@example.com으로 비공개 보고

---

**마지막 업데이트:** 2025-11-29 | **버전:** 0.0.2
