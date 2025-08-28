# scripts/ocr/analyze_ocr_results.py
import os, json, argparse, pathlib
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
import re

# 前処理エンジンをインポート
from .preprocess import PreprocessingEngine

# run_ocr.pyと同じ改善された正規表現を使用
NUMERIC_RE = re.compile(r"^(?!.*[IO]/[IO])(?![IO]+$)(?![A-Z]+$)[0-9OIl:.,+\-_/\\()\s°C°F%℃]+$")

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

def reproduce_preprocessing(img_path: str, preprocessing_info: Dict[str, Any]) -> np.ndarray:
    """前処理情報を基に前処理を再実行"""
    if not preprocessing_info.get("used_preprocessing", False):
        return cv2.imread(img_path)
    
    image = cv2.imread(img_path)
    engine = PreprocessingEngine()
    
    def simple_ocr_callback(processed_img: np.ndarray) -> Tuple[bool, bool, List[Dict[str, Any]]]:
        # 簡易版：数値的な内容があるかの判定のみ
        return True, True, []  # 前処理成功条件を満たすまで継続
    
    return engine.process_image(image, simple_ocr_callback)

def draw_bounding_polygons(img_path: str, lines: List[Dict[str, Any]], numeric_lines: List[Dict[str, Any]], preprocessing_info: Dict[str, Any] = None) -> np.ndarray:
    """画像にbounding_polygonを描画して可視化"""
    # 前処理情報に基づいて適切な画像を取得
    if preprocessing_info and preprocessing_info.get("used_preprocessing", False):
        img = reproduce_preprocessing(img_path, preprocessing_info)
    else:
        img = cv2.imread(img_path)
        
    if img is None:
        print(f"Warning: Could not read image {img_path}")
        return None
    
    canvas = img.copy()
    
    # 全ての検出行を青色で描画
    for line in lines:
        if "bounding_polygon" in line:
            pts = np.array([[pt["x"], pt["y"]] for pt in line["bounding_polygon"]], np.int32)
            cv2.polylines(canvas, [pts], True, (255, 0, 0), 2)  # 青色
            # テキストを表示
            if pts.size > 0:
                cv2.putText(canvas, line["text"], (int(pts[0][0]), int(pts[0][1]) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    
    # 数値として認識された行を緑色で上描き
    for num_line in numeric_lines:
        if "bounding_polygon" in num_line:
            pts = np.array([[pt["x"], pt["y"]] for pt in num_line["bounding_polygon"]], np.int32)
            cv2.polylines(canvas, [pts], True, (0, 255, 0), 3)  # 緑色（太い）
            # 正規化後のテキストを表示
            if pts.size > 0:
                display_text = f"{num_line.get('normalized', num_line['text'])}"
                cv2.putText(canvas, display_text, (int(pts[0][0]), int(pts[0][1]) - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    return canvas

def analyze_ocr_results(lines: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """OCR結果の包括的分析：数値抽出と失敗段階分析"""
    extracted_numbers = []
    numeric_candidates = []
    regex_matches = []
    
    # 各行を分析・数値抽出
    for line in lines:
        text = line["text"].strip()
        
        # 数字を含む行をチェック
        if re.search(r'[0-9]', text):
            numeric_candidates.append(text)
        
        # 正規表現マッチで数値として抽出
        if NUMERIC_RE.fullmatch(text):
            # 賢い正規化を使用
            normalized = smart_normalize(text)
            extracted_numbers.append({**line, "normalized": normalized})
            regex_matches.append(text)
    
    # 失敗段階と理由を特定
    if not lines:
        failure_stage = "detection_failed"
        picked_because = "no_text_detected"
    elif not numeric_candidates:
        failure_stage = "no_numeric_content"
        picked_because = "no_digits_found"
    elif not regex_matches:
        failure_stage = "regex_too_strict"
        picked_because = "regex_filter_blocked"
    else:
        failure_stage = "success"
        picked_because = "regex_match"
    
    analysis = {
        "failure_stage": failure_stage,
        "picked_because": picked_because,
        "total_lines": len(lines),
        "numeric_candidates": numeric_candidates,
        "regex_matches": regex_matches
    }
    
    return extracted_numbers, analysis

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True, help="OCR結果ディレクトリ（例: runs/ocr/20250816-160044）")
    ap.add_argument("--output-dir", default=None, help="分析結果出力先（未指定なら results-dir/analysis）")
    ap.add_argument("--test-regex", help="代替正規表現パターンをテスト")
    args = ap.parse_args()
    
    # 代替正規表現のテスト
    global NUMERIC_RE
    if args.test_regex:
        print(f"正規表現を変更: {args.test_regex}")
        NUMERIC_RE = re.compile(args.test_regex)
    
    results_dir = pathlib.Path(args.results_dir)
    output_dir = pathlib.Path(args.output_dir or results_dir / "analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 結果ファイルの読み込み
    jsonl_path = results_dir / "results.jsonl"
    if not jsonl_path.exists():
        raise FileNotFoundError(f"results.jsonl not found in {results_dir}")
    
    analysis_summary = []
    viz_dir = output_dir / "visualizations"
    viz_dir.mkdir(exist_ok=True)
    
    print("OCR結果を分析中...")
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            data = json.loads(line.strip())
            img_path = data["image"]
            all_lines = data["all_lines"]
            preprocessing_info = data.get("preprocessing", {})
            
            # 統一された分析関数で包括的分析を実行
            extracted_numbers, analysis = analyze_ocr_results(all_lines)
            
            # 画像可視化（前処理情報を使用）
            img_name = pathlib.Path(img_path).stem
            canvas = draw_bounding_polygons(img_path, all_lines, extracted_numbers, preprocessing_info)
            
            if canvas is not None:
                # 分析結果をテキストで画像に追加
                status_text = f"Stage: {analysis['failure_stage']}"
                lines_text = f"Lines: {analysis['total_lines']}"
                numeric_text = f"Numeric: {len(analysis['numeric_candidates'])}"
                
                cv2.putText(canvas, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(canvas, lines_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(canvas, numeric_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 保存
                output_path = viz_dir / f"{img_name}_analysis.jpg"
                cv2.imwrite(str(output_path), canvas)
            
            # サマリーに追加
            summary_item = {
                "image": img_path,
                "image_name": img_name,
                "failure_stage": analysis["failure_stage"],
                "total_lines": analysis["total_lines"],
                "numeric_candidates": analysis["numeric_candidates"],
                "regex_matches": analysis["regex_matches"],
                "picked_because": analysis["picked_because"],
                "best_result": extracted_numbers[0]["normalized"] if extracted_numbers else "",
                "success": len(extracted_numbers) > 0
            }
            
            analysis_summary.append(summary_item)
    
    # 失敗段階デバッグ用の統計のみ計算
    total_images = len(analysis_summary)
    success_count = sum(1 for item in analysis_summary if item["success"])
    
    failure_stages = {}
    picked_reasons = {}
    for item in analysis_summary:
        stage = item["failure_stage"]
        reason = item["picked_because"]
        failure_stages[stage] = failure_stages.get(stage, 0) + 1
        picked_reasons[reason] = picked_reasons.get(reason, 0) + 1
    
    summary_stats = {
        "total_images": total_images,
        "success_count": success_count,
        "success_rate": success_count / total_images if total_images > 0 else 0,
        "failure_stages": failure_stages,
        "picked_reasons": picked_reasons,
        "regex_pattern": NUMERIC_RE.pattern,
        "detailed_results": analysis_summary
    }
    
    # 結果保存
    with open(output_dir / "analysis_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_stats, f, ensure_ascii=False, indent=2)
    
    # 失敗例のレポート
    failed_items = [item for item in analysis_summary if not item["success"]]
    with open(output_dir / "failed_cases.json", "w", encoding="utf-8") as f:
        json.dump(failed_items, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 分析結果 ===")
    print(f"総画像数: {total_images}")
    print(f"成功数: {success_count} ({success_count/total_images*100:.1f}%)")
    
    print(f"\n使用正規表現: {NUMERIC_RE.pattern}")
    
    print(f"\n失敗段階別:")
    for stage, count in failure_stages.items():
        print(f"  {stage}: {count}枚")
    
    print(f"\n選択理由別:")
    for reason, count in picked_reasons.items():
        print(f"  {reason}: {count}枚")
    
    print(f"\n可視化結果: {viz_dir}")
    print(f"詳細分析: {output_dir / 'analysis_summary.json'}")
    print(f"失敗例: {output_dir / 'failed_cases.json'}")

if __name__ == "__main__":
    main() 