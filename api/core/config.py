import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    vision_endpoint: str = os.getenv("VISION_ENDPOINT", "")
    vision_key: str = os.getenv("VISION_KEY", "")
    
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    def validate(self):
        if not self.vision_endpoint:
            raise ValueError("VISION_ENDPOINT is not set")
        if not self.vision_key:
            raise ValueError("VISION_KEY is not set")


settings = Settings()
