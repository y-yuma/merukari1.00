# tools/coordinate_setup.py
"""
座標初期設定スクリプト
プロジェクトの初回セットアップ時に実行
"""

import sys
from pathlib import Path
import json
from typing import List

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from tools.coordinate_mapper import CoordinateMapper  # noqa: E402

class CoordinateSetup:
    """座標初期設定クラス"""

    def __init__(self):
        self.mapper = CoordinateMapper()
        self.config_path = Path("config")
        self.coord_path = Path("config/coordinate_sets")

    def run_setup(self):
        """セットアップ実行"""
        self.print_welcome()

        # 環境チェック
        if not self.check_environment():
            return

        # 既存設定の確認
        existing_modules = self.check_existing_coordinates()

        if existing_modules:
            self.handle_existing_setup(existing_modules)
        else:
            self.run_initial_setup()

        # 設定完了
        self.print_completion()

    # --------- helpers ---------
    def print_welcome(self):
        """ウェルカムメッセージ"""
        print("=" * 80)
        print(" メルカリ自動化システム - 座標初期設定ツール")
        print("=" * 80)
        print("\nこのツールは、画面上の各要素の座標を設定します。")
        print("初回実行時は全モジュールの設定が必要です。")
        print("\n【準備事項】")
        print("1. Google Chromeを起動")
        print("2. メルカリにログイン")
        print("3. Googleスプレッドシートを開く")
        print("4. 1688.com（アリババ）を別タブで開く")
        print("5. ウィンドウサイズを固定（最大化推奨）")

    def check_environment(self) -> bool:
        """環境チェック"""
        print("\n環境チェック中...")
        self.coord_path.mkdir(parents=True, exist_ok=True)

        config_file = self.config_path / "config.json"
        if not config_file.exists():
            print("✗ config.jsonが見つかりません -> 既定を作成します")
            self.create_default_config()

        print("✓ 環境チェック完了")
        return True

    def create_default_config(self):
        """デフォルト設定ファイル作成"""
        default_config = {
            "spreadsheet_url": "",
            "exchange_rate": 21.0,
            "profit_threshold": 30,
            "monthly_sales_threshold": 30,
            "operation_hours": {"start": "09:00", "end": "23:00"},
        }
        self.config_path.mkdir(parents=True, exist_ok=True)
        with (self.config_path / "config.json").open("w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

    def check_existing_coordinates(self) -> List[str]:
        """既存の座標ファイル一覧を返す"""
        modules = []
        for m in ["mercari", "alibaba", "spreadsheet", "listing"]:
            if (self.coord_path / f"{m}.json").exists():
                modules.append(m)
        return modules

    def handle_existing_setup(self, modules: List[str]):
        """既存座標がある場合の処理"""
        print("\n既存の座標設定が見つかりました:")
        for m in modules:
            print(f" - {m}.json")
        print("\nオプション:")
        print(" 1) 追 加 測 定（未設定モジュールのみ）")
        print(" 2) モジュール個別で再測定")
        print(" 3) 全て測定し直す")
        choice = input("番号を入力してください (1/2/3): ").strip()

        if choice == "1":
            for m in ["mercari", "alibaba", "spreadsheet", "listing"]:
                if m not in modules:
                    getattr(self, f"map_{m}_only")()
        elif choice == "2":
            while True:
                name = input("再測定するモジュール名（mercari/alibaba/spreadsheet/listing, 空Enterで終了）: ").strip()
                if not name:
                    break
                if name in ["mercari", "alibaba", "spreadsheet", "listing"]:
                    getattr(self, f"map_{name}_only")()
                else:
                    print("不正な入力です")
        else:
            # 3 or その他
            self.run_initial_setup()

    def run_initial_setup(self):
        """初回セットアップ（全モジュール）"""
        self.map_mercari_only()
        ans = input("続けて Alibaba / Spreadsheet / Listing も設定しますか？ (y/N): ").strip().lower()
        if ans == "y":
            self.map_alibaba_only()
            self.map_spreadsheet_only()
            self.map_listing_only()

    def print_completion(self):
        """完了表示"""
        print("\n" + "=" * 60)
        print(" 座標初期設定が完了しました ")
        print("=" * 60)
        print("メニューから実行モードを選択")
        print("\n【トラブルシューティング】")
        print("- 座標がずれた場合: python tools/coordinate_setup.py で再設定")
        print("- 特定モジュールのみ: 選択的セットアップを使用")

    # --------- wrappers ---------
    def map_mercari_only(self):
        self.mapper.map_mercari_coordinates()

    def map_alibaba_only(self):
        self.mapper.map_alibaba_coordinates()

    def map_spreadsheet_only(self):
        self.mapper.map_spreadsheet_coordinates()

    def map_listing_only(self):
        self.mapper.map_listing_coordinates()


def main():
    """メインエントリーポイント"""
    setup = CoordinateSetup()
    setup.run_setup()


if __name__ == "__main__":
    main()
