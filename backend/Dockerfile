# Python 3.10 기반 (FastAPI + Whisper 호환)
FROM python:3.10-slim

# 시스템 패키지 설치 (ffmpeg 필수)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /app

# requirements 먼저 복사 (캐시 최적화)
COPY requirements.txt .

# pip 업그레이드 + 의존성 설치
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 전체 코드 복사
COPY . .

# FastAPI 실행 포트
EXPOSE 8000

# 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]