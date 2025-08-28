# scripts/ocr/preprocess/operations.py
import cv2
import numpy as np

class PreprocessingOperations:
    def __init__(self):
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        self.clahe_strong = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
    
    def apply_preset(self, image: np.ndarray, preset: str, scale: float = 1.0):
        """プリセット適用"""
        # スケーリング
        if scale != 1.0:
            processed = self._scale(image, scale)
        else:
            processed = image.copy()
        
        # プリセット適用
        if preset == "invert":
            return self._invert(processed)
        elif preset == "clahe":
            return self._clahe(processed)
        elif preset == "closing":
            return self._closing(processed)
        elif preset == "lcd_strong":
            return self._lcd_strong(processed)
        elif preset == "decimal_enhance":
            return self._decimal_enhance(processed)
        else:  # as-is
            return processed
    
    def extract_horizontal_rois(self, image: np.ndarray, k: int = 3):
        """横長ROI検出・抽出（パラメータ調整済み）"""
        # 前処理: invert + 適応二値化
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        inverted = cv2.bitwise_not(gray)
        binary = cv2.adaptiveThreshold(inverted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # morphology: open → closing
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 2))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        
        # 輪郭検出・矩形抽出
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rects = [cv2.boundingRect(c) for c in contours]
        
        # フィルタ: アスペクト比・面積（緩和済み）
        filtered_rects = []
        h, w = image.shape[:2]
        for x, y, rect_w, rect_h in rects:
            aspect_ratio = rect_w / rect_h if rect_h > 0 else 0
            area = rect_w * rect_h
            # アスペクト比緩和: 2.0 → 1.5, 最小面積削減: 0.01 → 0.005
            if aspect_ratio > 1.5 and area > (w * h * 0.005):
                filtered_rects.append((x, y, rect_w, rect_h))
        
        # NMS: 重複除去
        nms_rects = self._nms_rects(filtered_rects, 0.3)
        
        # 上位K個選択（面積順）
        sorted_rects = sorted(nms_rects, key=lambda r: r[2] * r[3], reverse=True)
        return sorted_rects[:k]
    
    def crop_roi(self, image: np.ndarray, roi_coords):
        """ROI切り出し"""
        x, y, w, h = roi_coords
        return image[y:y+h, x:x+w]
    
    def _lcd_strong(self, image):
        """液晶ディスプレイ特化の強力な前処理"""
        # グレースケール変換
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 1. ガンマ補正で暗部を明るく（暗い液晶文字を強調）
        gamma = 0.4
        gamma_table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype("uint8")
        enhanced = cv2.LUT(gray, gamma_table)
        
        # 2. 強化CLAHE（コントラスト大幅向上）
        clahe_result = self.clahe_strong.apply(enhanced)
        
        # 3. アンシャープマスク（エッジ強調）
        gaussian = cv2.GaussianBlur(clahe_result, (0, 0), 2.0)
        unsharp = cv2.addWeighted(clahe_result, 2.0, gaussian, -1.0, 0)
        
        # 4. 適応二値化で最終調整
        binary = cv2.adaptiveThreshold(unsharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 7, 2)
        
        # カラー画像として返す（OCRエンジンの要求に合わせて）
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    
    def _nms_rects(self, rects, overlap_thresh):
        """矩形のNMS"""
        if not rects:
            return []
        
        rects = np.array(rects, dtype=np.float32)
        x1, y1 = rects[:, 0], rects[:, 1]
        x2, y2 = x1 + rects[:, 2], y1 + rects[:, 3]
        areas = rects[:, 2] * rects[:, 3]
        indices = np.argsort(areas)
        
        keep = []
        while len(indices) > 0:
            last = len(indices) - 1
            i = indices[last]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[indices[:last]])
            yy1 = np.maximum(y1[i], y1[indices[:last]])
            xx2 = np.minimum(x2[i], x2[indices[:last]])
            yy2 = np.minimum(y2[i], y2[indices[:last]])
            
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            overlap = (w * h) / areas[indices[:last]]
            
            indices = np.delete(indices, np.concatenate(([last], np.where(overlap > overlap_thresh)[0])))
        
        return [tuple(map(int, rects[i])) for i in keep]
    
    def _scale(self, image, factor):
        h, w = image.shape[:2]
        new_size = (int(w * factor), int(h * factor))
        interp = cv2.INTER_AREA if factor < 1.0 else cv2.INTER_CUBIC
        return cv2.resize(image, new_size, interpolation=interp)
    
    def _invert(self, image):
        return cv2.bitwise_not(image)
    
    def _clahe(self, image):
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = self.clahe.apply(l)
            return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        return self.clahe.apply(image)
    
    def _closing(self, image):
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 2))
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            return cv2.cvtColor(closed, cv2.COLOR_GRAY2BGR)
        return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
    
    def _decimal_enhance(self, image):
        """小数点検出特化の前処理"""
        # グレースケール変換
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 1. 強い拡大（小数点を大きく）
        enlarged = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        
        # 2. ガウシアンブラーで滑らか化
        blurred = cv2.GaussianBlur(enlarged, (3, 3), 0.5)
        
        # 3. 穏やかなCLAHE（小数点を潰さない）
        clahe_mild = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe_mild.apply(blurred)
        
        # 4. アンシャープマスク（エッジ強調）
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
        unsharp = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
        
        # カラー画像として返す
        return cv2.cvtColor(unsharp, cv2.COLOR_GRAY2BGR)