from pydantic import BaseModel, validator


class MlApiRequest(BaseModel):
    image_base64: str
    
    @validator('image_base64')
    def validate_base64(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('image_base64 must be a non-empty string')
        
        # Base64形式の基本チェック
        if not v.startswith('data:image/'):
            raise ValueError('image_base64 must start with data:image/')
        
        return v
