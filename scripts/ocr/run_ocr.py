# scripts/ocr/run_ocr.py
import os, re, json, argparse, pathlib, datetime
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from tqdm import tqdm
import cv2
import numpy as np
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

# 新しく追加されたpreprocessモジュールをインポート
from .preprocess import PreprocessingEngine, PreprocessingLogger

NUMERIC_RE = re.compile(r"^(?!.*[IO]/[IO])(?![IO]+$)(?![A-Z]+$)[0-9OIl:.,+\-_/\\()\s°C°F%]+$")

def make_client():
    load_dotenv()  # reads .env at repo root
    endpoint = os.environ.get("VISION_ENDPOINT")
    key = os.environ.get("VISION_KEY")
    if not endpoint or not key:
        raise RuntimeError("VISION_ENDPOINT / VISION_KEY が未設定です（.env を確認）")
    return ImageAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

def analyze_image_bytes(client: ImageAnalysisClient, img_bytes: bytes) -> Dict[str, Any]:
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

def pick_numeric(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for ln in lines:
        text = ln["text"].strip()
        if NUMERIC_RE.fullmatch(text):
            # 賢い正規化: 文脈を考慮した文字置換
            normalized = smart_normalize(text)
            out.append({**ln, "normalized": normalized})
    return out

def smart_normalize(text: str) -> str:
    """シンプルな賢い正規化"""
    import re
    
    # 明らかに非数値なパターンはそのまま返す
    non_numeric = ['I/O', 'O/I', 'ON', 'OFF', 'IO', 'OI']
    if text.upper() in non_numeric:
        return text
    
    # 時刻表示の前処理クリーンアップ
    # ". 1 1:38" → "11:38" のような変換
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

# 新しく追加: OCR試行と早期終了判定のためのヘルパー関数
def check_ocr_success(lines: List[Dict[str, Any]]) -> Tuple[bool, bool, List[Dict[str, Any]]]:
    """OCR結果の成功判定を行う"""
    found_any_line = len(lines) > 0
    numeric_results = pick_numeric(lines)
    found_numeric_like = len(numeric_results) > 0
    return found_any_line, found_numeric_like, numeric_results

# 新しく追加: 前処理付きOCR処理関数
def analyze_with_preprocessing(client: ImageAnalysisClient, image_path: pathlib.Path, use_preprocessing: bool = True) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """前処理エンジンを使用したOCR処理"""
    img_bytes = image_path.read_bytes()
    
    if not use_preprocessing:
        # 従来の処理
        res = analyze_image_bytes(client, img_bytes)
        nums = pick_numeric(res["lines"])
        preprocessing_log = {"used_preprocessing": False, "attempts": 1}
        return res, {"numeric": nums, "preprocessing": preprocessing_log}
    
    # 前処理エンジンを使用
    image = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    engine = PreprocessingEngine()
    logger = PreprocessingLogger()
    
    def ocr_callback(processed_img: np.ndarray) -> Tuple[bool, bool, List[Dict[str, Any]]]:
        """前処理された画像に対するOCRコールバック"""
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="data_ocr/images/*.*", help="入力画像のglobパターン")
    ap.add_argument("--outdir", default=None, help="出力先（未指定なら runs/ocr/<timestamp>)")
    # 新しく追加: 前処理機能のオン/オフ切り替え
    ap.add_argument("--no-preprocessing", action="store_true", help="前処理を無効にする（従来の処理のみ）")
    args = ap.parse_args()

    client = make_client()
    paths = [p for p in map(pathlib.Path, sorted(pathlib.Path().glob(args.glob)))]
    if not paths:
        raise SystemExit(f"no files for pattern: {args.glob}")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = pathlib.Path(args.outdir or f"runs/ocr/{ts}")
    outdir.mkdir(parents=True, exist_ok=True)
    jsonl = open(outdir/"results.jsonl", "w", encoding="utf-8")
    tsv   = open(outdir/"numeric_lines.tsv", "w", encoding="utf-8")
    tsv.write("image\ttext_normalized\ttext_raw\tpreprocessing_attempts\n")

    use_preprocessing = not args.no_preprocessing
    print(f"前処理モード: {'有効' if use_preprocessing else '無効'}")

    for p in tqdm(paths, desc="OCR"):
        # 新しい統合処理を使用
        res, analysis = analyze_with_preprocessing(client, p, use_preprocessing)
        nums = analysis["numeric"]
        preprocessing_info = analysis["preprocessing"]
        
        best = nums[0]["normalized"] if nums else ""
        attempts = preprocessing_info.get("attempts", 1)
        tsv.write(f"{p}\t{best}\t{(nums[0]['text'] if nums else '')}\t{attempts}\n")
        
        # JSONLに前処理情報も含める
        jsonl_data = {
            "image": str(p), 
            "all_lines": res["lines"], 
            "numeric": nums,
            "preprocessing": preprocessing_info
        }
        jsonl.write(json.dumps(jsonl_data, ensure_ascii=False) + "\n")
        
        # 詳細ファイルも更新
        pretty_dir = outdir / "details"
        pretty_dir.mkdir(exist_ok=True)
        pretty_path = pretty_dir / (p.stem + ".json")
        with open(pretty_path, "w", encoding="utf-8") as fp:
            json.dump(jsonl_data, fp, ensure_ascii=False, indent=2)

    jsonl.close(); tsv.close()
    print(f"done: {outdir}")

if __name__ == "__main__":
    main()
