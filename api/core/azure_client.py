from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.core.credentials import AzureKeyCredential
from .config import settings


class AzureClientManager:
    """Azure Vision Clientのシングルトン管理"""
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self) -> ImageAnalysisClient:
        """Azure Vision Clientを取得（初回のみ作成）"""
        if self._client is None:
            settings.validate()
            self._client = ImageAnalysisClient(
                endpoint=settings.vision_endpoint,
                credential=AzureKeyCredential(settings.vision_key)
            )
        return self._client


azure_client_manager = AzureClientManager()
