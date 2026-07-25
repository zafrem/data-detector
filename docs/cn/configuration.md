# 配置

## 配置文件

示例 `config.yml`：

```yaml
server:
  port: 8080
  host: "0.0.0.0"
  tls: false
  cert_file: ""  # TLS 证书路径
  key_file: ""   # TLS 密钥路径

security:
  api_key_required: false
  api_key: ""  # 如果 api_key_required 为 true 则设置
  rate_limit_rps: 100  # 每秒请求数

registry:
  paths:
    - patterns/  # 从目录加载所有 .yml/.yaml 文件
    # 或指定单个文件：
    # - patterns/common.yml
    # - patterns/kr.yml
    # - patterns/us.yml
  hot_reload: true
  reload_interval_seconds: 60
  validate_schema: true
  validate_examples: true

redaction:
  default_strategy: mask  # 选项：mask、hash、tokenize
  mask_char: "*"
  hash_algorithm: sha256  # 用于哈希策略

observability:
  metrics: prometheus
  metrics_path: /metrics
  health_path: /health
  log_level: INFO  # DEBUG、INFO、WARNING、ERROR、CRITICAL

performance:
  max_text_size_bytes: 1048576  # 1MB
  max_concurrent_requests: 1000
  worker_threads: 4
```

## 加载配置

### 从文件

```bash
data-detector serve --config config.yml
```

### 从环境变量

```bash
export DATA_DETECTOR_PORT=8080
export DATA_DETECTOR_LOG_LEVEL=DEBUG
data-detector serve
```

### 程序化配置

```python
from datadetector import Engine, load_registry

# 配置注册表加载
registry = load_registry(
    paths=["patterns/"],
    validate_schema=True,
    validate_examples=True
)

# 配置引擎
engine = Engine(
    registry=registry,
    default_mask_char="*",
    hash_algorithm="sha256"
)
```

## 服务器配置

### 基本服务器

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

### 安全性

```yaml
security:
  api_key_required: true
  api_key: "your-secret-api-key"
  rate_limit_rps: 100
```

在请求中使用 API 密钥：

```bash
curl -H "X-API-Key: your-secret-api-key" \
  http://localhost:8080/find -d '{"text": "..."}'
```

## 注册表配置

### 从目录加载所有模式

```yaml
registry:
  paths:
    - patterns/
```

### 加载特定文件

```yaml
registry:
  paths:
    - patterns/common.yml
    - patterns/kr.yml
    - patterns/us.yml
    - patterns/custom.yml
```

### 热重载

```yaml
registry:
  hot_reload: true
  reload_interval_seconds: 60
```

这会在文件更改时自动重新加载模式，无需重新启动服务器。

### 验证设置

```yaml
registry:
  validate_schema: true      # 针对 JSON 模式验证
  validate_examples: true    # 验证模式示例
```

## 脱敏配置

### 默认策略

```yaml
redaction:
  default_strategy: mask  # 选项：mask、hash、tokenize
```

策略：
- **mask**：用掩码字符替换（例如，`***-****-****`）
- **hash**：用哈希替换（例如，`[HASH:a1b2c3d4]`）
- **tokenize**：用令牌引用替换（例如，`[TOKEN:kr/mobile:0]`）

### 掩码配置

```yaml
redaction:
  default_strategy: mask
  mask_char: "*"  # 用于掩码的字符
```

### 哈希配置

```yaml
redaction:
  default_strategy: hash
  hash_algorithm: sha256  # 选项：md5、sha1、sha256、sha512
```

## 可观察性配置

### 日志记录

```yaml
observability:
  log_level: INFO  # DEBUG、INFO、WARNING、ERROR、CRITICAL
```

### 指标

```yaml
observability:
  metrics: prometheus
  metrics_path: /metrics
```

访问指标：
```bash
curl http://localhost:8080/metrics
```

### 健康检查

```yaml
observability:
  health_path: /health
```

访问健康端点：
```bash
curl http://localhost:8080/health
```

## 性能配置

### 资源限制

```yaml
performance:
  max_text_size_bytes: 1048576  # 1MB 最大输入大小
  max_concurrent_requests: 1000
  worker_threads: 4
```

### 优化

```yaml
performance:
  enable_caching: true
  cache_size: 10000  # 要缓存的模式数
```

## 环境变量

所有配置选项都可以使用前缀 `DATA_DETECTOR_` 通过环境变量设置：

```bash
# 服务器
export DATA_DETECTOR_PORT=8080
export DATA_DETECTOR_HOST="0.0.0.0"

# 安全性
export DATA_DETECTOR_API_KEY="secret-key"
export DATA_DETECTOR_RATE_LIMIT_RPS=100

# 注册表
export DATA_DETECTOR_PATTERN_PATHS="patterns/,custom/"
export DATA_DETECTOR_HOT_RELOAD=true

# 脱敏
export DATA_DETECTOR_DEFAULT_STRATEGY=mask
export DATA_DETECTOR_MASK_CHAR="*"

# 可观察性
export DATA_DETECTOR_LOG_LEVEL=INFO
```

## Docker 配置

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

## 配置优先级

配置按以下顺序应用（后者覆盖前者）：

1. 默认值
2. 配置文件
3. 环境变量
4. 命令行参数

示例：
```bash
# config.yml 有 port: 8080
# 这将覆盖为 port: 9090
DATA_DETECTOR_PORT=9090 data-detector serve --config config.yml
```
