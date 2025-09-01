# メーター針検出・数値読取システム - 開発者向けガイド

## 📋 プロジェクト概要

本プロジェクトは、**アナログメーターの針位置を自動検出し、針の角度から数値を読み取るAIシステム**です。YOLOv8n-poseを使用したキーポイント検出とAzure Computer Vision OCRを組み合わせて、高精度なメーター読取を実現しています。

### 🎯 システムの目的
- アナログメーターの針の位置を自動検出
- 針の角度から実際の測定値への変換
- OCRによる数値表示の読み取り
- 工業・製造業での自動検査システムへの応用

### 📊 現在の精度
- **針検出精度**: mAP50 = 99.5%、mAP50-95 = 87.1%
- **キーポイント検出**: mAP50 = 99.5%、mAP50-95 = 91.0%
- **角度精度**: 現在MAE 48.26°（目標: ≤3°）
- **OCR成功率**: 76.9%（26枚中20枚成功）

## 🔧 技術スタック

### 主要フレームワーク・ライブラリ
- **物体検出**: Ultralytics YOLO v8n-pose
- **画像処理**: OpenCV
- **OCR**: Azure Computer Vision API
- **機械学習**: PyTorch（YOLOベース）
- **データ処理**: NumPy, pandas
- **設定管理**: YAML
- **可視化**: matplotlib

### 必須依存関係
```
ultralytics         # YOLO v8
opencv-python      # 画像処理
azure-ai-vision-imageanalysis  # Azure OCR
python-dotenv      # 環境変数管理
tqdm              # プログレスバー
pyyaml            # YAML設定ファイル
numpy             # 数値計算
```

## 📁 プロジェクト構造

```
object-detection-demo/
├── config/                      # 設定ファイル
│   ├── gauge_config.yml        # メーター仕様設定
│   ├── eval_config.yml         # 評価設定
│   ├── azure_ocr.yml          # Azure OCR設定
│   └── preprocessing_config.yml # 前処理設定
├── data/                       # 学習・評価データ
│   ├── images/
│   │   ├── train/             # 学習画像（28枚）
│   │   ├── val/               # 検証画像（8枚）
│   │   └── test/              # テスト画像（4枚）
│   └── labels/                # YOLO形式ラベル
├── data_ocr/                   # OCR専用データ
├── scripts/                    # 実行スクリプト
│   ├── eval_angle_mae.py      # 角度精度評価
│   ├── eval_value_mae.py      # 数値精度評価
│   └── ocr/                   # OCRモジュール
│       ├── run_ocr.py         # OCR実行メイン
│       ├── analyze_ocr_results.py # OCR結果分析
│       └── preprocess/        # 前処理エンジン
├── runs/                       # 学習・実行結果
│   ├── pose/train3/weights/   # 学習済みモデル
│   └── ocr/                   # OCR実行結果
├── docs/                       # ドキュメント
├── dataset.yaml                # YOLOデータセット設定
└── yolov8n-pose.pt            # 事前学習モデル
```

## 🚀 環境セットアップ

### 1. 必要な環境
- Python 3.8+
- CUDA対応GPU（推奨、CPUでも動作可能）
- Azure Computer Vision APIキー

### 2. 依存関係のインストール
```bash
# 仮想環境の作成・有効化
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# 必要なライブラリのインストール
pip install ultralytics opencv-python azure-ai-vision-imageanalysis
pip install python-dotenv tqdm pyyaml numpy matplotlib
```

### 3. 環境変数の設定
プロジェクトルートに `.env` ファイルを作成：
```env
VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
VISION_KEY=your-azure-vision-api-key
```

### 4. YOLOモデルの準備
```bash
# 事前学習モデルのダウンロード（自動実行される場合もあり）
# yolov8n-pose.pt は既にプロジェクトに含まれています

# 学習済みカスタムモデルの場所
# runs/pose/train3/weights/best.pt
```

## 🎮 主要機能の使用方法

### 1. 針角度の評価
```bash
cd /home/tomotomo/workspace/object-detection-demo
python scripts/eval_angle_mae.py
```
**機能**: テストデータに対して針の角度予測精度を評価
**出力**: 
- 角度MAE（平均絶対誤差）
- 可視化画像（GT vs 予測の矢印表示）
- CSV・JSON形式の詳細結果

### 2. 数値変換の評価
```bash
python scripts/eval_value_mae.py
```
**機能**: 角度から実際の測定値への変換精度を評価
**前提**: `config/gauge_config.yml` の設定が正しく行われていること

### 3. OCR実行
```bash
python scripts/ocr/run_ocr.py --glob "data_ocr/images/*.*"
```
**機能**: 
- Azure Computer Vision APIを使用した文字認識
- 前処理エンジンによる画像品質向上
- 数値のみの抽出・正規化

**オプション**:
- `--no-preprocessing`: 前処理を無効化
- `--outdir`: 出力先ディレクトリ指定

### 4. OCR結果の分析
```bash
python scripts/ocr/analyze_ocr_results.py runs/ocr/latest/results.jsonl
```
**機能**: OCR実行結果の詳細分析と失敗要因の特定

## 📈 現在の開発状況

### ✅ 完成済み機能
1. **物体検出システム**
   - YOLOv8n-poseによる針検出（mAP50: 99.5%）
   - pivot（回転軸）とtip（先端）のキーポイント検出
   - 学習パイプラインの確立

2. **角度計算システム**
   - 画像座標系での正確な角度算出
   - 円周上の最短差による誤差測定
   - 可視化機能付き評価システム

3. **OCR前処理システム**
   - 段階的画像前処理エンジン
   - Azure Computer Vision API統合
   - 数値抽出・正規化機能

4. **評価・分析ツール**
   - 角度MAE評価スクリプト
   - OCR結果分析ツール
   - 可視化・レポート生成機能

### ⚠️ 改善が必要な課題

#### 1. 角度精度の向上（最優先）
- **現状**: MAE 48.26°
- **目標**: ≤3°
- **原因**: pivot位置の微小誤差（2-3ピクセル）が角度誤差に拡大
- **対策**: データ量増加（28枚 → 98枚 → 147枚の段階的増強）

#### 2. データ不足
- **現状**: 学習データ40枚（train:28, val:8, test:4）
- **課題**: 汎化性能不足、統計的信頼性の低さ
- **計画**: 
  - Phase1: 70枚 → MAE 25-30°期待
  - Phase2: 140枚 → MAE 10-15°期待
  - Phase3: 210枚 → MAE 3-5°期待

#### 3. アノテーション品質
- **課題**: pivot位置の一貫性不足
- **対策**: 
  - ガイド円を使用した精密アノテーション
  - アノテーションガイドライン策定
  - 複数人による相互チェック

### ❌ 未実装機能

1. **実用システム化**
   - API化（REST API、バッチ処理対応）
   - エラーハンドリング強化
   - 複数画像の一括処理

2. **機種対応拡張**
   - SKU別仕様管理システム
   - 複数メーター機種への対応
   - 動的設定切り替え

3. **値変換システム**
   - 角度→数値変換の実装
   - 値MAE評価の実行
   - メーター機種別の変換ロジック

## 🎯 開発の優先順位

### Phase 1（短期: 1-2週間）
1. **データ収集**: train+21枚の追加撮影・アノテーション
2. **再学習・評価**: MAE改善効果の確認
3. **値MAE実装**: 実用性評価の開始

### Phase 2（中期: 1ヶ月）
4. **更なるデータ増加**: train=98枚まで拡張
5. **アノテーション品質向上**: ガイドライン策定・相互チェック
6. **機種対応設計**: SKU管理システムの基盤構築

### Phase 3（長期: 2-3ヶ月）
7. **実用システム化**: API化・バッチ処理対応
8. **パフォーマンス最適化**: 推論速度の向上
9. **エラーハンドリング**: 異常画像・未検出時の処理

## 💡 開発を始める前に

### 1. 既存ドキュメントの確認
- `docs/project_status.md`: 詳細な進捗状況
- `docs/ocr_analysis_report.md`: OCR分析結果

### 2. データセットの理解
- YOLO Pose形式のラベル構造
- キーポイント（pivot, tip）の意味
- 画像サイズと正規化座標系

### 3. 設定ファイルの確認
- `config/gauge_config.yml`: メーター仕様設定
- `dataset.yaml`: YOLOデータセット設定

### 4. 評価結果の確認
```bash
# 最新の学習結果確認
ls runs/pose/train3/
# 最新のOCR結果確認  
ls runs/ocr/
```

## 🔗 関連リソース

- [Ultralytics YOLO v8 Documentation](https://docs.ultralytics.com/)
- [Azure Computer Vision API](https://docs.microsoft.com/en-us/azure/cognitive-services/computer-vision/)
- [Roboflow Dataset](https://universe.roboflow.com/objectdetection-kjwct/my-first-project-zsqfw/dataset/2)

## 🤝 コントリビューション

新規開発者の皆様、このプロジェクトへようこそ！まずは上記のセットアップを完了し、既存の評価スクリプトを実行して現在の状況を把握してください。質問や提案がございましたら、お気軽にお声かけください。

**重要**: コマンド実行時は `pnpm` ではなく `python` コマンドを使用し、ターミナルコマンドで `&&` は使用しないでください。 