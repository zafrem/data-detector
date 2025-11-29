# 安装指南

## 先决条件

- Python 3.8 或更高版本
- pip 包管理器

## 从 PyPI 安装

```bash
pip install data-detector
```

## 从源代码安装

```bash
git clone https://github.com/yourusername/data-detector.git
cd data-detector
pip install -e .
```

## 使用开发依赖项安装

```bash
pip install -e ".[dev]"
```

## Docker 安装

```bash
# 构建
docker build -t data-detector:latest .

# 运行
docker run -p 8080:8080 -v ./patterns:/app/patterns data-detector:latest
```

## 验证安装

```bash
data-detector --version
```

或在 Python 中：

```python
import datadetector
print(datadetector.__version__)
```
