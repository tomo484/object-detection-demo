import base64
import cv2
import numpy as np


def decode_base64_image(image_base64: str) -> bytes:
    """Base64画像をバイト列に変換"""
    
    # "data:image/jpeg;base64," プレフィックス除去
    if image_base64.startswith("data:image"):
        image_base64 = image_base64.split(",")[1]
    
    try:
        # Base64デコード
        image_bytes = base64.b64decode(image_base64)
    except Exception as e:
        raise ValueError(f"Invalid base64 format: {e}")
    
    # 画像サイズチェック（20MB制限）
    if len(image_bytes) > 20 * 1024 * 1024:
        raise ValueError("Image size exceeds 20MB limit")
    
    # 画像形式の基本検証
    if not validate_image_format(image_bytes):
        raise ValueError("Invalid image format")
    
    return image_bytes


def validate_image_format(image_bytes: bytes) -> bool:
    """画像形式の検証"""
    try:
        img_array = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return image is not None
    except:
        return False


