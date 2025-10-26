import os
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()


class Settings:
    # Azure Vision API設定
    vision_endpoint: str = os.getenv("VISION_ENDPOINT", "")
    vision_key: str = os.getenv("VISION_KEY", "")
    
    # API設定
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    def validate(self):
        """設定の検証"""
        if not self.vision_endpoint:
            raise ValueError("VISION_ENDPOINT is not set")
        if not self.vision_key:
            raise ValueError("VISION_KEY is not set")


# グローバル設定インスタンス
settings = Settings()
