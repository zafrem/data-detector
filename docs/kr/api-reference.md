# API 참조

## Python API

### 패턴 로드

#### `load_registry(paths=None, validate_schema=True, validate_examples=True)`

YAML 파일에서 패턴을 레지스트리로 로드합니다.

**매개변수:**
- `paths` (List[str], 선택): 파일 또는 디렉토리 경로 목록. None이면 기본 패턴을 로드합니다.
- `validate_schema` (bool): JSON 스키마에 대해 검증할지 여부. 기본값: True.
- `validate_examples` (bool): 패턴에 대해 예제를 검증할지 여부. 기본값: True.

**반환값:** `PatternRegistry`

**예제:**
```python
from datadetector import load_registry

# 디렉토리에서 로드
registry = load_registry(paths=["patterns/"])

# 특정 파일 로드
registry = load_registry(paths=["patterns/common.yml", "patterns/kr.yml"])

# 검증 없이 로드
registry = load_registry(
    paths=["patterns/"],
    validate_schema=False,
    validate_examples=False
)
```

### Engine 클래스

#### `Engine(registry, default_mask_char='*', hash_algorithm='sha256')`

PII 감지, 검증 및 수정을 위한 핵심 엔진.

**매개변수:**
- `registry` (PatternRegistry): 로드된 패턴이 있는 레지스트리
- `default_mask_char` (str): 마스킹을 위한 기본 문자. 기본값: '*'
- `hash_algorithm` (str): 해싱 전략을 위한 해시 알고리즘. 기본값: 'sha256'

#### `Engine.find(text, namespaces=None, allow_overlaps=False, include_matched_text=False)`

텍스트에서 모든 PII 일치를 찾습니다.

**매개변수:**
- `text` (str): 검색할 텍스트
- `namespaces` (List[str], 선택): 검색할 네임스페이스 목록. None이면 모두 검색합니다.
- `allow_overlaps` (bool): 겹치는 일치를 허용할지 여부. 기본값: False.
- `include_matched_text` (bool): 결과에 일치된 텍스트를 포함할지 여부. 기본값: False.

**반환값:** `FindResult`

**예제:**
```python
result = engine.find("Phone: 010-1234-5678, Email: test@example.com")
for match in result.matches:
    print(f"{match.category} at {match.start}-{match.end}")
```

#### `Engine.validate(text, ns_id)`

특정 패턴에 대해 텍스트를 검증합니다.

**매개변수:**
- `text` (str): 검증할 텍스트
- `ns_id` (str): 전체 네임스페이스/id (예: "kr/mobile_01")

**반환값:** `ValidationResult`

**예제:**
```python
result = engine.validate("010-1234-5678", "kr/mobile_01")
print(result.is_valid)  # True 또는 False
```

#### `Engine.redact(text, namespaces=None, strategy=None, allow_overlaps=False)`

텍스트에서 PII를 수정합니다.

**매개변수:**
- `text` (str): 수정할 텍스트
- `namespaces` (List[str], 선택): 검색할 네임스페이스 목록. None이면 모두 검색합니다.
- `strategy` (RedactionStrategy, 선택): 수정 전략 (mask/hash/tokenize). 기본값: mask.
- `allow_overlaps` (bool): 겹치는 일치를 허용할지 여부. 기본값: False.

**반환값:** `RedactionResult`

**예제:**
```python
result = engine.redact(
    "SSN: 900101-1234567",
    namespaces=["kr"],
    strategy="mask"
)
print(result.redacted_text)
```

### 데이터 모델

#### `FindResult`

찾기 작업의 결과.

**속성:**
- `text` (str): 원본 텍스트
- `matches` (List[Match]): 찾은 일치 목록
- `namespaces_searched` (List[str]): 검색된 네임스페이스
- `has_matches` (bool): 속성 - 일치가 발견되면 True
- `match_count` (int): 속성 - 일치 개수

#### `Match`

단일 패턴 일치 결과.

**속성:**
- `ns_id` (str): 전체 네임스페이스/id (예: "kr/mobile_01")
- `pattern_id` (str): 패턴 ID
- `namespace` (str): 네임스페이스
- `category` (Category): PII 카테고리
- `start` (int): 텍스트에서 시작 위치
- `end` (int): 텍스트에서 종료 위치
- `matched_text` (str, 선택): 일치된 텍스트 (정책이 허용하는 경우)
- `mask` (str, 선택): 마스크 템플릿
- `severity` (Severity): 심각도 수준

#### `ValidationResult`

검증 작업의 결과.

**속성:**
- `text` (str): 검증된 텍스트
- `ns_id` (str): 사용된 패턴 네임스페이스/id
- `is_valid` (bool): 텍스트가 유효한지 여부
- `match` (Match, 선택): 유효한 경우 일치 세부 정보

#### `RedactionResult`

수정 작업의 결과.

**속성:**
- `original_text` (str): 원본 텍스트
- `redacted_text` (str): PII가 수정된 텍스트
- `strategy` (RedactionStrategy): 사용된 전략
- `matches` (List[Match]): 수정된 일치
- `redaction_count` (int): 수정 개수

### 검증 함수

#### `iban_mod97(value)`

Mod-97 체크 알고리즘을 사용하여 IBAN을 검증합니다.

**매개변수:**
- `value` (str): IBAN 문자열

**반환값:** `bool`

#### `luhn(value)`

Luhn 알고리즘(mod-10 체크섬)을 사용하여 검증합니다.

**매개변수:**
- `value` (str): 숫자 문자열

**반환값:** `bool`

#### `register_verification_function(name, func)`

사용자 정의 검증 함수를 등록합니다.

**매개변수:**
- `name` (str): 등록할 이름
- `func` (Callable[[str], bool]): 검증 함수

#### `get_verification_function(name)`

이름으로 검증 함수를 가져옵니다.

**매개변수:**
- `name` (str): 함수 이름

**반환값:** `Callable[[str], bool]` 또는 `None`

#### `unregister_verification_function(name)`

검증 함수의 등록을 해제합니다.

**매개변수:**
- `name` (str): 함수 이름

**반환값:** `bool` - 제거되면 True, 찾지 못하면 False

## REST API

### POST /find

텍스트에서 PII 일치를 찾습니다.

**요청:**
```json
{
  "text": "My phone is 010-1234-5678",
  "namespaces": ["kr"],
  "allow_overlaps": false,
  "include_matched_text": false
}
```

**응답:**
```json
{
  "text": "My phone is 010-1234-5678",
  "matches": [
    {
      "ns_id": "kr/mobile_01",
      "pattern_id": "mobile_01",
      "namespace": "kr",
      "category": "phone",
      "start": 12,
      "end": 25,
      "matched_text": null,
      "severity": "high"
    }
  ],
  "namespaces_searched": ["kr"],
  "match_count": 1
}
```

### POST /validate

패턴에 대해 텍스트를 검증합니다.

**요청:**
```json
{
  "text": "010-1234-5678",
  "ns_id": "kr/mobile_01"
}
```

**응답:**
```json
{
  "text": "010-1234-5678",
  "ns_id": "kr/mobile_01",
  "is_valid": true,
  "match": {
    "ns_id": "kr/mobile_01",
    "category": "phone",
    "start": 0,
    "end": 13
  }
}
```

### POST /redact

텍스트에서 PII를 수정합니다.

**요청:**
```json
{
  "text": "My SSN is 900101-1234567",
  "namespaces": ["kr"],
  "strategy": "mask",
  "allow_overlaps": false
}
```

**응답:**
```json
{
  "original_text": "My SSN is 900101-1234567",
  "redacted_text": "My SSN is ***-****-****",
  "strategy": "mask",
  "matches": [...],
  "redaction_count": 1
}
```

### GET /health

상태 확인 엔드포인트.

**응답:**
```json
{
  "status": "healthy",
  "version": "0.0.1",
  "patterns_loaded": 150,
  "namespaces": ["kr", "us", "co"]
}
```

### GET /metrics

Prometheus 메트릭 엔드포인트.

**응답:** (Prometheus 형식)
```
# HELP data_detector_requests_total Total requests
# TYPE data_detector_requests_total counter
data_detector_requests_total{method="find"} 1234
...
```

## CLI 참조

### data-detector find

텍스트에서 PII를 찾습니다.

```bash
data-detector find [OPTIONS]
```

**옵션:**
- `--text TEXT`: 검색할 텍스트
- `--file PATH`: 검색할 파일
- `--ns NAMESPACE`: 검색할 네임스페이스 (여러 개 지정 가능)
- `--output FORMAT`: 출력 형식 (json/text)

**예제:**
```bash
data-detector find --text "010-1234-5678" --ns kr
data-detector find --file input.txt --ns kr us --output json
```

### data-detector validate

패턴에 대해 텍스트를 검증합니다.

```bash
data-detector validate [OPTIONS]
```

**옵션:**
- `--text TEXT`: 검증할 텍스트
- `--ns-id NS_ID`: 패턴 네임스페이스/id

**예제:**
```bash
data-detector validate --text "010-1234-5678" --ns-id kr/mobile_01
```

### data-detector redact

텍스트에서 PII를 수정합니다.

```bash
data-detector redact [OPTIONS]
```

**옵션:**
- `--in PATH`: 입력 파일
- `--out PATH`: 출력 파일
- `--ns NAMESPACE`: 검색할 네임스페이스
- `--strategy STRATEGY`: 수정 전략 (mask/hash/tokenize)

**예제:**
```bash
data-detector redact --in input.log --out redacted.log --ns kr us
```

### data-detector serve

서버를 시작합니다.

```bash
data-detector serve [OPTIONS]
```

**옵션:**
- `--port PORT`: 서버 포트 (기본값: 8080)
- `--host HOST`: 서버 호스트 (기본값: 0.0.0.0)
- `--config PATH`: 설정 파일 경로

**예제:**
```bash
data-detector serve --port 8080 --config config.yml
```
