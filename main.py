"""
メルカリ自動化システム メインプログラム
Version 2.0 - 座標モジュール対応版
"""
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import json

# モジュールのインポート
from modules.research import MercariResearcher
from core.spreadsheet import SpreadsheetManager
from utils.logger import setup_logger

class MercariAutomationSystem:
    """
    統合自動化システム
    全モジュールを統括してリサーチを自動実行
    """
    def __init__(self):
        """初期化処理"""
        self.logger = setup_logger(__name__)
        self.logger.info("=" * 60)
        self.logger.info("メルカリ自動化システム起動")
        self.logger.info("=" * 60)
        
        # 設定読み込み
        self.load_config()
        
        # 座標設定の確認
        if not self.verify_coordinates():
            self.logger.error("座標設定が不完全です")
            print("\n座標設定が必要です。")
            print("python tools/coordinate_mapper.py を実行してください")
            sys.exit(1)
        
        # スプレッドシート初期化
        self.spreadsheet = SpreadsheetManager(self.config.get('spreadsheet_url'))
        
        # リサーチモジュール初期化
        self.researcher = MercariResearcher(self.spreadsheet)
        
        self.logger.info("システム初期化完了")

    def load_config(self):
        """設定ファイル読み込み"""
        config_path = Path("config/config.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.logger.warning("設定ファイルが見つかりません。デフォルト設定を使用")
            self.config = {
                "exchange_rate": 21.0,
                "profit_threshold": 30,
                "monthly_sales_threshold": 30,
                "spreadsheet_url": ""
            }

    def verify_coordinates(self):
        """座標設定の確認"""
        required_modules = ['mercari']  # 最低限必要なモジュール
        
        for module in required_modules:
            coord_file = Path(f"config/coordinate_sets/{module}.json")
            if not coord_file.exists():
                self.logger.error(f"{module}の座標が未設定")
                return False
                
            with open(coord_file, 'r', encoding='utf-8') as f:
                coords = json.load(f)
                if not coords or len(coords) <= 1:
                    self.logger.error(f"{module}の座標が不完全")
                    return False
                    
                self.logger.info(f"{module}: {len(coords)-1}項目の座標設定済み")
        
        return True

    def run_research_phase(self):
        """
        リサーチフェーズ実行
        カテゴリーベースで商品を検索し、3日間売上をカウント
        """
        self.logger.info("=" * 40)
        self.logger.info("リサーチフェーズ開始")
        self.logger.info("=" * 40)
        
        all_products = []
        
        # カテゴリー設定（キーワードは使用しない）
        categories = self._load_categories()
        
        for category_path in categories:
            self.logger.info(f"カテゴリー検索: {' > '.join(category_path)}")
            
            try:
                # メルカリ検索（カテゴリーベース）
                products = self.researcher.search_by_category(category_path, max_items=50)
                self.logger.info(f"  検索結果: {len(products)}件")
                
                # 業者商品フィルタリング
                filtered = self.researcher.filter_by_seller_type(products)
                self.logger.info(f"  業者商品: {len(filtered)}件")
                
                # 3日間売上分析
                analyzed = self.researcher.analyze_3days_sales(filtered)
                
                # 基準を満たす商品のみ
                threshold = self.config.get('monthly_sales_threshold', 30)
                qualified = [p for p in analyzed if p['monthly_estimate'] >= threshold]
                self.logger.info(f"  基準クリア: {len(qualified)}件（月{threshold}個以上）")
                
                # スプレッドシートに保存
                if qualified:
                    self.researcher.save_to_spreadsheet(qualified)
                
                all_products.extend(qualified)
                
                # レート制限対策
                time.sleep(60)  # 1分待機
                
            except Exception as e:
                self.logger.error(f"カテゴリー{category_path}でエラー: {e}")
                continue
        
        self.logger.info(f"リサーチ完了: 合計{len(all_products)}件")
        return all_products

    def _load_categories(self):
        """カテゴリー設定読み込み"""
        categories_file = Path("config/categories.txt")
        if categories_file.exists():
            categories = []
            with open(categories_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        categories.append(line.split(' > '))
            return categories
        else:
            # デフォルトカテゴリー
            return [
                ['家電・スマホ・カメラ', 'PC/タブレット', 'PC周辺機器'],
                ['おもちゃ・ホビー・グッズ', 'おもちゃ', 'キャラクターグッズ'],
                ['スポーツ・レジャー', 'トレーニング/エクササイズ', 'トレーニング用品']
            ]

    def run_with_menu(self):
        """メニュー形式で実行"""
        while True:
            self.show_menu()
            choice = input("\n選択 (0-5): ")
            
            if choice == "0":
                print("システムを終了します")
                break
            elif choice == "1":
                self.run_research_phase()
            elif choice == "2":
                self.setup_spreadsheet()
            elif choice == "3":
                self.show_statistics()
            elif choice == "4":
                self.run_coordinate_setup()
            elif choice == "5":
                self.show_config()
            else:
                print("無効な選択です")

    def show_menu(self):
        """メニュー表示"""
        print("\n" + "=" * 60)
        print(" メルカリ自動化システム - メインメニュー")
        print("=" * 60)
        print("1. リサーチ実行")
        print("2. スプレッドシート設定")
        print("3. 統計情報表示")
        print("4. 座標再設定")
        print("5. 設定確認")
        print("0. 終了")
        print("-" * 60)

    def setup_spreadsheet(self):
        """スプレッドシート初期設定"""
        print("\nスプレッドシート設定")
        
        if not self.config.get('spreadsheet_url'):
            url = input("スプレッドシートURLを入力してください: ")
            self.config['spreadsheet_url'] = url
            
            # 設定を保存
            config_path = Path("config/config.json")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        
        # スプレッドシートを開く
        if self.spreadsheet.open_spreadsheet():
            # ヘッダー行設定
            setup_header = input("ヘッダー行を設定しますか？ (y/n): ")
            if setup_header.lower() == 'y':
                self.spreadsheet.setup_headers()
        
        print("スプレッドシート設定完了")

    def show_statistics(self):
        """統計情報表示"""
        stats = self.spreadsheet.get_statistics()
        
        print("\n" + "=" * 60)
        print(" 統計情報")
        print("=" * 60)
        print(f"総商品数: {stats.get('total_products', 0)}")
        print(f"出品中: {stats.get('active_listings', 0)}")
        print(f"売却済み: {stats.get('sold', 0)}")
        print(f"合計売上: ¥{stats.get('total_sales', 0):,}")
        print(f"合計利益: ¥{stats.get('total_profit', 0):,}")
        print(f"平均利益率: {stats.get('avg_profit_rate', 0):.1f}%")

    def run_coordinate_setup(self):
        """座標再設定"""
        print("\n座標設定ツールを起動します...")
        
        try:
            from tools.coordinate_mapper import CoordinateMapper
            mapper = CoordinateMapper()
            mapper.start_mapping_session()
            
            # 座標再読み込み
            self.__init__()
            print("座標設定が完了し、システムを再初期化しました")
            
        except Exception as e:
            print(f"座標設定エラー: {e}")

    def show_config(self):
        """設定確認"""
        print("\n" + "=" * 60)
        print(" 現在の設定")
        print("=" * 60)
        
        for key, value in self.config.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")

def main():
    """メインエントリーポイント"""
    print("メルカリ自動化システムを起動しています...")
    
    try:
        system = MercariAutomationSystem()
        
        # コマンドライン引数処理
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
            if mode == "research":
                system.run_research_phase()
            elif mode == "setup":
                system.run_coordinate_setup()
            else:
                print(f"不明なモード: {mode}")
                print("使用可能: research, setup")
        else:
            # メニュー形式で実行
            system.run_with_menu()
            
    except KeyboardInterrupt:
        print("\n\n処理を中断しました")
    except Exception as e:
        print(f"\nシステムエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()