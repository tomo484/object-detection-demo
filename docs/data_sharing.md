# データ・結果共有ガイド

## 📊 共有データの管理

### 🎯 学習用データセット
- **場所**: [Google Drive/OneDrive/Dropboxのリンク]
- **更新頻度**: 新しいアノテーションデータ追加時
- **担当者**: データ収集チーム

### 🏆 学習済みモデル
- **最新モデル**: `runs/pose/train3/weights/best.pt`
- **バックアップ**: [クラウドストレージリンク]
- **性能**: mAP50=99.5%, 角度MAE=48.26°

### 📈 実験結果
- **結果サマリー**: `runs/experiment_log.json`
- **可視化画像**: `runs/visualizations/`
- **詳細ログ**: [実験管理ツールのリンク]

## 🔄 データ同期手順

### 初期セットアップ
```bash
# 1. リポジトリクローン
git clone [repository-url]
cd object-detection-demo

# 2. データフォルダ作成
mkdir -p data/images/{train,val,test}
mkdir -p data/labels/{train,val,test}

# 3. 共有データのダウンロード
# [クラウドストレージからのダウンロード手順]
```

### 定期同期
```bash
# 最新のデータセットを取得
# [定期的なデータ同期手順]

# 実験結果の共有
# [結果をチームに共有する手順]
```

## 📝 ファイル命名規則

### モデルファイル
- `best_v[version]_[date]_[performance].pt`
- 例: `best_v1.2_20250116_mae48.pt`

### 実験結果
- `experiment_[date]_[description]/`
- 例: `experiment_20250116_data_augmentation/`

### データセット
- `dataset_v[version]_[total_images]imgs/`
- 例: `dataset_v2_40imgs/`

## 🚀 推奨ワークフロー

1. **開発者A**: 新しいデータを収集・アノテーション
2. **共有**: クラウドストレージにアップロード
3. **通知**: チャットでデータ更新を通知
4. **開発者B,C**: データをダウンロードして実験実行
5. **結果共有**: 実験結果をクラウドにアップロード
6. **レビュー**: チーム全体で結果を確認・議論 