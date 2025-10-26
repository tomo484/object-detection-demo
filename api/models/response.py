from pydantic import BaseModel
from typing import Optional


class MlApiResult(BaseModel):
    text_normalized: str
    preprocessing_attempts: int


class MlApiMetadata(BaseModel):
    total_lines_detected: int
    numeric_candidates: int


class MlApiResponse(BaseModel):
    success: bool
    result: MlApiResult
    processing_time: float
    metadata: MlApiMetadata


class ApiError(BaseModel):
    code: str
    message: str


class MlApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiError
