# Configuration

## Configuration File

Example `config.yml`:

```yaml
server:
  port: 8080
  host: "0.0.0.0"
  tls: false
  cert_file: ""  # Path to TLS certificate
  key_file: ""   # Path to TLS key

security:
  api_key_required: false
  api_key: ""  # Set if api_key_required is true
  rate_limit_rps: 100  # Requests per second

registry:
  paths:
    - patterns/  # Load all .yml/.yaml files from directory
    # Or specify individual files:
    # - patterns/common.yml
    # - patterns/kr.yml
    # - patterns/us.yml
  hot_reload: true
  reload_interval_seconds: 60
  validate_schema: true
  validate_examples: true

redaction:
  default_strategy: mask  # Options: mask, hash, tokenize
  mask_char: "*"
  hash_algorithm: sha256  # For hash strategy

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

## Loading Configuration

### From File

```bash
data-detector serve --config config.yml
```

### From Environment Variables

```bash
export DATA_DETECTOR_PORT=8080
export DATA_DETECTOR_LOG_LEVEL=DEBUG
data-detector serve
```

### Programmatic Configuration

```python
from datadetector import Engine, load_registry

# Configure registry loading
registry = load_registry(
    paths=["patterns/"],
    validate_schema=True,
    validate_examples=True
)

# Configure engine
engine = Engine(
    registry=registry,
    default_mask_char="*",
    hash_algorithm="sha256"
)
```

## Server Configuration

### Basic Server

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

### Security

```yaml
security:
  api_key_required: true
  api_key: "your-secret-api-key"
  rate_limit_rps: 100
```

Use API key in requests:

```bash
curl -H "X-API-Key: your-secret-api-key" \
  http://localhost:8080/find -d '{"text": "..."}'
```

## Registry Configuration

### Load All Patterns from Directory

```yaml
registry:
  paths:
    - patterns/
```

### Load Specific Files

```yaml
registry:
  paths:
    - patterns/common.yml
    - patterns/kr.yml
    - patterns/us.yml
    - patterns/custom.yml
```

### Hot Reload

```yaml
registry:
  hot_reload: true
  reload_interval_seconds: 60
```

This automatically reloads patterns when files change, without restarting the server.

### Validation Settings

```yaml
registry:
  validate_schema: true      # Validate against JSON schema
  validate_examples: true    # Validate pattern examples
```

## Redaction Configuration

### Default Strategy

```yaml
redaction:
  default_strategy: mask  # Options: mask, hash, tokenize
```

Strategies:
- **mask**: Replace with mask characters (e.g., `***-****-****`)
- **hash**: Replace with hash (e.g., `[HASH:a1b2c3d4]`)
- **tokenize**: Replace with token reference (e.g., `[TOKEN:kr/mobile:0]`)

### Masking Configuration

```yaml
redaction:
  default_strategy: mask
  mask_char: "*"  # Character to use for masking
```

### Hashing Configuration

```yaml
redaction:
  default_strategy: hash
  hash_algorithm: sha256  # Options: md5, sha1, sha256, sha512
```

## Observability Configuration

### Logging

```yaml
observability:
  log_level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Metrics

```yaml
observability:
  metrics: prometheus
  metrics_path: /metrics
```

Access metrics:
```bash
curl http://localhost:8080/metrics
```

### Health Checks

```yaml
observability:
  health_path: /health
```

Access health endpoint:
```bash
curl http://localhost:8080/health
```

## Performance Configuration

### Resource Limits

```yaml
performance:
  max_text_size_bytes: 1048576  # 1MB max input size
  max_concurrent_requests: 1000
  worker_threads: 4
```

### Optimization

```yaml
performance:
  enable_caching: true
  cache_size: 10000  # Number of patterns to cache
```

## Environment Variables

All configuration options can be set via environment variables using the prefix `DATA_DETECTOR_`:

```bash
# Server
export DATA_DETECTOR_PORT=8080
export DATA_DETECTOR_HOST="0.0.0.0"

# Security
export DATA_DETECTOR_API_KEY="secret-key"
export DATA_DETECTOR_RATE_LIMIT_RPS=100

# Registry
export DATA_DETECTOR_PATTERN_PATHS="patterns/,custom/"
export DATA_DETECTOR_HOT_RELOAD=true

# Redaction
export DATA_DETECTOR_DEFAULT_STRATEGY=mask
export DATA_DETECTOR_MASK_CHAR="*"

# Observability
export DATA_DETECTOR_LOG_LEVEL=INFO
```

## Docker Configuration

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

## Configuration Precedence

Configuration is applied in this order (later overrides earlier):

1. Default values
2. Configuration file
3. Environment variables
4. Command-line arguments

Example:
```bash
# config.yml has port: 8080
# This overrides to port: 9090
DATA_DETECTOR_PORT=9090 data-detector serve --config config.yml
```
