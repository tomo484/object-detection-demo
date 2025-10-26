# Dockerfile for FastAPI OCR Service
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新とOpenCV依存関係のインストール
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# アプリケーションコードをコピー
COPY api/ ./api/
COPY experiments/scripts/ ./scripts/

# ポート8000を公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# アプリケーションを起動
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
