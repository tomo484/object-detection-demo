import time
from typing import Dict, Any
from azure.ai.vision.imageanalysis import ImageAnalysisClient

# 既存のOCR処理モジュールを活用
from scripts.ocr.single_image_ocr import analyze_single_image
from ..utils.image_processing import decode_base64_image
from ..models.response import MlApiResponse, MlApiResult, MlApiMetadata


class OCRService:
    
    def __init__(self, azure_client: ImageAnalysisClient):
        self.azure_client = azure_client
    
    def process_image(self, image_base64: str) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            image_bytes = decode_base64_image(image_base64)
            
            result, analysis = analyze_single_image(
                self.azure_client, 
                image_bytes, 
                use_preprocessing=True
            )
            
            processing_time = time.time() - start_time
            
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
            
        except ValueError as e:
            processing_time = time.time() - start_time
            return {
                "success": False,
                "error": {
                    "code": "INVALID_IMAGE",
                    "message": "画像の形式が不正です。再度写真を撮って、お試しください"
                },
                "processing_time": processing_time,
                "result": {
                    "text_normalized": "",
                    "preprocessing_attempts": 0
                },
                "metadata": {
                    "total_lines_detected": 0,
                    "numeric_candidates": 0
                }
            }
        except ConnectionError as e:
            processing_time = time.time() - start_time
            return {
                "success": False,
                "error": {
                    "code": "NETWORK_ERROR",
                    "message": "ネットワークエラーが発生しました。再度お試しください"
                },
                "processing_time": processing_time,
                "result": {
                    "text_normalized": "",
                    "preprocessing_attempts": 0
                },
                "metadata": {
                    "total_lines_detected": 0,
                    "numeric_candidates": 0
                }
            }
        except Exception as e:
            processing_time = time.time() - start_time
            error_code = "AZURE_API_ERROR" if "InvalidRequest" in str(e) or "InvalidImageSize" in str(e) else "OCR_FAILED"
            
            return {
                "success": False,
                "error": {
                    "code": error_code,
                    "message": "OCR読み取りができませんでした。再度写真を撮って、お試しください"
                },
                "processing_time": processing_time,
                "result": {
                    "text_normalized": "",
                    "preprocessing_attempts": 0
                },
                "metadata": {
                    "total_lines_detected": 0,
                    "numeric_candidates": 0
                }
            }
