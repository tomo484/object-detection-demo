# OCRシステム詳細ガイド

## 📋 概要

本OCRシステムは、**Azure Computer Vision APIと独自の段階的前処理エンジンを組み合わせた高精度な数値認識システム**です。アナログメーターのデジタル表示部分から数値を抽出し、正規化・分析することで、メーター読み取りの自動化を実現しています。

### 🎯 システムの特徴
- **段階的前処理**: 3段階（S0→S1→S2→S3）の適応的前処理
- **早期終了機能**: 成功時の効率的な処理停止
- **液晶表示特化**: LCD/LED表示に最適化された前処理プリセット
- **ROIフォールバック**: 全体処理失敗時の領域別処理
- **スマート正規化**: 文脈を考慮した文字置換・正規化

### 📊 現在の性能
- **OCR成功率**: 76.9%（26枚中20枚成功）
- **前処理効果**: 段階的処理により品質向上
- **処理効率**: 早期終了により平均試行回数を削減

## 🔧 システム構成

### 📁 ファイル構造
```
scripts/ocr/
├── run_ocr.py              # メイン実行スクリプト
├── analyze_ocr_results.py  # 結果分析・可視化
└── preprocess/             # 前処理エンジン
    ├── __init__.py         # モジュール初期化
    ├── engine.py          # 段階的前処理エンジン
    ├── operations.py      # 画像処理操作
    └── logger.py          # ログ管理
```

### 🧩 主要コンポーネント

#### 1. PreprocessingEngine (`engine.py`)
段階的前処理の制御を行うメインエンジン

**主要メソッド**:
- `process_image()`: 3段階の前処理実行
- `_try_ocr()`: OCR試行と早期終了判定
- `_is_valid_numeric()`: 数値妥当性の厳格チェック

**処理ステージ**:
- **S0**: 素通し（元画像でのOCR）
- **S1**: 基本プリセット適用
- **S2**: スケーリング×プリセット組み合わせ
- **S3**: ROI抽出によるフォールバック処理

#### 2. PreprocessingOperations (`operations.py`)
画像前処理操作の実装

**プリセット一覧**:
- `invert`: 色反転処理
- `clahe`: 適応ヒストグラム均等化
- `closing`: モルフォロジークロージング
- `lcd_strong`: 液晶表示特化の強力な前処理
- `decimal_enhance`: 小数点検出特化処理
- `as-is`: 無変換（スケーリングのみ）

**ROI機能**:
- `extract_horizontal_rois()`: 横長領域の自動抽出
- `crop_roi()`: 領域切り出し
- NMS（Non-Maximum Suppression）による重複除去

#### 3. PreprocessingLogger (`logger.py`)
試行結果のログ管理とサマリー生成

## 🎮 使用方法

### 1. OCR実行 (`run_ocr.py`)

#### 基本実行
```bash
# デフォルト設定でOCR実行
python scripts/ocr/run_ocr.py

# 特定パターンの画像を指定
python scripts/ocr/run_ocr.py --glob "data_ocr/images/*.jpg"

# 出力先を指定
python scripts/ocr/run_ocr.py --outdir "runs/ocr/my_experiment"
```

#### 前処理制御
```bash
# 前処理を無効化（従来処理のみ）
python scripts/ocr/run_ocr.py --no-preprocessing

# 前処理有効（デフォルト）
python scripts/ocr/run_ocr.py
```

#### 出力ファイル
- `results.jsonl`: 全結果の詳細データ（JSONL形式）
- `numeric_lines.tsv`: 数値抽出結果（TSV形式）
- `details/`: 各画像の詳細JSON（可読性重視）

### 2. 結果分析 (`analyze_ocr_results.py`)

#### 基本分析
```bash
# 標準分析実行
python scripts/ocr/analyze_ocr_results.py --results-dir runs/ocr/20250116-160044

# 出力先を指定
python scripts/ocr/analyze_ocr_results.py --results-dir runs/ocr/latest --output-dir analysis_custom
```

#### 正規表現テスト
```bash
# 代替正規表現パターンをテスト
python scripts/ocr/analyze_ocr_results.py --results-dir runs/ocr/latest --test-regex "^[0-9.,\s]+$"
```

#### 分析結果ファイル
- `analysis_summary.json`: 包括的分析結果
- `failed_cases.json`: 失敗事例の詳細
- `visualizations/`: 可視化画像（bounding box付き）

## 🔬 前処理エンジンの詳細

### 段階的処理フロー

#### S0: 原画像処理
```python
# 素通し試行
if self._try_ocr(image, ocr_callback, "S0-original"):
    return image
```

#### S1: 基本プリセット
```python
# 最小プリセット適用
presets = ["invert", "clahe", "lcd_strong", "decimal_enhance"]
for preset in presets:
    processed = self.ops.apply_preset(image, preset)
    if self._try_ocr(processed, ocr_callback, f"S1-{preset}"):
        return processed
```

#### S2: スケール×プリセット
```python
# 最優先: closing-1.5
processed = self.ops.apply_preset(image, "closing", 1.5)
if self._try_ocr(processed, ocr_callback, "S2-closing-1.5"):
    return processed

# スケール×プリセット組み合わせ
scales = [0.75, 0.5, 1.5, 2.0]
presets = ["invert", "clahe", "closing", "as-is"]
```

#### S3: ROIフォールバック
```python
# 横長ROI抽出
rois = self.ops.extract_horizontal_rois(image, k=3)
for roi_idx, roi_coords in enumerate(rois):
    roi_image = self.ops.crop_roi(image, roi_coords)
    # S2と同じ処理をROIに適用
```

### プリセット詳細

#### `lcd_strong`: 液晶表示特化
```python
def _lcd_strong(self, image):
    # 1. ガンマ補正（暗部強調）
    gamma = 0.4
    # 2. 強化CLAHE
    clahe_result = self.clahe_strong.apply(enhanced)
    # 3. アンシャープマスク
    unsharp = cv2.addWeighted(clahe_result, 2.0, gaussian, -1.0, 0)
    # 4. 適応二値化
    binary = cv2.adaptiveThreshold(unsharp, 255, ...)
```

#### `decimal_enhance`: 小数点特化
```python
def _decimal_enhance(self, image):
    # 1. 強い拡大（2.5倍）
    enlarged = cv2.resize(gray, None, fx=2.5, fy=2.5)
    # 2. ガウシアンブラー
    blurred = cv2.GaussianBlur(enlarged, (3, 3), 0.5)
    # 3. 穏やかなCLAHE
    enhanced = clahe_mild.apply(blurred)
    # 4. アンシャープマスク
```

### 早期終了判定

#### 成功条件
```python
def _is_valid_numeric(self, numeric_results):
    # 最小長チェック
    if len(text.replace(" ", "")) < 2:
        return False
    
    # 除外パターン
    exclude_patterns = [
        r'^\.',                    # .11:34
        r'^0:\d{2}$',             # 0:03  
        r'^\d{1,2}\.\d{3,}$',     # 10.004 (小数点以下3桁以上)
        r'^0{3,}$',               # 000
        # ... その他
    ]
    
    # 数字が2桁以上あれば基本的にOK
    digit_count = sum(1 for c in text if c.isdigit())
    return digit_count >= 2
```

## 📈 スマート正規化

### 正規化ロジック
```python
def smart_normalize(text: str) -> str:
    # 1. 非数値パターンの保護
    non_numeric = ['I/O', 'O/I', 'ON', 'OFF', 'IO', 'OI']
    if text.upper() in non_numeric:
        return text
    
    # 2. 時刻表示のクリーンアップ
    cleaned = re.sub(r'^[.\-\s]+', '', text)           # 先頭不要文字除去
    cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', cleaned) # "1 1:38" → "11:38"
    cleaned = re.sub(r'(\d)\s+:', r'\1:', cleaned)     # "1 :" → "1:"
    cleaned = re.sub(r':\s+(\d)', r':\1', cleaned)     # ": 38" → ":38"
    
    # 3. 文字置換（数字がある場合のみ）
    if re.search(r'\d', cleaned):
        cleaned = cleaned.replace("O", "0").replace("I", "1").replace("l", "1")
    
    return cleaned
```

### 正規表現フィルター
```python
NUMERIC_RE = re.compile(r"^(?!.*[IO]/[IO])(?![IO]+$)(?![A-Z]+$)[0-9OIl:.,+\-_/\\()\s°C°F%]+$")
```

**パターン説明**:
- `(?!.*[IO]/[IO])`: I/OやO/Iパターンを除外
- `(?![IO]+$)`: IやOのみの文字列を除外
- `(?![A-Z]+$)`: 大文字のみの文字列を除外
- `[0-9OIl:.,+\-_/\\()\s°C°F%]+`: 許可文字セット

## 🔍 結果分析機能

### 失敗段階分類
```python
def analyze_ocr_results(lines):
    if not lines:
        failure_stage = "detection_failed"      # OCR検出失敗
    elif not numeric_candidates:
        failure_stage = "no_numeric_content"    # 数字を含む行なし
    elif not regex_matches:
        failure_stage = "regex_too_strict"      # 正規表現フィルター阻止
    else:
        failure_stage = "success"               # 成功
```

### 可視化機能
- **青色**: 全検出行（bounding polygon）
- **緑色**: 数値として抽出された行（太線）
- **テキスト表示**: 正規化後の数値
- **統計情報**: Stage、Lines、Numeric の表示

### 出力レポート
```json
{
  "total_images": 26,
  "success_count": 20,
  "success_rate": 0.769,
  "failure_stages": {
    "detection_failed": 2,
    "no_numeric_content": 1,
    "regex_too_strict": 3,
    "success": 20
  },
  "regex_pattern": "^(?!.*[IO]/[IO])...",
  "detailed_results": [...]
}
```

## ⚙️ 設定・カスタマイズ

### 環境変数設定
```env
# .env ファイル
VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
VISION_KEY=your-azure-vision-api-key
```

### 前処理パラメータ調整
```python
# engine.py
scales = [0.75, 0.5, 1.5, 2.0]              # スケール設定
presets = ["invert", "clahe", "closing"]      # プリセット順序

# operations.py
self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))      # CLAHE設定
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 2))           # closing設定
```

### ROI抽出パラメータ
```python
# 横長ROI抽出の調整
def extract_horizontal_rois(self, image, k=3):
    # アスペクト比: aspect_ratio > 1.5
    # 最小面積: area > (w * h * 0.005)
    # NMS閾値: 0.3
```

## 🚀 パフォーマンス最適化

### 効率化のポイント
1. **早期終了**: 成功時即座に処理停止
2. **優先順位**: 効果的なプリセットを先に試行
3. **ROIフォールバック**: 全体処理失敗時のみ実行
4. **妥当性チェック**: 不正な数値の早期除外

### ベンチマーク結果
- **平均試行回数**: 3-5回（最大20回程度）
- **処理時間**: 1画像あたり2-5秒
- **メモリ使用量**: 段階的処理により効率的

## 🔧 トラブルシューティング

### よくある問題

#### 1. Azure API接続エラー
```bash
RuntimeError: VISION_ENDPOINT / VISION_KEY が未設定です
```
**解決**: `.env`ファイルでAPI認証情報を正しく設定

#### 2. 画像サイズエラー
```python
# 20MB超過時の自動リサイズ
if len(img_bytes) > 20 * 1024 * 1024:
    # 70%にリサイズして処理
```

#### 3. ROI抽出失敗
```python
# ROIが小さすぎる場合はスキップ
if roi_image.shape[0] < 20 or roi_image.shape[1] < 50:
    continue
```

### デバッグ方法
```bash
# 詳細ログで前処理過程を確認
python scripts/ocr/run_ocr.py --glob "problem_image.jpg"

# 可視化で失敗原因を特定
python scripts/ocr/analyze_ocr_results.py --results-dir runs/ocr/latest
```

## 📊 改善の方向性

### 現在の課題
1. **成功率向上**: 76.9% → 85%+ を目標
2. **処理速度**: 段階数削減による高速化
3. **正規表現調整**: より柔軟なパターンマッチング

### 今後の拡張予定
1. **機械学習ベース前処理**: より適応的な前処理選択
2. **多言語対応**: 日本語・中国語数字の認識
3. **バッチ処理最適化**: 大量画像の効率的処理

## 🔗 関連リソース

- [Azure Computer Vision API](https://docs.microsoft.com/ja-jp/azure/cognitive-services/computer-vision/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [プロジェクト進捗詳細](docs/project_status.md)
- [OCR分析レポート](docs/ocr_analysis_report.md) 