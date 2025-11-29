# 설치 가이드

## 사전 요구사항

- Python 3.8 이상
- pip 패키지 관리자

## PyPI에서 설치

```bash
pip install data-detector
```

## 소스에서 설치

```bash
git clone https://github.com/yourusername/data-detector.git
cd data-detector
pip install -e .
```

## 개발 의존성과 함께 설치

```bash
pip install -e ".[dev]"
```

## Docker 설치

```bash
# 빌드
docker build -t data-detector:latest .

# 실행
docker run -p 8080:8080 -v ./patterns:/app/patterns data-detector:latest
```

## 설치 확인

```bash
data-detector --version
```

또는 Python에서:

```python
import datadetector
print(datadetector.__version__)
```
