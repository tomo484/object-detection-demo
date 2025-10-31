# OCR Analysis System

> **注意**: こちらはバックエンド側のリポジトリです。  
> フロントエンド側のリポジトリは [object-detection-web](https://github.com/tomo484/object-detection-web) をご確認ください。

## 概要

カメラ撮影画像のOCR解析を行うシステムです。Web側アプリケーションで撮影された画像を、FastAPI OCRサービスで解析し、数値データを抽出します。

## システム構成

### アーキテクチャ図

```
┌─────────────────────────────────────────┐
│ Container Apps Environment (共有)        │
│                                         │
│  ┌─────────────────┐  ┌───────────────┐ │
│  │ Web Container   │  │ OCR Container │ │
│  │                 │→ │               │ │
│  └─────────────────┘  └───────────────┘ │
└─────────────────────────────────────────┘
         ↓                       ↓
    ┌─────────┐              ┌─────────┐
    │Web側専用│              │OCR側専用│
    ├─────────┤              ├─────────┤
    │PostgreSQL│              │Computer │
    │Blob      │              │Vision   │
    │Storage   │              │API      │
    └─────────┘              └─────────┘
              ↓              ↑
         ┌─────────────────────┐
         │Container Registry   │
         │(共有)              │
         └─────────────────────┘
```

### 技術スタック

#### OCR API側
- **FastAPI**: Web APIフレームワーク
- **Azure Computer Vision**: OCR処理エンジン
- **OpenCV**: 画像前処理
- **Python 3.12**: ランタイム

#### インフラ構成
- **Azure Container Apps**: アプリケーションホスティング
- **Azure Container Registry**: Dockerイメージ管理
- **Azure Computer Vision API**: OCR処理サービス

## API仕様

### エンドポイント

#### POST /api/ocr/analyze
画像のOCR解析を実行します。

**リクエスト:**
```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD..."
}
```

**レスポンス（成功）:**
```json
{
  "success": true,
  "result": {
    "text_normalized": "10:03",
    "preprocessing_attempts": 2
  },
  "processing_time": 15.2,
  "metadata": {
    "total_lines_detected": 5,
    "numeric_candidates": 3
  }
}
```

**レスポンス（エラー）:**
```json
{
  "success": false,
  "error": {
    "code": "OCR_FAILED",
    "message": "No numeric content detected"
  }
}
```

#### GET /health
ヘルスチェックエンドポイントです。

**レスポンス:**
```json
{
  "status": "healthy",
  "message": "API is running"
}
```

## ローカル開発

### 環境構築

1. **仮想環境の作成・アクティベート**
   ```bash
   source venv/bin/activate
   ```

2. **依存関係のインストール**
   ```bash
   pip install -r requirements-api.txt
   ```

3. **環境変数の設定**
   ```bash
   # env.exampleを.envにコピーして編集
   cp env.example .env
   # .envファイルを編集して実際の値を設定
   VISION_ENDPOINT=https://your-vision.cognitiveservices.azure.com/
   VISION_KEY=your-api-key
   ```

### サーバー起動

```bash
# 開発サーバーを起動
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### テスト実行

```bash
# ヘルスチェック
curl http://localhost:8000/health

# OCR解析テスト
curl -X POST "http://localhost:8000/api/ocr/analyze" \
     -H "Content-Type: application/json" \
     -d "{\"image_base64\": \"data:image/jpeg;base64,$(base64 -w 0 data_ocr/images/ストップウォッチ-1_OCR用.jpg)\"}"
```

## デプロイ

### Azureリソース

以下のAzureリソースが必要です：

- **Azure Container Apps**: FastAPIアプリケーションのホスティング
- **Azure Container Registry**: Dockerイメージの管理
- **Azure Computer Vision API**: OCR処理サービス
- **Container Apps Environment**: 実行環境（Web側と共有）

### デプロイ手順

1. **Dockerイメージのビルド**
   ```bash
   docker build -t ocr-api:latest .
   ```

2. **Container Registryにプッシュ**
   ```bash
   az acr login --name yourregistry
   docker tag ocr-api:latest yourregistry.azurecr.io/ocr-api:latest
   docker push yourregistry.azurecr.io/ocr-api:latest
   ```

3. **Container Appsにデプロイ**
   ```bash
   az containerapp create \
     --name ocr-api \
     --resource-group your-rg \
     --environment your-env \
     --image yourregistry.azurecr.io/ocr-api:latest \
     --env-vars \
       VISION_ENDPOINT="https://your-vision.cognitiveservices.azure.com/" \
       VISION_KEY="your-api-key"
   ```

## プロジェクト構造

### プロダクション用
```
├── api/                       # FastAPI OCRサービス
│   ├── __init__.py
│   ├── main.py               # FastAPIアプリケーション
│   ├── models/
│   │   ├── __init__.py
│   │   ├── request.py        # リクエストモデル
│   │   └── response.py       # レスポンスモデル
│   ├── routers/
│   │   ├── __init__.py
│   │   └── ocr.py            # OCRエンドポイント
│   ├── services/
│   │   ├── __init__.py
│   │   └── ocr_service.py    # OCR処理ロジック
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # 設定管理
│   │   └── azure_client.py   # Azure Client管理
│   ├── dependencies.py       # 依存性注入
│   └── utils/
│       ├── __init__.py
│       └── image_processing.py # 画像処理ユーティリティ
├── Dockerfile                # Container Apps用
├── .dockerignore            # Docker除外設定
├── env.example              # 環境変数サンプル
├── requirements-api.txt     # 依存関係
├── README.md               # このファイル
└── .gitignore              # Git除外設定
```

### 実験・開発履歴
```
experiments/                 # 研究・実験用コード（参考用）
├── scripts/
│   └── ocr/
│       ├── run_ocr.py       # バッチOCR処理
│       ├── single_image_ocr.py # 単一画像OCR処理
│       └── preprocess/      # 前処理エンジン
├── data_ocr/               # OCR用テストデータ
├── runs/                   # 実験結果
├── docs/                   # 実験ドキュメント
└── config/                 # 実験設定
```

## 機能

### OCR処理
- **前処理エンジン**: 画像の品質向上による認識精度の改善
- **数値抽出**: 時刻、温度、計算結果などの数値データの抽出
- **正規化**: OCR結果の文字補正と正規化

### API機能
- **RESTful API**: 標準的なHTTP APIインターフェース
- **エラーハンドリング**: 適切なエラーレスポンスとログ出力
- **CORS対応**: クロスオリジンリクエストのサポート
- **ヘルスチェック**: システム状態の監視


