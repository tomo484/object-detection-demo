# scripts/ocr/preprocess/engine.py
import cv2
import numpy as np
import re
from .operations import PreprocessingOperations

class PreprocessingEngine:
    def __init__(self):
        self.ops = PreprocessingOperations()
        self.attempt_count = 0
    
    def process_image(self, image: np.ndarray, ocr_callback):
        """段階的前処理実行"""
        self.attempt_count = 0
        
        # S0: 素通し
        if self._try_ocr(image, ocr_callback, "S0-original"):
            return image
        
        # S1: 最小プリセット（液晶特化・小数点特化を追加）
        for preset in ["invert", "clahe", "lcd_strong", "decimal_enhance"]:
            processed = self.ops.apply_preset(image, preset)
            if self._try_ocr(processed, ocr_callback, f"S1-{preset}"):
                return processed
        
        # S2: スケール×プリセット（closing-1.5を最優先）
        scales = [0.75, 0.5, 1.5, 2.0]
        
        # 最優先: closing-1.5
        processed = self.ops.apply_preset(image, "closing", 1.5)
        if self._try_ocr(processed, ocr_callback, "S2-closing-1.5"):
            return processed
        
        # 残りの組み合わせ
        for scale in scales:
            presets = ["invert", "clahe", "closing"]
            if scale <= 1.0:  # 縮小時のみas-is追加
                presets.append("as-is")
                
            for preset in presets:
                # closing-1.5は既に試行済みなのでスキップ
                if preset == "closing" and scale == 1.5:
                    continue
                    
                processed = self.ops.apply_preset(image, preset, scale)
                if self._try_ocr(processed, ocr_callback, f"S2-{preset}-{scale}"):
                    return processed
        
        # S3: ROIフォールバック（最後の救済手段）
        rois = self.ops.extract_horizontal_rois(image, k=3)
        for roi_idx, roi_coords in enumerate(rois):
            roi_image = self.ops.crop_roi(image, roi_coords)
            
            # ROIが小さすぎる場合はスキップ
            if roi_image.shape[0] < 20 or roi_image.shape[1] < 50:
                continue
                
            # S2と同じスケール×プリセット順序
            for scale in scales:
                presets = ["invert", "clahe", "closing"]
                if scale <= 1.0:
                    presets.append("as-is")
                    
                for preset in presets:
                    processed = self.ops.apply_preset(roi_image, preset, scale)
                    if self._try_ocr(processed, ocr_callback, f"S3-roi{roi_idx}-{preset}-{scale}"):
                        return processed
        
        return image  # 全て失敗
    
    def _is_valid_numeric(self, numeric_results):
        """シンプルな数値妥当性判定"""
        if not numeric_results:
            return False
        
        text = numeric_results[0]["normalized"].strip()
        
        # 最小長チェック
        if len(text.replace(" ", "")) < 2:
            return False
        
        # 除外パターン（問題のあるもの）
        exclude_patterns = [
            r'^\.',                         # .11:34
            r'^0:\d{2}$',                  # 0:03  
            r'^\d{1,2}\.\d{3,}$',          # 10.004, 10.0045 (小数点以下3桁以上)
            r'^\d+\.\s+\d+$',              # 10. 0045 (スペース入り小数)
            r'^0{3,}$',                    # 000
            r'^\d{1}[°℃°F%]$',            # 7℃
            r'^[°℃°FC%]+$',                # C, ℃のみ
            r'^\([IO]/[IO]\)$',            # (I/O), (O/I)
        ]
        
        if any(re.match(p, text) for p in exclude_patterns):
            return False
        
        # 数字が2桁以上あれば基本的にOK
        digit_count = sum(1 for c in text if c.isdigit())
        return digit_count >= 2
    
    def _try_ocr(self, image, ocr_callback, stage_name):
        """OCR試行と厳格な早期終了判定"""
        self.attempt_count += 1
        found_any_line, found_numeric_like, numeric_results = ocr_callback(image)
        
        print(f"Attempt {self.attempt_count} ({stage_name}): "
              f"line={found_any_line}, numeric={found_numeric_like}")
        
        # 厳格な終了条件
        if found_any_line and found_numeric_like:
            # さらに数値の妥当性をチェック
            valid_numeric = self._is_valid_numeric(numeric_results)
            if valid_numeric:
                print(f"  → Valid numeric found: {numeric_results[0]['normalized']}")
                return True
            else:
                print(f"  → Invalid numeric rejected: {numeric_results[0]['normalized'] if numeric_results else 'None'}")
        
        return False