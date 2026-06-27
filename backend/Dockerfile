# Python 3.10 기반 FastAPI + Whisper 이미지.
FROM python:3.10-slim

# 한국어 키워드/추천 문구 UTF-8 처리.
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Whisper 음성 처리 도구 설치.
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Docker 빌드 캐시 우선.
COPY requirements.txt .

# 백엔드 Python 의존성 설치.
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 애플리케이션 코드 복사.
COPY . .

EXPOSE 8000

# 개발 중 reload 실행.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
