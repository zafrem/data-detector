# Configuration Guide

Data Detector is highly configurable, allowing you to control everything from server settings to redaction strategies. Configuration can be provided through a YAML file, environment variables, or command-line arguments.

## The `config.yml` File

The most common way to configure Data Detector is by using a `config.yml` file. It provides a single place to manage all settings.

**Example `config.yml`:**
```yaml
# Server settings control the network interface (host, port, TLS).
server:
  port: 8080
  host: "0.0.0.0"
  tls: false
  cert_file: ""  # Path to TLS certificate
  key_file: ""   # Path to TLS key

# Security settings protect the server with API keys and rate limiting.
security:
  api_key_required: false
  api_key: ""  # The secret key clients must provide if api_key_required is true
  rate_limit_rps: 100  # Max requests per second

# Registry settings control how patterns are loaded and managed.
registry:
  paths:
    - patterns/  # Load all .yml/.yaml files from a directory
    # You can also specify individual files:
    # - patterns/common.yml
    # - patterns/kr.yml
  hot_reload: true
  reload_interval_seconds: 60
  validate_schema: true
  validate_examples: true

# Redaction settings define the default behavior for masking sensitive data.
redaction:
  default_strategy: mask  # Options: mask, hash, replace
  mask_char: "*"
  hash_algorithm: sha256  # Used for the "hash" strategy

# Observability settings configure logging, metrics, and health checks.
observability:
  metrics: prometheus
  metrics_path: /metrics
  health_path: /health
  log_level: INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Performance settings allow you to tune resource usage and throughput.
performance:
  max_text_size_bytes: 1048576  # 1MB limit for input text
  max_concurrent_requests: 1000
  worker_threads: 4
```

## Methods of Configuration

### 1. From a Configuration File

You can specify a configuration file when starting the server using the `--config` flag.
```bash
data-detector serve --config config.yml
```

### 2. From Environment Variables

All configuration options can be overridden using environment variables. This is useful for containerized deployments. The variables must be prefixed with `DATA_DETECTOR_`, and nested keys are joined with an underscore.

```bash
export DATA_DETECTOR_SERVER_PORT=8080
export DATA_DETECTOR_OBSERVABILITY_LOG_LEVEL=DEBUG
data-detector serve
```

### 3. Programmatic Configuration

When using Data Detector as a library, you can configure its components programmatically by passing arguments to the `load_registry` and `Engine` classes.

```python
from datadetector import Engine, load_registry

# Configure the registry at loading time
registry = load_registry(
    paths=["patterns/"],
    validate_schema=True,
    validate_examples=True
)

# Configure the engine at initialization
engine = Engine(
    registry=registry,
    default_mask_char="*",
    default_hash_algorithm="sha256"
)
```

## Configuration Precedence

Data Detector applies configuration in a specific order, with later sources overriding earlier ones. This gives you fine-grained control over your settings.

The order of precedence is as follows:
1.  **Default Values**: The hardcoded defaults in the application.
2.  **Configuration File**: Values loaded from `config.yml`.
3.  **Environment Variables**: Values set in the environment (e.g., `DATA_DETECTOR_SERVER_PORT`).
4.  **Command-Line Arguments**: Flags passed when running a command (e.g., `--port 8080`).

For example, if your `config.yml` sets the port to `8080`, but you set an environment variable `DATA_DETECTOR_SERVER_PORT=9090`, the server will start on port `9090`.

## Detailed Configuration Sections

### Server Configuration

Controls the server's network binding and TLS settings.

**Basic Server (HTTP):**
```yaml
server:
  port: 8080
  host: "0.0.0.0"
```

**Secure Server (HTTPS):**
To enable TLS, set `tls: true` and provide paths to your certificate and key files.
```yaml
server:
  port: 8443
  tls: true
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/key.pem"
```

### Security Configuration

Protects the server from unauthorized access and overuse.

```yaml
security:
  api_key_required: true
  api_key: "your-secret-api-key"
  rate_limit_rps: 100 # Requests per second
```

When `api_key_required` is `true`, clients must include the key in the `X-API-Key` header:
```bash
curl -H "X-API-Key: your-secret-api-key" \
  http://localhost:8080/find -d '{"text": "..."}'
```

### Registry Configuration

Defines how detection patterns are loaded and updated.

**Load All Patterns from a Directory:**
```yaml
registry:
  paths:
    - patterns/
```

**Load Specific Pattern Files:**
```yaml
registry:
  paths:
    - patterns/common.yml
    - patterns/kr.yml
    - patterns/custom.yml
```

**Hot Reload:**
When enabled, Data Detector will automatically monitor pattern files for changes and reload them without a server restart.
```yaml
registry:
  hot_reload: true
  reload_interval_seconds: 60 # How often to check for changes
```

**Validation Settings:**
These settings help ensure your patterns are well-formed and correct. It is highly recommended to keep these enabled during development.
```yaml
registry:
  validate_schema: true      # Validate pattern structure against the official JSON schema.
  validate_examples: true    # Test the examples in each pattern file to ensure they match as expected.
```

### Redaction Configuration

Determines how sensitive data is replaced after detection.

**Redaction Strategies:**
- **`mask`**: Replaces the detected text with a masking character (e.g., `***-****-****`).
- **`hash`**: Replaces the detected text with a hash of the original value (e.g., `[HASH:a1b2c3d4...]`).
- **`replace`**: Replaces the detected text with a static string, often the category of the data (e.g., `[PHONE_NUMBER]`).

```yaml
redaction:
  # The strategy to use if none is specified in a request.
  default_strategy: mask
  # The character to use for the 'mask' strategy.
  mask_char: "*"
  # The algorithm to use for the 'hash' strategy.
  # Options: md5, sha1, sha256, sha512
  hash_algorithm: sha256
```

### Observability Configuration

Configures logging, metrics, and health check endpoints.

**Logging:**
```yaml
observability:
  log_level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**Metrics (Prometheus):**
```yaml
observability:
  metrics: prometheus
  metrics_path: /metrics
```
You can access the metrics endpoint at `http://localhost:8080/metrics`.

**Health Checks:**
```yaml
observability:
  health_path: /health
```
You can access the health endpoint at `http://localhost:8080/health`.

### Performance Configuration

Allows you to set resource limits and tune performance.

```yaml
performance:
  max_text_size_bytes: 1048576  # 1MB max input size
  max_concurrent_requests: 1000 # Max number of parallel requests
  worker_threads: 4 # Number of threads for processing requests
```

### Docker and Kubernetes

Configuration can be easily managed in containerized environments using environment variables or by mounting `config.yml` as a volume or ConfigMap.

**Docker Compose:**
```yaml
version: '3.8'

services:
  data-detector:
    image: data-detector:latest
    ports:
      - "8080:8080"
    volumes:
      - ./patterns:/app/patterns
      - ./config.yml:/app/config.yml # Mount config file
    environment:
      # Or override with environment variables
      - DATA_DETECTOR_OBSERVABILITY_LOG_LEVEL=INFO
    command: serve --config /app/config.yml
```

**Kubernetes ConfigMap:**
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