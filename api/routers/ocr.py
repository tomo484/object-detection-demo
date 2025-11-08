from fastapi import APIRouter, Depends, HTTPException
from azure.ai.vision.imageanalysis import ImageAnalysisClient

from ..models.request import MlApiRequest
from ..models.response import MlApiResponse, MlApiErrorResponse
from ..services.ocr_service import OCRService
from ..dependencies import get_azure_client


router = APIRouter()


def get_ocr_service(azure_client: ImageAnalysisClient = Depends(get_azure_client)) -> OCRService:
    return OCRService(azure_client)


@router.post("/ocr/analyze", response_model=MlApiResponse)
async def analyze_ocr(
    request: MlApiRequest,
    ocr_service: OCRService = Depends(get_ocr_service)
):
    result = ocr_service.process_image(request.image_base64)
    return result

