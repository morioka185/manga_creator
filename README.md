# Manga Creator

マンガページレイアウトを作成するためのデスクトップアプリケーションです。PyQt6を使用して構築されており、直感的なUIでマンガのコマ割り、吹き出し、テキストの配置が行えます。

**Stable Diffusion WebUI Forge連携によるAI画像生成機能を搭載。** キャラクターの一貫性を保った画像生成やストーリー仕様書からの一括生成が可能です。

## 機能

### ページ管理
- 複数ページの作成・削除・複製
- ページサイズのカスタマイズ（デフォルト: 1600x2560px）
- サムネイル付きページリスト

### コマ割り
- 分割線を描画してコマを自動生成
- 水平・垂直方向へのスナップ機能
- コマ間の余白（ガター）調整
- 8種類のレイアウトテンプレート
  - 4コマ縦割り
  - 2x2グリッド
  - 2x3グリッド
  - 3x2グリッド
  - 大1コマ+小2コマ
  - 上大+下2コマ
  - 3段構成
  - 2段構成

### 吹き出し
- 4種類の吹き出しタイプ
  - 楕円（通常のセリフ）
  - 角丸四角形
  - 雲形（思考・回想）
  - 爆発形（叫び・効果音）
- サイズ変更・移動
- しっぽの位置調整
- テキスト編集（ダブルクリック）
- 縦書き/横書き切替（デフォルト：縦書き）

### テキスト
- 自由配置テキスト
- フォント・サイズ・色の変更

### 画像
- コマへの画像配置（ダブルクリックで読み込み）
- 画像の拡大縮小（マウスホイールまたはプロパティパネル）
- 画像の位置調整（ドラッグでトリミング位置変更）
- 右クリックメニューで画像の変更・クリア・リセット

### AI画像生成（Forge連携）
- **txt2img生成**: プロンプトから画像を生成
- **キャラクター管理**: 参照画像とプロンプトを登録して一貫性のあるキャラクター生成
- **IP-Adapter**: 参照画像から特徴を抽出してキャラクターの一貫性を維持
- **ControlNet**: ポーズ画像による構図指定
- **複数キャラクターモード**: Regional Prompterによる画面分割生成
- **ADetailer**: 顔の自動補正
- **ストーリーインポート**: JSON仕様書から一括画像生成

### エクスポート
- PNG形式（300 DPI）
- JPEG形式（品質調整可能）
- PDF形式（複数ページ対応）

### 操作
- ズーム（Ctrl + マウスホイール、0.2x〜5.0x）
- 画面にフィット表示
- 選択ツール / コマツール / 吹き出しツール / テキストツール
- 元に戻す / やり直し
- コピー / ペースト

### ファイル
- プロジェクト保存（.manga形式）
- プロジェクト読み込み
- 未保存変更の警告

## インストール

### 必要条件
- Python 3.10以上

### セットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd manga_creator

# 仮想環境を作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# または
venv\Scripts\activate  # Windows

# 依存パッケージをインストール
pip install -r requirements.txt
```

## AI画像生成のセットアップ（Forge環境構築）

AI画像生成機能を使用するには、Stable Diffusion WebUI Forgeのセットアップが必要です。

### 方法1: Stability Matrix（推奨・初心者向け）

[Stability Matrix](https://github.com/LykosAI/StabilityMatrix)は、Stable Diffusion関連ツールを簡単に管理できるランチャーです。

1. **Stability Matrixをダウンロード**
   - https://github.com/LykosAI/StabilityMatrix/releases から最新版をダウンロード
   - Windowsの場合: `StabilityMatrix-win-x64.zip`

2. **Stability Matrixを起動してForgeをインストール**
   - 解凍して `StabilityMatrix.exe` を起動
   - 「Packages」タブで「Add Package」をクリック
   - 「Stable Diffusion WebUI Forge」を選択してインストール
   - インストール先は `C:\StabilityMatrix\Data\Packages\stable-diffusion-webui-forge` などになります

3. **モデルをダウンロード**
   - 「Models」タブで「Download」をクリック
   - Civitai等からSD1.5またはSDXL系のモデルをダウンロード
   - 推奨モデル例:
     - アニメ系: `animagine-xl-3.1.safetensors`（SDXL）
     - 汎用: `sd-v1-5.safetensors`（SD1.5）

4. **Forgeを起動**
   - 「Packages」タブでForgeの「Launch」をクリック
   - 初回起動時は依存関係のダウンロードに時間がかかります
   - 起動完了後、ブラウザで `http://127.0.0.1:7860` が開きます

### 方法2: 手動インストール

```bash
# Forgeをクローン
git clone https://github.com/lllyasviel/stable-diffusion-webui-forge
cd stable-diffusion-webui-forge

# Windows: webui-user.batを編集してAPIを有効化
# COMMANDLINE_ARGS に --api を追加

# 起動
webui-user.bat  # Windows
./webui.sh      # Linux/macOS
```

### Manga CreatorでのForge設定

1. **設定ダイアログを開く**
   - メニュー「編集」→「設定」→「AI画像生成」タブ

2. **接続設定**
   - **Forgeパス**: Forgeのインストールフォルダを指定
     - Stability Matrixの場合: `C:\StabilityMatrix\Data\Packages\stable-diffusion-webui-forge`
   - **API URL**: `http://127.0.0.1:7860`（通常はデフォルトのまま）
   - 「接続テスト」ボタンで接続を確認

3. **オプション設定**
   - **自動起動**: AI生成時にForgeを自動起動する場合はチェック
   - **API-onlyモード**: UIなしで高速起動（エラーが出る場合はオフに）

### 推奨拡張機能（複数キャラクター生成用）

複数キャラクターの同時生成を行う場合は、以下の拡張機能のインストールを推奨します。

| 拡張機能 | 用途 | インストール |
|---------|------|-------------|
| Regional Prompter | 画面分割でキャラクター別プロンプト適用 | Forge内「Extensions」タブから |
| ADetailer | 顔の自動検出・補正 | Forge内「Extensions」タブから |
| ControlNet | ポーズ指定、IP-Adapter | Forgeに同梱済み |

**インストール手順:**
1. Forgeを起動してWebUIにアクセス
2. 「Extensions」タブ→「Install from URL」
3. 以下のURLを入力してインストール:
   - Regional Prompter: `https://github.com/hako-mikan/sd-webui-regional-prompter`
   - ADetailer: `https://github.com/Bing-su/adetailer`
4. Forgeを再起動

**動作確認:**
- Manga Creatorの設定ダイアログで「拡張機能確認」ボタンをクリック

## 使い方

### 起動

```bash
python main.py
```

### 基本操作

1. **コマ割りの作成**
   - 左パネルから「コマ」ツールを選択
   - キャンバス上でドラッグして分割線を描画
   - 分割線が交差する部分で自動的にコマが生成されます

2. **テンプレートの使用**
   - 左パネルのテンプレートボタンをクリック
   - 選択したレイアウトが自動的に適用されます

3. **吹き出しの追加**
   - 「吹き出し」ツールを選択
   - 吹き出しタイプを選択（楕円/角丸/雲/爆発）
   - キャンバス上でドラッグして配置
   - ダブルクリックでテキストを編集

4. **テキストの追加**
   - 「テキスト」ツールを選択
   - キャンバス上でクリックして配置
   - 右パネルでフォント・サイズ・色を調整

5. **画像の配置と編集**
   - コマをダブルクリックで画像を選択
   - マウスホイールで拡大縮小（1.0x〜4.0x）
   - ドラッグで画像の位置を調整（トリミング）
   - 右クリックで画像の変更・クリア・リセット
   - プロパティパネルでも拡大率を調整可能

6. **AI画像生成**
   - コマを選択して「AI生成」ボタンをクリック
   - プロンプトを入力して「生成」
   - 生成された画像から選んで「コマに配置」

7. **キャラクター管理**
   - AI生成ダイアログで「管理」ボタンをクリック
   - キャラクターを追加して参照画像を設定
   - 生成時にキャラクターを選択するとIP-Adapterで一貫性を維持

8. **ストーリーインポート**
   - メニュー「ファイル」→「ストーリーを読み込み」
   - JSON形式の仕様書を選択
   - キャラクター画像を生成（推奨）
   - 「一括生成」で全コマの画像を生成

9. **エクスポート**
   - メニュー「ファイル」→「エクスポート」
   - PNG / JPEG / PDF から形式を選択

### キーボードショートカット

| 操作 | ショートカット |
|------|---------------|
| 新規 | Ctrl + N |
| 開く | Ctrl + O |
| 保存 | Ctrl + S |
| 名前を付けて保存 | Ctrl + Shift + S |
| 元に戻す | Ctrl + Z |
| やり直し | Ctrl + Y / Ctrl + Shift + Z |
| コピー | Ctrl + C |
| ペースト | Ctrl + V |
| 削除 | Delete |
| ズームイン | Ctrl + マウスホイール上 |
| ズームアウト | Ctrl + マウスホイール下 |
| コマ内画像の拡大 | マウスホイール上（コマ上で） |
| コマ内画像の縮小 | マウスホイール下（コマ上で） |
| コマ内画像の移動 | ドラッグ（コマ上で） |

## プロジェクト構成

```
manga_creator/
├── main.py                 # アプリケーションエントリーポイント
├── build.py                # 実行ファイルビルドスクリプト
├── requirements.txt        # 依存パッケージ
├── README.md              # このファイル
└── src/
    ├── models/            # データモデル
    │   ├── project.py         # プロジェクト
    │   ├── page.py            # ページ
    │   ├── panel.py           # コマ
    │   ├── panel_image_data.py    # コマ画像データ
    │   ├── divider_line.py    # 分割線
    │   ├── speech_bubble.py   # 吹き出し
    │   ├── text_element.py    # テキスト要素
    │   └── character.py       # キャラクター
    ├── views/             # UIコンポーネント
    │   ├── main_window.py     # メインウィンドウ
    │   ├── canvas_scene.py    # キャンバスシーン
    │   ├── canvas_view.py     # キャンバスビュー
    │   ├── page_list_widget.py # ページリスト
    │   ├── panels/
    │   │   ├── tool_panel.py      # ツールパネル
    │   │   └── property_panel.py  # プロパティパネル
    │   └── dialogs/
    │       ├── settings_dialog.py         # 設定ダイアログ
    │       ├── image_gen_dialog.py        # AI画像生成ダイアログ
    │       ├── character_manager_dialog.py    # キャラクター管理
    │       ├── character_generation_dialog.py # キャラクター画像生成
    │       └── story_import_dialog.py     # ストーリーインポート
    ├── graphics/          # グラフィックスアイテム
    │   ├── panel_item.py          # コマアイテム
    │   ├── speech_bubble_item.py  # 吹き出しアイテム
    │   ├── text_item.py           # テキストアイテム
    │   ├── divider_line_item.py   # 分割線アイテム
    │   └── bubble_shapes.py       # 吹き出し形状
    ├── services/          # ビジネスロジック
    │   ├── panel_calculator.py    # コマ計算
    │   ├── export_service.py      # エクスポート
    │   ├── template_service.py    # テンプレート
    │   ├── project_serializer.py  # 保存/読み込み
    │   ├── settings_service.py    # 設定管理
    │   ├── forge_service.py       # Forge API通信
    │   ├── forge_launcher.py      # Forge起動管理
    │   ├── character_service.py   # キャラクター管理
    │   ├── story_import_service.py    # ストーリーインポート
    │   └── image_path_service.py  # 画像パス管理
    ├── workers/           # バックグラウンド処理
    │   ├── generation_worker.py       # 画像生成ワーカー
    │   └── batch_generation_worker.py # バッチ生成ワーカー
    ├── commands/          # Undo/Redoコマンド
    │   └── undo_commands.py
    └── utils/             # ユーティリティ
        ├── constants.py   # 定数
        └── enums.py       # 列挙型
```

## 依存パッケージ

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| PyQt6 | >= 6.6.0 | GUIフレームワーク |
| reportlab | >= 4.0.0 | PDF生成 |
| Pillow | >= 10.0.0 | 画像処理 |
| requests | >= 2.31.0 | HTTP通信（Forge API） |
| PyInstaller | >= 6.0.0 | 実行ファイル作成 |

## 実行ファイルの作成（配布用）

非エンジニアでも使えるよう、ダブルクリックで起動できる実行ファイルを作成できます。

### ビルド方法

```bash
# 依存パッケージをインストール（初回のみ）
pip install -r requirements.txt

# ビルド実行
python build.py
```

### 出力先

| OS | 出力ファイル | 場所 |
|----|------------|------|
| Windows | MangaCreator.exe | dist/MangaCreator.exe |
| Mac | MangaCreator.app | dist/MangaCreator.app |

### 配布方法

1. `dist/` フォルダ内の実行ファイルをZIPで圧縮
2. ユーザーに配布
3. ユーザーはダブルクリックで起動可能

### 注意事項

- **クロスコンパイル不可**: Windows用はWindows上で、Mac用はMac上でビルドする必要があります
- **アイコン設定**: `assets/icon.ico`（Windows用）や `assets/icon.icns`（Mac用）を配置すると、アプリアイコンが適用されます

## ストーリー仕様書のフォーマット

JSON形式でストーリーを定義し、一括でマンガを生成できます。

```json
{
  "title": "マンガタイトル",
  "characters": [
    {
      "id": "char1",
      "name": "主人公",
      "appearance": "黒髪ショート、青い目",
      "personality": "元気で明るい",
      "prompt": "1girl, black hair, short hair, blue eyes"
    }
  ],
  "pages": [
    {
      "page_number": 1,
      "template": "4panel_2x2",
      "panels": [
        {
          "panel_index": 0,
          "scene_description": "主人公が登場するシーン",
          "characters": ["char1"],
          "composition": "medium_shot",
          "prompt": "standing, smile, school uniform",
          "negative_prompt": "bad anatomy",
          "dialogues": [
            {
              "speaker": "主人公",
              "text": "こんにちは！"
            }
          ]
        }
      ]
    }
  ]
}
```

## トラブルシューティング

### Forgeに接続できない

1. Forgeが起動しているか確認
2. `--api` オプション付きで起動しているか確認
3. ファイアウォールでポート7860がブロックされていないか確認
4. API URLが正しいか確認（通常は `http://127.0.0.1:7860`）

### 画像生成が失敗する

1. Forgeでモデルが選択されているか確認
2. 設定ダイアログで「接続テスト」を実行
3. Forge側のコンソールでエラーメッセージを確認
4. VRAMが不足している場合は解像度を下げる

### キャラクターの一貫性が保てない

1. IP-Adapterモデルがインストールされているか確認（設定ダイアログの「拡張機能確認」）
2. 参照画像が鮮明で、キャラクターの顔が大きく写っているものを使用
3. IP-Adapter強度を調整（0.7〜0.9推奨）

## 今後の予定

- [x] プロジェクトの保存/読み込み機能
- [x] 元に戻す/やり直し機能
- [x] コピー/ペースト機能
- [x] AI画像生成（Forge連携）
- [x] キャラクター管理
- [x] ストーリーインポート
- [ ] レイヤー管理
- [ ] ドラッグ&ドロップによる画像読み込み
- [ ] カスタムテンプレートの保存
- [ ] img2img対応

## ライセンス

MIT License

## 作者

Manga Creator Team
