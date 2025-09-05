"""
座標測定ツール - 各モジュールごとに座標を設定可能
Version 2.0 - モジュール別管理対応
"""
import pyautogui
import json
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional
import sys

class CoordinateMapper:
    """
    座標マッピングツール
    各モジュールの画面要素の座標を記録・管理
    """
    def __init__(self):
        """初期化処理"""
        self.coordinates = {}
        self.current_module = None
        self.base_path = Path("config/coordinate_sets")
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # PyAutoGUIの安全設定
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5

    def start_mapping_session(self):
        """
        マッピングセッション開始
        対話的に座標を設定
        """
        self.print_header()
        while True:
            choice = self.show_menu()
            if choice == "0":
                print("\n座標測定を終了します")
                self.print_summary()
                break
            elif choice == "1":
                self.map_mercari_coordinates()
            elif choice == "2":
                self.map_alibaba_coordinates()
            elif choice == "3":
                self.map_spreadsheet_coordinates()
            elif choice == "4":
                self.map_listing_coordinates()
            elif choice == "5":
                self.map_all_coordinates()
            elif choice == "6":
                self.verify_all_coordinates()
            elif choice == "7":
                self.test_coordinates()
            else:
                print("無効な選択です")

    def print_header(self):
        """ヘッダー表示"""
        print("=" * 80)
        print("    座標測定ツール v2.0 - メルカリ自動化システム")
        print("=" * 80)
        print("\n【使い方】")
        print("1. 対象の画面要素が表示されている状態にする")
        print("2. マウスを目的の位置に移動")
        print("3. Enterキーを押して座標を記録")
        print("4. スキップする場合は 's' を入力")
        print("\n【注意事項】")
        print("- ウィンドウサイズを固定してください")
        print("- 全画面表示は避けてください")
        print("- デュアルディスプレイの場合はメイン画面で実行")

    def show_menu(self):
        """メニュー表示"""
        print("\n" + "-" * 60)
        print("設定メニュー:")
        print("-" * 60)
        print("1. メルカリ座標設定")
        print("2. アリババ座標設定")
        print("3. スプレッドシート座標設定")
        print("4. 出品座標設定")
        print("5. 全モジュール設定")
        print("6. 設定確認")
        print("7. 座標テスト")
        print("0. 終了")
        print("-" * 60)
        return input("選択してください (0-7): ")

    def get_coordinate(self, name: str, description: str = "") -> Optional[Tuple[int, int]]:
        """
        単一座標の取得
        Args:
            name: 座標の名前
            description: 座標の説明
        Returns:
            座標のタプル (x, y) またはNone
        """
        print(f"\n{'=' * 60}")
        print(f"設定項目: {name}")
        if description:
            print(f"説明: {description}")
        print("-" * 60)
        print("操作方法:")
        print("  1. マウスを目的の位置に移動")
        print("  2. Enterキーを押して確定")
        print("  3. スキップする場合は 's' + Enter")
        print("  4. 3秒間のカウントダウン後に位置を取得する場合は 't' + Enter")
        
        user_input = input("\n入力: ").lower().strip()
        
        if user_input == 's':
            print(f"✗ {name} をスキップしました")
            return None
        elif user_input == 't':
            print("\n3秒後に座標を取得します...")
            for i in range(3, 0, -1):
                print(f"{i}...")
                time.sleep(1)
            x, y = pyautogui.position()
            print(f"✓ {name}: ({x}, {y}) を記録しました")
            time.sleep(0.3)
            return (x, y)
        else:
            x, y = pyautogui.position()
            print(f"✓ {name}: ({x}, {y}) を記録しました")
            time.sleep(0.3)
            return (x, y)

    def get_area_coordinates(self, name: str, description: str = "") -> Optional[Dict]:
        """
        エリア座標の取得（左上と右下）
        Args:
            name: エリアの名前
            description: エリアの説明
        Returns:
            エリアの座標辞書 {"top_left": (x, y), "bottom_right": (x, y)}
        """
        print(f"\n{'=' * 60}")
        print(f"エリア設定: {name}")
        if description:
            print(f"説明: {description}")
        print("-" * 60)
        
        print("\n【左上の座標を設定】")
        top_left = self.get_coordinate(f"{name}_左上", "エリアの左上角")
        if not top_left:
            return None
            
        print("\n【右下の座標を設定】")
        bottom_right = self.get_coordinate(f"{name}_右下", "エリアの右下角")
        if not bottom_right:
            return None
            
        return {
            "top_left": top_left,
            "bottom_right": bottom_right,
            "width": bottom_right[0] - top_left[0],
            "height": bottom_right[1] - top_left[1]
        }

    def map_mercari_coordinates(self):
        """メルカリ用座標マッピング（詳細版）"""
        self.current_module = "mercari"
        print("\n" + "=" * 80)
        print("メルカリモジュール座標設定")
        print("=" * 80)
        print("\nメルカリのページを開いて準備してください")
        input("準備ができたらEnterキーを押してください...")
        
        mercari_coords = {}
        
        # トップページ要素
        print("\n【トップページ要素】")
        mercari_coords['logo'] = self.get_coordinate(
            'logo',
            'メルカリロゴ（ホームに戻る用）'
        )
        mercari_coords['search_bar'] = self.get_coordinate(
            'search_bar',
            '検索バー（使用しないが位置確認用）'
        )
        
        # カテゴリー関連
        print("\n【カテゴリー設定】")
        mercari_coords['category_button'] = self.get_coordinate(
            'category_button',
            'カテゴリーボタンの位置'
        )
        
        # 大カテゴリー
        print("\n【大カテゴリー（第1階層）】")
        categories_level1 = [
            ('category_electronics', '家電・スマホ・カメラ'),
            ('category_toys', 'おもちゃ・ホビー・グッズ'),
            ('category_sports', 'スポーツ・レジャー'),
            ('category_mens', 'メンズ'),
            ('category_ladies', 'レディース'),
            ('category_baby', 'ベビー・キッズ')
        ]
        for cat_id, cat_name in categories_level1:
            mercari_coords[cat_id] = self.get_coordinate(cat_id, cat_name)
        
        # 中カテゴリー
        print("\n【中カテゴリー（第2階層）】")
        categories_level2 = [
            ('category_pc_tablet', 'PC/タブレット'),
            ('category_smartphone', 'スマートフォン本体'),
            ('category_camera', 'カメラ'),
            ('category_toys_general', 'おもちゃ'),
            ('category_character', 'キャラクターグッズ'),
            ('category_training', 'トレーニング/エクササイズ')
        ]
        for cat_id, cat_name in categories_level2:
            mercari_coords[cat_id] = self.get_coordinate(cat_id, cat_name)
        
        # 小カテゴリー
        print("\n【小カテゴリー（第3階層）】")
        categories_level3 = [
            ('category_pc_accessories', 'PC周辺機器'),
            ('category_tablet_accessories', 'タブレット'),
            ('category_smartphone_accessories', 'スマホアクセサリー'),
            ('category_training_goods', 'トレーニング用品'),
            ('category_yoga', 'ヨガ'),
            ('category_running', 'ランニング')
        ]
        for cat_id, cat_name in categories_level3:
            mercari_coords[cat_id] = self.get_coordinate(cat_id, cat_name)
        
        # フィルター関連
        print("\n【フィルター設定】")
        mercari_coords['filter_button'] = self.get_coordinate(
            'filter_button',
            '詳細検索ボタン'
        )
        mercari_coords['condition_filter'] = self.get_coordinate(
            'condition_filter',
            '商品の状態フィルター'
        )
        mercari_coords['condition_new'] = self.get_coordinate(
            'condition_new',
            '新品・未使用チェックボックス'
        )
        mercari_coords['condition_unused'] = self.get_coordinate(
            'condition_unused',
            '未使用に近いチェックボックス'
        )
        mercari_coords['price_range'] = self.get_coordinate(
            'price_range',
            '価格帯選択'
        )
        mercari_coords['price_min'] = self.get_coordinate(
            'price_min',
            '最低価格入力欄'
        )
        mercari_coords['price_max'] = self.get_coordinate(
            'price_max',
            '最高価格入力欄'
        )
        mercari_coords['sold_filter'] = self.get_coordinate(
            'sold_filter',
            '販売状況フィルター'
        )
        mercari_coords['sold_out_checkbox'] = self.get_coordinate(
            'sold_out_checkbox',
            '売り切れチェックボックス'
        )
        mercari_coords['search_button'] = self.get_coordinate(
            'search_button',
            '検索実行ボタン'
        )
        
        # 商品グリッド（20個まで対応）
        print("\n【商品グリッド設定】")
        print("※商品一覧の各商品の中心位置をクリック")
        for i in range(1, 21):
            coord = self.get_coordinate(
                f'product_grid_{i}',
                f'{i}番目の商品位置（{(i-1)//5 + 1}行{(i-1)%5 + 1}列目）'
            )
            if coord:
                mercari_coords[f'product_grid_{i}'] = coord
            else:
                if i <= 10:  # 最初の10個は必須
                    print(f"警告: 商品グリッド{i}は必須項目です")
        
        # 商品詳細ページ
        print("\n【商品詳細ページ要素】")
        mercari_coords['product_title'] = self.get_coordinate(
            'product_title',
            '商品タイトル位置'
        )
        mercari_coords['product_price'] = self.get_coordinate(
            'product_price',
            '商品価格位置'
        )
        mercari_coords['product_description'] = self.get_coordinate(
            'product_description',
            '商品説明文エリア'
        )
        
        # 商品画像エリア
        print("\n【商品画像エリア】")
        image_area = self.get_area_coordinates(
            'product_image_area',
            '商品画像表示エリア（複数画像対応）'
        )
        if image_area:
            mercari_coords['product_image_area'] = image_area
        
        mercari_coords['product_image_main'] = self.get_coordinate(
            'product_image_main',
            'メイン商品画像の中心'
        )
        
        # 販売者情報
        print("\n【販売者情報】")
        mercari_coords['seller_name'] = self.get_coordinate(
            'seller_name',
            '販売者名表示位置'
        )
        mercari_coords['seller_rating'] = self.get_coordinate(
            'seller_rating',
            '販売者評価表示位置'
        )
        
        # 売却情報エリア
        print("\n【売却情報エリア】")
        mercari_coords['sold_label'] = self.get_coordinate(
            'sold_label',
            'SOLDラベル位置'
        )
        
        sold_history_area = self.get_area_coordinates(
            'sold_history_area',
            '売却履歴表示エリア（3日間売上カウント用）'
        )
        if sold_history_area:
            mercari_coords['sold_history_area'] = sold_history_area
        
        # ナビゲーション
        print("\n【ナビゲーション】")
        mercari_coords['back_button'] = self.get_coordinate(
            'back_button',
            '戻るボタン位置'
        )
        mercari_coords['next_page'] = self.get_coordinate(
            'next_page',
            '次のページボタン'
        )
        
        # 保存
        self.save_coordinates(mercari_coords, 'mercari')
        print(f"\n✓ メルカリ座標設定完了: {len(mercari_coords)}項目")

    def map_alibaba_coordinates(self):
        """アリババ用座標マッピング（基本版）"""
        self.current_module = "alibaba"
        print("\n" + "=" * 80)
        print("アリババ（1688.com）モジュール座標設定")
        print("=" * 80)
        print("\n1688.comを開いて準備してください")
        input("準備ができたらEnterキーを押してください...")
        
        alibaba_coords = {}
        
        # 画像検索機能
        print("\n【画像検索機能】")
        alibaba_coords['image_search_button'] = self.get_coordinate(
            'image_search_button',
            'カメラアイコン（画像検索開始）'
        )
        alibaba_coords['file_upload_button'] = self.get_coordinate(
            'file_upload_button',
            'ローカルファイル選択ボタン'
        )
        
        # 検索結果一覧
        print("\n【検索結果一覧】")
        for i in range(1, 4):  # 上位3件のみ
            alibaba_coords[f'search_result_{i}'] = self.get_coordinate(
                f'search_result_{i}',
                f'検索結果{i}番目の商品'
            )
        
        # 商品詳細ページ
        print("\n【商品詳細ページ】")
        alibaba_coords['product_title'] = self.get_coordinate(
            'product_title',
            '商品タイトル'
        )
        alibaba_coords['price_element'] = self.get_coordinate(
            'price_element',
            '価格表示エリア'
        )
        alibaba_coords['moq_element'] = self.get_coordinate(
            'moq_element',
            'MOQ（最小注文数）表示'
        )
        alibaba_coords['weight_element'] = self.get_coordinate(
            'weight_element',
            '商品重量表示'
        )
        
        # 保存
        self.save_coordinates(alibaba_coords, 'alibaba')
        print(f"\n✓ アリババ座標設定完了: {len(alibaba_coords)}項目")

    def map_spreadsheet_coordinates(self):
        """スプレッドシート用座標マッピング（基本版）"""
        self.current_module = "spreadsheet"
        print("\n" + "=" * 80)
        print("Googleスプレッドシートモジュール座標設定")
        print("=" * 80)
        print("\nGoogleスプレッドシートを開いて準備してください")
        input("準備ができたらEnterキーを押してください...")
        
        spreadsheet_coords = {}
        
        # ヘッダー行設定
        print("\n【ヘッダー行設定（1行目）】")
        headers = [
            ('header_a1', 'A1: キーワード'),
            ('header_b1', 'B1: 予想販売数/月'),
            ('header_c1', 'C1: メルカリ相場'),
            ('header_e1', 'E1: 商品URL'),
            ('header_g1', 'G1: 仕入URL'),
            ('header_h1', 'H1: 仕入価格'),
            ('header_m1', 'M1: 利益率'),
            ('header_o1', 'O1: ステータス')
        ]
        for cell_id, description in headers:
            spreadsheet_coords[cell_id] = self.get_coordinate(cell_id, description)
        
        # データ行設定
        print("\n【データ行設定（2行目）】")
        data_cells = [
            ('cell_a2', 'A2: キーワード入力セル'),
            ('cell_b2', 'B2: 予想販売数入力セル'),
            ('cell_c2', 'C2: メルカリ相場入力セル'),
            ('cell_e2', 'E2: 商品URL入力セル'),
            ('cell_g2', 'G2: 仕入URL入力セル'),
            ('cell_h2', 'H2: 仕入価格入力セル'),
            ('cell_m2', 'M2: 利益率計算セル'),
            ('cell_o2', 'O2: ステータス表示セル')
        ]
        for cell_id, description in data_cells:
            spreadsheet_coords[cell_id] = self.get_coordinate(cell_id, description)
        
        # 保存
        self.save_coordinates(spreadsheet_coords, 'spreadsheet')
        print(f"\n✓ スプレッドシート座標設定完了: {len(spreadsheet_coords)}項目")

    def map_listing_coordinates(self):
        """出品用座標マッピング（基本版）"""
        self.current_module = "listing"
        print("\n" + "=" * 80)
        print("メルカリ出品モジュール座標設定")
        print("=" * 80)
        print("\nメルカリの出品ページを開いて準備してください")
        input("準備ができたらEnterキーを押してください...")
        
        listing_coords = {}
        
        # 基本的な出品要素のみ
        print("\n【出品フォーム】")
        listing_coords['upload_image'] = self.get_coordinate(
            'upload_image',
            '画像アップロードボタン'
        )
        listing_coords['title_input'] = self.get_coordinate(
            'title_input',
            '商品名入力欄'
        )
        listing_coords['description_input'] = self.get_coordinate(
            'description_input',
            '商品説明入力欄'
        )
        listing_coords['price_input'] = self.get_coordinate(
            'price_input',
            '販売価格入力欄'
        )
        listing_coords['submit_button'] = self.get_coordinate(
            'submit_button',
            '出品するボタン'
        )
        
        # 保存
        self.save_coordinates(listing_coords, 'listing')
        print(f"\n✓ 出品座標設定完了: {len(listing_coords)}項目")

    def map_all_coordinates(self):
        """全モジュールの座標を順番に設定"""
        print("\n全モジュールの座標を順番に設定します")
        print("これには約15-30分かかる場合があります")
        confirm = input("\n続行しますか？ (y/n): ")
        if confirm.lower() != 'y':
            print("キャンセルしました")
            return
        
        self.map_mercari_coordinates()
        print("\n次のモジュールに進みます...")
        time.sleep(2)
        
        self.map_alibaba_coordinates()
        print("\n次のモジュールに進みます...")
        time.sleep(2)
        
        self.map_spreadsheet_coordinates()
        print("\n次のモジュールに進みます...")
        time.sleep(2)
        
        self.map_listing_coordinates()
        
        print("\n" + "=" * 80)
        print("✓ 全モジュールの設定が完了しました")
        self.print_summary()

    def save_coordinates(self, coords: Dict, module_name: str):
        """
        座標を保存
        Args:
            coords: 座標辞書
            module_name: モジュール名
        """
        # None値を除外
        coords = {k: v for k, v in coords.items() if v is not None}
        
        # ファイルパス
        filepath = self.base_path / f"{module_name}.json"
        
        # 既存の座標があれば読み込んでマージ
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            # 新しい座標で更新
            existing.update(coords)
            coords = existing
        
        # メタデータ追加
        coords['_metadata'] = {
            'module': module_name,
            'updated_at': datetime.now().isoformat(),
            'total_items': len(coords) - 1,  # metadataを除く
            'screen_size': pyautogui.size()
        }
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(coords, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ {module_name}の座標を保存しました")
        print(f"  ファイル: {filepath}")
        print(f"  設定項目数: {len(coords) - 1}")

    def load_coordinates(self, module_name: str) -> Dict:
        """
        座標を読み込み
        Args:
            module_name: モジュール名
        Returns:
            座標辞書
        """
        filepath = self.base_path / f"{module_name}.json"
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def verify_coordinates(self, module_name: str) -> bool:
        """
        座標設定の確認
        Args:
            module_name: モジュール名
        Returns:
            設定済みならTrue
        """
        coords = self.load_coordinates(module_name)
        if not coords or len(coords) <= 1:  # metadataのみの場合
            print(f"✗ {module_name}の座標が設定されていません")
            return False
        
        # メタデータ表示
        if '_metadata' in coords:
            meta = coords['_metadata']
            print(f"\n{module_name}の座標設定:")
            print(f"  最終更新: {meta.get('updated_at', '不明')}")
            print(f"  設定項目数: {meta.get('total_items', len(coords) - 1)}")
            print(f"  画面サイズ: {meta.get('screen_size', '不明')}")
        else:
            print(f"\n{module_name}の座標設定: {len(coords)}項目")
        return True

    def verify_all_coordinates(self):
        """全モジュールの座標設定を確認"""
        print("\n" + "=" * 80)
        print("座標設定の確認")
        print("=" * 80)
        
        modules = ['mercari', 'alibaba', 'spreadsheet', 'listing']
        all_set = True
        
        for module in modules:
            if not self.verify_coordinates(module):
                all_set = False
        
        if all_set:
            print("\n✓ すべてのモジュールの座標が設定されています")
        else:
            print("\n✗ 未設定のモジュールがあります")
            print("  座標設定を実行してください")
        
        return all_set

    def test_coordinates(self):
        """座標のテスト"""
        print("\n" + "=" * 80)
        print("座標テストモード")
        print("=" * 80)
        print("\nテストするモジュールを選択:")
        print("1. メルカリ")
        print("2. アリババ")
        print("3. スプレッドシート")
        print("4. 出品")
        print("0. 戻る")
        
        choice = input("\n選択 (0-4): ")
        
        module_map = {
            "1": "mercari",
            "2": "alibaba", 
            "3": "spreadsheet",
            "4": "listing"
        }
        
        if choice == "0":
            return
        elif choice in module_map:
            module_name = module_map[choice]
            self.test_module_coordinates(module_name)
        else:
            print("無効な選択です")

    def test_module_coordinates(self, module_name: str):
        """特定モジュールの座標をテスト"""
        coords = self.load_coordinates(module_name)
        if not coords:
            print(f"{module_name}の座標が設定されていません")
            return
        
        print(f"\n{module_name}の座標をテストします")
        print("各座標にマウスが移動します")
        print("中断する場合はCtrl+Cを押してください")
        
        # metadataを除く座標のみ取得
        test_coords = {k: v for k, v in coords.items() if k != '_metadata'}
        
        for name, coord in test_coords.items():
            if isinstance(coord, (list, tuple)) and len(coord) == 2:
                print(f"\nテスト: {name} -> {coord}")
                pyautogui.moveTo(coord[0], coord[1], duration=0.5)
                time.sleep(0.5)
            elif isinstance(coord, dict) and 'top_left' in coord:
                # エリア座標の場合
                print(f"\nテスト: {name} (エリア)")
                top_left = coord['top_left']
                bottom_right = coord['bottom_right']
                # 四角形を描くように移動
                pyautogui.moveTo(top_left[0], top_left[1], duration=0.3)
                pyautogui.moveTo(bottom_right[0], top_left[1], duration=0.3)
                pyautogui.moveTo(bottom_right[0], bottom_right[1], duration=0.3)
                pyautogui.moveTo(top_left[0], bottom_right[1], duration=0.3)
                pyautogui.moveTo(top_left[0], top_left[1], duration=0.3)
        
        print(f"\n✓ {module_name}のテスト完了")

    def print_summary(self):
        """設定サマリーを表示"""
        print("\n" + "=" * 80)
        print("座標設定サマリー")
        print("=" * 80)
        
        modules = ['mercari', 'alibaba', 'spreadsheet', 'listing']
        total_items = 0
        
        for module in modules:
            coords = self.load_coordinates(module)
            if coords and '_metadata' in coords:
                items = coords['_metadata'].get('total_items', 0)
                total_items += items
                print(f"{module:15}: {items:3}項目")
            else:
                print(f"{module:15}: 未設定")
        
        print("-" * 30)
        print(f"{'合計':15}: {total_items:3}項目")

# 実行部分
if __name__ == "__main__":
    try:
        print("座標測定ツールを起動します...")
        mapper = CoordinateMapper()
        mapper.start_mapping_session()
    except KeyboardInterrupt:
        print("\n\n座標測定を中断しました")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        sys.exit(1)