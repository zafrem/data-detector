# 설정

## 설정 파일

예제 `config.yml`:

```yaml
server:
  port: 8080
  host: "0.0.0.0"
  tls: false
  cert_file: ""  # TLS 인증서 경로
  key_file: ""   # TLS 키 경로

security:
  api_key_required: false
  api_key: ""  # api_key_required가 true이면 설정
  rate_limit_rps: 100  # 초당 요청 수

registry:
  paths:
    - patterns/  # 디렉토리의 모든 .yml/.yaml 파일 로드
    # 또는 개별 파일 지정:
    # - patterns/common.yml
    # - patterns/kr.yml
    # - patterns/us.yml
  hot_reload: true
  reload_interval_seconds: 60
  validate_schema: true
  validate_examples: true

redaction:
  default_strategy: mask  # 옵션: mask, hash, tokenize
  mask_char: "*"
  hash_algorithm: sha256  # 해시 전략용

observability:
  metrics: prometheus
  metrics_path: /metrics
  health_path: /health
  log_level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

performance:
  max_text_size_bytes: 1048576  # 1MB
  max_concurrent_requests: 1000
  worker_threads: 4
```

## 설정 로드

### 파일에서

```bash
data-detector serve --config config.yml
```

### 환경 변수에서

```bash
export DATA_DETECTOR_PORT=8080
export DATA_DETECTOR_LOG_LEVEL=DEBUG
data-detector serve
```

### 프로그래밍 방식 설정

```python
from datadetector import Engine, load_registry

# 레지스트리 로드 설정
registry = load_registry(
    paths=["patterns/"],
    validate_schema=True,
    validate_examples=True
)

# 엔진 설정
engine = Engine(
    registry=registry,
    default_mask_char="*",
    hash_algorithm="sha256"
)
```

## 서버 설정

### 기본 서버

```yaml
server:
  port: 8080
  host: "0.0.0.0"
```

### TLS/HTTPS

```yaml
server:
  port: 8443
  tls: true
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/key.pem"
```

### 보안

```yaml
security:
  api_key_required: true
  api_key: "your-secret-api-key"
  rate_limit_rps: 100
```

요청에서 API 키 사용:

```bash
curl -H "X-API-Key: your-secret-api-key" \
  http://localhost:8080/find -d '{"text": "..."}'
```

## 레지스트리 설정

### 디렉토리에서 모든 패턴 로드

```yaml
registry:
  paths:
    - patterns/
```

### 특정 파일 로드

```yaml
registry:
  paths:
    - patterns/common.yml
    - patterns/kr.yml
    - patterns/us.yml
    - patterns/custom.yml
```

### 핫 리로드

```yaml
registry:
  hot_reload: true
  reload_interval_seconds: 60
```

파일이 변경되면 서버를 재시작하지 않고 자동으로 패턴을 다시 로드합니다.

### 검증 설정

```yaml
registry:
  validate_schema: true      # JSON 스키마에 대해 검증
  validate_examples: true    # 패턴 예제 검증
```

## 수정 설정

### 기본 전략

```yaml
redaction:
  default_strategy: mask  # 옵션: mask, hash, tokenize
```

전략:
- **mask**: 마스크 문자로 교체 (예: `***-****-****`)
- **hash**: 해시로 교체 (예: `[HASH:a1b2c3d4]`)
- **tokenize**: 토큰 참조로 교체 (예: `[TOKEN:kr/mobile:0]`)

### 마스킹 설정

```yaml
redaction:
  default_strategy: mask
  mask_char: "*"  # 마스킹에 사용할 문자
```

### 해싱 설정

```yaml
redaction:
  default_strategy: hash
  hash_algorithm: sha256  # 옵션: md5, sha1, sha256, sha512
```

## 관찰성 설정

### 로깅

```yaml
observability:
  log_level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 메트릭

```yaml
observability:
  metrics: prometheus
  metrics_path: /metrics
```

메트릭 접근:
```bash
curl http://localhost:8080/metrics
```

### 상태 확인

```yaml
observability:
  health_path: /health
```

상태 엔드포인트 접근:
```bash
curl http://localhost:8080/health
```

## 성능 설정

### 리소스 제한

```yaml
performance:
  max_text_size_bytes: 1048576  # 최대 입력 크기 1MB
  max_concurrent_requests: 1000
  worker_threads: 4
```

### 최적화

```yaml
performance:
  enable_caching: true
  cache_size: 10000  # 캐시할 패턴 수
```

## 환경 변수

모든 설정 옵션은 `DATA_DETECTOR_` 접두사를 사용하여 환경 변수를 통해 설정할 수 있습니다:

```bash
# 서버
export DATA_DETECTOR_PORT=8080
export DATA_DETECTOR_HOST="0.0.0.0"

# 보안
export DATA_DETECTOR_API_KEY="secret-key"
export DATA_DETECTOR_RATE_LIMIT_RPS=100

# 레지스트리
export DATA_DETECTOR_PATTERN_PATHS="patterns/,custom/"
export DATA_DETECTOR_HOT_RELOAD=true

# 수정
export DATA_DETECTOR_DEFAULT_STRATEGY=mask
export DATA_DETECTOR_MASK_CHAR="*"

# 관찰성
export DATA_DETECTOR_LOG_LEVEL=INFO
```

## Docker 설정

### Docker Compose

```yaml
version: '3.8'

services:
  data-detector:
    image: data-detector:latest
    ports:
      - "8080:8080"
    volumes:
      - ./patterns:/app/patterns
      - ./config.yml:/app/config.yml
    environment:
      - DATA_DETECTOR_LOG_LEVEL=INFO
      - DATA_DETECTOR_HOT_RELOAD=true
    command: serve --config /app/config.yml
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: data-detector-config
data:
  config.yml: |
    server:
      port: 8080
    registry:
      paths:
        - patterns/
      hot_reload: true
    observability:
      log_level: INFO
```

## 설정 우선순위

설정은 다음 순서로 적용됩니다 (나중 것이 이전 것을 재정의):

1. 기본값
2. 설정 파일
3. 환경 변수
4. 명령줄 인자

예제:
```bash
# config.yml에 port: 8080이 있음
# 이것은 port: 9090으로 재정의됨
DATA_DETECTOR_PORT=9090 data-detector serve --config config.yml
```
