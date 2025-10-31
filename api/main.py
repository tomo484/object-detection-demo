from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import ocr
from .core.config import settings


app = FastAPI(
    title="OCR Analysis API",
    description="カメラ撮影画像のOCR解析API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr.router, prefix="/api")


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "OCR Analysis API", "status": "running"}


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # 設定の検証
        settings.validate()
        return {"status": "healthy", "message": "API is running"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


@app.on_event("startup")
async def startup_event():
    """起動時処理"""
    print("OCR Analysis API starting up...")
    try:
        settings.validate()
        print("Configuration validated successfully")
    except Exception as e:
        print(f"Configuration error: {e}")
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )


