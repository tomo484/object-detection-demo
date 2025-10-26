import time
from typing import Dict, Any
from azure.ai.vision.imageanalysis import ImageAnalysisClient

# 既存のOCR処理モジュールを活用
from scripts.ocr.single_image_ocr import analyze_single_image
from ..utils.image_processing import decode_base64_image
from ..models.response import MlApiResponse, MlApiResult, MlApiMetadata


class OCRService:
    """OCR処理サービス"""
    
    def __init__(self, azure_client: ImageAnalysisClient):
        self.azure_client = azure_client
    
    def process_image(self, image_base64: str) -> Dict[str, Any]:
        """画像のOCR処理を実行"""
        start_time = time.time()
        
        try:
            # Base64 → バイト列変換
            image_bytes = decode_base64_image(image_base64)
            
            # OCR処理（前処理エンジン使用）
            result, analysis = analyze_single_image(
                self.azure_client, 
                image_bytes, 
                use_preprocessing=True
            )
            
            processing_time = time.time() - start_time
            
            # 結果の整形
            numeric_results = analysis["numeric"]
            best_result = numeric_results[0]["normalized"] if numeric_results else ""
            
            return {
                "success": True,
                "result": {
                    "text_normalized": best_result,
                    "preprocessing_attempts": analysis["preprocessing"]["attempts"]
                },
                "processing_time": processing_time,
                "metadata": {
                    "total_lines_detected": len(result["lines"]),
                    "numeric_candidates": len(numeric_results)
                }
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            return {
                "success": False,
                "error": {
                    "code": "OCR_FAILED",
                    "message": str(e)
                },
                "processing_time": processing_time
            }
