# scripts/ocr/single_image_ocr.py
import re
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures

# 既存のpreprocessモジュールをインポート
from .preprocess import PreprocessingEngine

# 既存の正規表現を再利用
NUMERIC_RE = re.compile(r"^(?!.*[IO]/[IO])(?![IO]+$)(?![A-Z]+$)[0-9OIl:.,+\-_/\\()\s°C°F%]+$")


def analyze_image_bytes(client: ImageAnalysisClient, img_bytes: bytes) -> Dict[str, Any]:
    """既存のanalyze_image_bytes関数をそのまま使用"""
    # 画像サイズが20MB超過時はリサイズ
    if len(img_bytes) > 20 * 1024 * 1024:
        img_array = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        h, w = image.shape[:2]
        new_size = (int(w * 0.7), int(h * 0.7))
        resized = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
        _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_bytes = buffer.tobytes()
    
    result = client.analyze(image_data=img_bytes, visual_features=[VisualFeatures.READ])
    lines = []
    if result.read:
        for block in result.read.blocks:
            for line in block.lines:
                # ImagePointオブジェクトを辞書形式に変換してJSONシリアライズ可能にする
                bounding_polygon = [{"x": pt.x, "y": pt.y} for pt in line.bounding_polygon]
                words = []
                for w in line.words:
                    word_bp = [{"x": pt.x, "y": pt.y} for pt in w.bounding_polygon]
                    words.append({
                        "text": w.text, 
                        "confidence": getattr(w, "confidence", None), 
                        "bounding_polygon": word_bp
                    })
                
                lines.append({
                    "text": line.text,
                    "bounding_polygon": bounding_polygon,
                    "words": words
                })
    return {"lines": lines}


def smart_normalize(text: str) -> str:
    """既存のsmart_normalize関数をそのまま使用"""
    import re
    
    # 明らかに非数値なパターンはそのまま返す
    non_numeric = ['I/O', 'O/I', 'ON', 'OFF', 'IO', 'OI']
    if text.upper() in non_numeric:
        return text
    
    # 時刻表示の前処理クリーンアップ
    cleaned = text
    
    # 先頭の不要文字を除去
    cleaned = re.sub(r'^[.\-\s]+', '', cleaned)
    
    # 時刻パターンの間のスペースを除去
    cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', cleaned)  # "1 1:38" → "11:38"
    cleaned = re.sub(r'(\d)\s+:', r'\1:', cleaned)      # "1 :" → "1:"
    cleaned = re.sub(r':\s+(\d)', r':\1', cleaned)      # ": 38" → ":38"
    
    # 数字がある場合のみ文字置換
    if re.search(r'\d', cleaned):
        cleaned = cleaned.replace("O", "0").replace("I", "1").replace("l", "1")
    
    return cleaned


def pick_numeric(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """既存のpick_numeric関数をそのまま使用"""
    out = []
    for ln in lines:
        text = ln["text"].strip()
        if NUMERIC_RE.fullmatch(text):
            normalized = smart_normalize(text)
            out.append({**ln, "normalized": normalized})
    return out


def check_ocr_success(lines: List[Dict[str, Any]]) -> Tuple[bool, bool, List[Dict[str, Any]]]:
    """既存のcheck_ocr_success関数をそのまま使用"""
    found_any_line = len(lines) > 0
    numeric_results = pick_numeric(lines)
    found_numeric_like = len(numeric_results) > 0
    return found_any_line, found_numeric_like, numeric_results


def analyze_single_image(client: ImageAnalysisClient, img_bytes: bytes, use_preprocessing: bool = True) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """単一画像のOCR処理（バイト列版）"""
    
    if not use_preprocessing:
        # 前処理なしの場合
        res = analyze_image_bytes(client, img_bytes)
        nums = pick_numeric(res["lines"])
        preprocessing_log = {"used_preprocessing": False, "attempts": 1}
        return res, {"numeric": nums, "preprocessing": preprocessing_log}
    
    # 前処理エンジンを使用
    image = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image data")
    
    engine = PreprocessingEngine()
    
    def ocr_callback(processed_img: np.ndarray) -> Tuple[bool, bool, List[Dict[str, Any]]]:
        """前処理された画像に対するOCRコールバック"""
        if processed_img is None or processed_img.size == 0:
            return False, False, []
        
        _, buffer = cv2.imencode('.jpg', processed_img)
        processed_bytes = buffer.tobytes()
        res = analyze_image_bytes(client, processed_bytes)
        return check_ocr_success(res["lines"])
    
    # 段階的前処理実行
    final_image = engine.process_image(image, ocr_callback)
    
    # 最終結果のOCR
    _, buffer = cv2.imencode('.jpg', final_image)
    final_bytes = buffer.tobytes()
    final_res = analyze_image_bytes(client, final_bytes)
    final_nums = pick_numeric(final_res["lines"])
    
    preprocessing_log = {
        "used_preprocessing": True,
        "attempts": engine.attempt_count,
        "final_stage": f"attempt_{engine.attempt_count}"
    }
    
    return final_res, {"numeric": final_nums, "preprocessing": preprocessing_log}


