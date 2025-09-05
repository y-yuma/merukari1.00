# メルカリ自動化システム

## 概要
中国輸入ビジネスにおけるメルカリ販売の全18工程を自動化するRPAシステムです。

## 機能
- 🔍 **リサーチ自動化**: カテゴリーベースの商品検索と3日間売上分析
- 📊 **仕入れ判断**: アリババ画像検索による利益計算
- 📝 **出品自動化**: 商品情報の自動入力と出品
- 💰 **価格調整**: 日次の価格最適化と再出品

## 必要環境
- **Windows 10/11** または **macOS 10.15以上**
- **Python 3.9以上**
- **Google Chrome**
- **VSCode（推奨）**

## インストール

### 1. リポジトリのクローン
```bash
git clone https://github.com/your-repo/mercari-automation.git
cd mercari-automation
```

### 2. Python仮想環境の作成

#### Windows
```cmd
python -m venv venv
.\venv\Scripts\activate
```

#### macOS
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. パッケージインストール
```bash
pip install -r requirements.txt
```

### 4. Tesseract OCRのインストール

#### Windows
- https://github.com/UB-Mannheim/tesseract/wiki からインストーラーをダウンロード
- インストール時に「Japanese」と「Japanese (Vertical)」を追加

#### macOS
```bash
# Homebrewを使用
brew install tesseract tesseract-lang
```

## 初期設定

### 1. 必要なディレクトリを作成
#### Windows
```cmd
mkdir config\coordinate_sets
mkdir data\images\mercari
mkdir logs\screenshots
```

#### macOS
```bash
mkdir -p config/coordinate_sets
mkdir -p data/images/mercari
mkdir -p logs/screenshots
```

### 2. 空の__init__.pyファイルを作成
#### Windows
```cmd
echo. > modules\__init__.py
echo. > core\__init__.py  
echo. > utils\__init__.py
echo. > tools\__init__.py
```

#### macOS
```bash
touch modules/__init__.py
touch core/__init__.py
touch utils/__init__.py
touch tools/__init__.py
```

### 3. 座標設定
```bash
# Windows
python tools\coordinate_mapper.py

# macOS
python3 tools/coordinate_mapper.py
```

画面の指示に従って、各要素の座標を設定してください。

### 4. 設定ファイル編集
`config/config.json`を編集：
```json
{
  "spreadsheet_url": "YOUR_SPREADSHEET_URL",
  "exchange_rate": 21.0,
  "profit_threshold": 30,
  "monthly_sales_threshold": 30
}
```

## 使用方法

### 基本的な起動

#### Windows
```cmd
start.bat
```

#### macOS
```bash
chmod +x start.sh
./start.sh
```

### コマンドライン実行

#### Windows
```cmd
# リサーチのみ
python main.py research

# 座標設定
python main.py setup

# メニュー形式
python main.py
```

#### macOS  
```bash
# リサーチのみ
python3 main.py research

# 座標設定
python3 main.py setup

# メニュー形式
python3 main.py
```

## Mac特有の設定

### 1. アクセシビリティ許可
1. システム環境設定 > セキュリティとプライバシー > プライバシー
2. 「アクセシビリティ」を選択
3. Python（またはターミナル）を追加して許可

### 2. 画面収録の許可
1. システム環境設定 > セキュリティとプライバシー > プライバシー
2. 「画面収録」を選択  
3. Python（またはターミナル）を追加して許可

### 3. キーボードショートカット
- Macでは `Ctrl` キーの代わりに `Cmd` キーを使用
- システムが自動的に検出して適切なキーを使用します

## トラブルシューティング

### 座標がずれた場合
#### Windows
```cmd
python tools\coordinate_setup.py
```

#### macOS
```bash
python3 tools/coordinate_setup.py
```

### エラーログの確認
#### Windows
```cmd
type logs\error.log
```

#### macOS
```bash
cat logs/error.log
```

### よくある問題

#### Mac: "python3: command not found"
```bash
# Homebrewでpython3をインストール
brew install python3
```

#### Mac: Permission denied エラー
```bash
# 実行権限を付与
chmod +x start.sh
```

#### Windows: ModuleNotFoundError
```cmd
# 仮想環境が有効化されているか確認
.\venv\Scripts\activate
```

## システム要件

### Windows
- Windows 10 1903以降推奨
- RAM: 4GB以上
- ストレージ: 2GB以上の空き容量

### macOS
- macOS 10.15 (Catalina) 以降
- Intel Mac または Apple Silicon Mac対応
- RAM: 4GB以上
- ストレージ: 2GB以上の空き容量

## 制限事項
- 商品の色違いや仕様違いの自動判定はできません
- 1時間あたり300-500商品のリサーチが上限です
- メルカリの仕様変更により座標の再設定が必要な場合があります
- Mac版では一部のキーボードショートカットが異なります

## サポート

問題が発生した場合は、以下の情報と共に報告してください：
- OS（Windows/macOS）とバージョン
- エラーログ（`logs/error.log`）
- システムログ（`logs/system.log`）
- エラースクリーンショット（`logs/screenshots/`）

## ライセンス
プロプライエタリ - 無断複製・配布を禁じます