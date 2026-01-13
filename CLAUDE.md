# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

マンガページレイアウト作成デスクトップアプリケーション。PyQt6ベースのGUIで、コマ割り、吹き出し、テキスト配置が可能。

## コマンド

```bash
# 依存パッケージインストール
pip install -r requirements.txt

# アプリケーション起動
python main.py

# 実行ファイルビルド（配布用）
python build.py
```

## アーキテクチャ

### レイヤー構成

```
src/
├── models/      # データモデル（Project, Page, Panel, SpeechBubble, TextElement, DividerLine）
├── views/       # PyQt6 UIコンポーネント
├── graphics/    # QGraphicsItemベースの描画アイテム
├── services/    # ビジネスロジック（エクスポート、シリアライズ、テンプレート）
├── commands/    # Undo/Redoコマンド（QUndoCommand）
├── workers/     # バックグラウンド処理（画像生成等）
└── utils/       # 定数（constants.py）、列挙型（enums.py）
```

### 主要クラス関係

- `MainWindow` がアプリケーション全体を管理し、`CanvasScene`/`CanvasView`（QGraphicsScene/QGraphicsView）でキャンバス描画
- 各ページは `CanvasScene` インスタンスを持ち、`_scenes` 辞書でキャッシュ
- グラフィックスアイテム（`*Item`）はモデル（`models/`）への参照を保持し、UIとデータを同期
- `PropertyPanel` が選択アイテムのプロパティ編集を担当

### 主要パターン

- **MVC風分離**: models（データ）、views（UI）、graphics（描画）、services（ロジック）
- **Undo/Redo**: `QUndoStack` と `src/commands/undo_commands.py` の `QUndoCommand` サブクラス
- **シグナル駆動**: PyQt6シグナル（`page_modified`, `selectionChanged`等）でコンポーネント間通信

### 定数管理

`src/utils/constants.py` に全ての設定値（サイズ、色、Z値等）を集約。新規定数はここに追加する。

### ファイル形式

- プロジェクト保存: `.manga` 形式（JSON）
- エクスポート: PNG, JPEG, PDF（reportlab使用）
