from azure.ai.vision.imageanalysis import ImageAnalysisClient
from .core.azure_client import azure_client_manager


def get_azure_client() -> ImageAnalysisClient:
    """Azure Vision Clientを取得"""
    return azure_client_manager.get_client()
