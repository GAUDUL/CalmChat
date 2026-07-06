FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    pkg-config \
    gcc \
    g++ \
    build-essential \
    libsndfile1 \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-deps --no-cache-dir \
    git+https://github.com/myshell-ai/OpenVoice.git \
    git+https://github.com/myshell-ai/MeloTTS.git

RUN python -m unidic download

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]