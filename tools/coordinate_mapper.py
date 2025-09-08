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
                self.map_mercari_coordinates_flexible()
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

    def map_mercari_coordinates_flexible(self):
        """メルカリ用座標マッピング（柔軟設定版）"""
        self.current_module = "mercari"
        print("\n" + "=" * 80)
        print("メルカリモジュール座標設定（柔軟設定モード）")
        print("=" * 80)
        print("\nメルカリのページを開いて準備してください")
        print("このモードでは設定項目を自由にカスタマイズできます")
        input("準備ができたらEnterキーを押してください...")
        
        mercari_coords = {}
        
        # 既存設定の確認
        existing_coords = self.load_coordinates('mercari')
        if existing_coords and len(existing_coords) > 1:
            print(f"\n既存の設定が見つかりました（{len(existing_coords)-1}項目）")
            use_existing = input("既存設定をベースにしますか？ (y/n): ").lower()
            if use_existing == 'y':
                mercari_coords = existing_coords.copy()
                print("既存設定を読み込みました")
        
        # 設定項目の管理
        setting_items = self.manage_setting_items()
        
        # フロー確認
        self.confirm_setting_flow(setting_items)
        
        # 座標設定実行
        mercari_coords = self.execute_flexible_coordinate_setting(setting_items, mercari_coords)
        
        # 保存
        self.save_coordinates(mercari_coords, 'mercari')
        print(f"\n✓ メルカリ座標設定完了: {len(mercari_coords)}項目")

    def manage_setting_items(self):
        """設定項目の管理"""
        print("\n" + "=" * 60)
        print("設定項目の管理")
        print("=" * 60)
        
        # デフォルト設定項目
        default_items = [
            {'id': 'logo', 'name': 'メルカリロゴ', 'category': 'basic'},
            {'id': 'search_bar', 'name': '検索バー', 'category': 'basic'},
            {'id': 'category_button', 'name': 'カテゴリーボタン', 'category': 'category'},
            {'id': 'all_categories_button', 'name': 'すべてボタン', 'category': 'category'},
            {'id': 'category_electronics', 'name': '家電・スマホ・カメラ', 'category': 'category'},
            {'id': 'category_pc_tablet', 'name': 'PC/タブレット', 'category': 'category'},
            {'id': 'category_pc_accessories', 'name': 'PC周辺機器', 'category': 'category'},
            {'id': 'filter_button', 'name': '詳細検索ボタン', 'category': 'filter'},
            {'id': 'condition_new', 'name': '新品・未使用', 'category': 'filter'},
            {'id': 'price_min', 'name': '最低価格入力欄', 'category': 'filter'},
            {'id': 'price_max', 'name': '最高価格入力欄', 'category': 'filter'},
            {'id': 'search_button', 'name': '検索実行ボタン', 'category': 'filter'},
            {'id': 'product_grid_1', 'name': '商品1番目', 'category': 'product'},
            {'id': 'product_grid_2', 'name': '商品2番目', 'category': 'product'},
            {'id': 'product_grid_3', 'name': '商品3番目', 'category': 'product'},
            {'id': 'product_title', 'name': '商品タイトル', 'category': 'detail'},
            {'id': 'product_price', 'name': '商品価格', 'category': 'detail'},
            {'id': 'product_image_main', 'name': 'メイン商品画像', 'category': 'detail'},
            {'id': 'seller_name', 'name': '販売者名', 'category': 'detail'},
        ]
        
        print("デフォルト設定項目:")
        for i, item in enumerate(default_items, 1):
            print(f"{i:2d}. [{item['category']}] {item['name']} ({item['id']})")
        
        print("\n設定項目のカスタマイズ:")
        print("1. デフォルト設定をそのまま使用")
        print("2. 項目を選択して設定")
        print("3. 項目を追加・削除・順序変更")
        
        choice = input("\n選択 (1-3): ")
        
        if choice == "1":
            return default_items
        elif choice == "2":
            return self.select_items_from_default(default_items)
        elif choice == "3":
            return self.customize_items(default_items)
        else:
            print("無効な選択です。デフォルト設定を使用します。")
            return default_items

    def select_items_from_default(self, default_items):
        """デフォルト項目から選択"""
        print("\n設定したい項目を選択してください（複数選択可）:")
        print("例: 1,3,5-8,10  または  all")
        
        selection = input("\n選択: ").strip()
        
        if selection.lower() == 'all':
            return default_items
        
        selected_items = []
        try:
            # 選択範囲の解析
            parts = selection.split(',')
            indices = set()
            
            for part in parts:
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    indices.update(range(start-1, end))
                else:
                    indices.add(int(part)-1)
            
            for i in sorted(indices):
                if 0 <= i < len(default_items):
                    selected_items.append(default_items[i])
            
        except ValueError:
            print("入力形式が不正です。デフォルト設定を使用します。")
            return default_items
        
        print(f"\n選択された項目: {len(selected_items)}個")
        for item in selected_items:
            print(f"  - {item['name']}")
        
        return selected_items

    def customize_items(self, default_items):
        """項目のカスタマイズ"""
        print("\n" + "=" * 60)
        print("項目カスタマイズモード")
        print("=" * 60)
        
        items = default_items.copy()
        
        while True:
            print(f"\n現在の設定項目 ({len(items)}個):")
            for i, item in enumerate(items, 1):
                print(f"{i:2d}. [{item['category']}] {item['name']}")
            
            print("\nカスタマイズオプション:")
            print("1. 項目を追加")
            print("2. 項目を削除")
            print("3. 項目の順序を変更")
            print("4. 項目を挿入")
            print("5. 設定完了")
            
            choice = input("\n選択 (1-5): ")
            
            if choice == "1":
                items = self.add_custom_item(items)
            elif choice == "2":
                items = self.remove_item(items)
            elif choice == "3":
                items = self.reorder_items(items)
            elif choice == "4":
                items = self.insert_item(items)
            elif choice == "5":
                break
            else:
                print("無効な選択です")
        
        return items

    def add_custom_item(self, items):
        """カスタム項目の追加"""
        print("\n新しい項目を追加:")
        item_id = input("項目ID (英数字): ").strip()
        item_name = input("項目名: ").strip()
        
        categories = ['basic', 'category', 'filter', 'product', 'detail', 'custom']
        print("カテゴリー:", ", ".join(categories))
        item_category = input("カテゴリー: ").strip()
        
        if item_category not in categories:
            item_category = 'custom'
        
        new_item = {
            'id': item_id,
            'name': item_name,
            'category': item_category
        }
        
        items.append(new_item)
        print(f"項目 '{item_name}' を追加しました")
        return items

    def remove_item(self, items):
        """項目の削除"""
        if not items:
            print("削除する項目がありません")
            return items
        
        try:
            index = int(input("削除する項目番号: ")) - 1
            if 0 <= index < len(items):
                removed = items.pop(index)
                print(f"項目 '{removed['name']}' を削除しました")
            else:
                print("無効な番号です")
        except ValueError:
            print("数値を入力してください")
        
        return items

    def insert_item(self, items):
        """項目の挿入"""
        print("\n項目を挿入:")
        try:
            position = int(input("挿入位置 (1からの番号): ")) - 1
            if position < 0:
                position = 0
            elif position > len(items):
                position = len(items)
            
            item_id = input("項目ID: ").strip()
            item_name = input("項目名: ").strip()
            item_category = input("カテゴリー: ").strip() or 'custom'
            
            new_item = {
                'id': item_id,
                'name': item_name,
                'category': item_category
            }
            
            items.insert(position, new_item)
            print(f"項目 '{item_name}' を位置 {position+1} に挿入しました")
            
        except ValueError:
            print("無効な入力です")
        
        return items

    def reorder_items(self, items):
        """項目の順序変更"""
        print("\n順序変更:")
        print("移動したい項目番号と移動先を指定")
        
        try:
            from_index = int(input("移動元番号: ")) - 1
            to_index = int(input("移動先番号: ")) - 1
            
            if 0 <= from_index < len(items) and 0 <= to_index < len(items):
                item = items.pop(from_index)
                items.insert(to_index, item)
                print(f"項目 '{item['name']}' を移動しました")
            else:
                print("無効な番号です")
        except ValueError:
            print("数値を入力してください")
        
        return items

    def confirm_setting_flow(self, items):
        """設定フローの確認"""
        print("\n" + "=" * 60)
        print("設定フローの確認")
        print("=" * 60)
        print("以下の順序で座標設定を行います:")
        
        for i, item in enumerate(items, 1):
            print(f"{i:2d}. {item['name']} ({item['id']})")
        
        print(f"\n合計 {len(items)} 項目の設定を行います")
        
        confirm = input("\nこの順序で設定を開始しますか？ (y/n): ").lower()
        if confirm != 'y':
            print("設定をキャンセルしました")
            return False
        
        return True

    def execute_flexible_coordinate_setting(self, items, existing_coords):
        """柔軟な座標設定の実行"""
        coords = existing_coords.copy() if existing_coords else {}
        
        print("\n" + "=" * 60)
        print("座標設定開始")
        print("=" * 60)
        
        for i, item in enumerate(items, 1):
            print(f"\n--- 進捗: {i}/{len(items)} ---")
            
            # 既存設定の確認
            if item['id'] in coords and coords[item['id']]:
                print(f"既存設定: {item['name']} = {coords[item['id']]}")
                update = input("再設定しますか？ (y/n/s=スキップ): ").lower()
                if update == 's':
                    continue
                elif update != 'y':
                    continue
            
            # 座標設定
            coord = self.get_coordinate_with_options(item)
            
            if coord == 'BACK' and i > 1:
                # 前の項目に戻る
                prev_item = items[i-2]
                print(f"前の項目 '{prev_item['name']}' に戻ります")
                i -= 2
                continue
            elif coord == 'SKIP':
                print(f"項目 '{item['name']}' をスキップしました")
                continue
            elif coord:
                coords[item['id']] = coord
                print(f"✓ {item['name']}: {coord}")
        
        return coords

    def get_coordinate_with_options(self, item):
        """オプション付き座標取得"""
        print(f"\n{'=' * 60}")
        print(f"設定項目: {item['name']}")
        print(f"ID: {item['id']}")
        print(f"カテゴリー: {item['category']}")
        print("-" * 60)
        print("操作方法:")
        print("  Enter: 現在位置で座標取得")
        print("  t: 3秒後に座標取得")
        print("  s: スキップ")
        print("  r: やり直し")
        print("  b: 前の項目に戻る")
        print("  p: 一時停止（ブラウザ操作の時間）")
        print("  h: ヘルプ表示")
        
        while True:
            user_input = input("\n入力: ").lower().strip()
            
            if user_input == '' or user_input == 'enter':
                x, y = pyautogui.position()
                return (x, y)
            elif user_input == 't':
                print("\n3秒後に座標を取得します...")
                for i in range(3, 0, -1):
                    print(f"{i}...")
                    time.sleep(1)
                x, y = pyautogui.position()
                return (x, y)
            elif user_input == 's':
                return 'SKIP'
            elif user_input == 'r':
                print("やり直します...")
                continue
            elif user_input == 'b':
                return 'BACK'
            elif user_input == 'p':
                print("\n【一時停止】")
                print("ブラウザで必要な操作を行ってください")
                print("（例：プルダウンを開く、ページを移動など）")
                input("操作完了後、Enterキーを押してください...")
                continue
            elif user_input == 'h':
                self.show_coordinate_help()
                continue
            else:
                print("無効な入力です。'h'でヘルプを表示")
                continue

    def show_coordinate_help(self):
        """座標設定ヘルプ"""
        print("\n" + "=" * 40)
        print("座標設定ヘルプ")
        print("=" * 40)
        print("Enter: 現在のマウス位置で座標を記録")
        print("t: 3秒のカウントダウン後に座標記録")
        print("s: この項目をスキップ")
        print("r: この項目をやり直し")
        print("b: 前の項目に戻る")
        print("p: 一時停止してブラウザ操作")
        print("h: このヘルプを表示")
        print("-" * 40)

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
        """メルカリ用座標マッピング（改良版）"""
        self.current_module = "mercari"
        print("\n" + "=" * 80)
        print("メルカリモジュール座標設定")
        print("=" * 80)
        print("\nメルカリのページを開いて準備してください")
        print("注意：カテゴリー選択では段階的な操作が必要です")
        input("準備ができたらEnterキーを押してください...")
        
        mercari_coords = {}
        coordinate_history = []  # 設定履歴を保持
        
        # 基本要素の設定
        basic_elements = [
            ('logo', 'メルカリロゴ（ホームに戻る用）'),
            ('search_bar', '検索バー（使用しないが位置確認用）'),
        ]
        
        for element_id, description in basic_elements:
            coord = self.get_coordinate_with_history(element_id, description, coordinate_history)
            if coord and coord != 'BACK':
                mercari_coords[element_id] = coord
            elif coord == 'BACK' and coordinate_history:
                # 前の項目に戻る
                last_item = coordinate_history.pop()
                if last_item in mercari_coords:
                    del mercari_coords[last_item]
                continue
        
        # カテゴリー設定（段階的操作対応）
        print("\n【カテゴリー設定 - 段階的操作】")
        print("カテゴリー選択は複数ステップが必要な場合があります")
        print("例：カテゴリーボタン → 大カテゴリー → サブカテゴリー表示 → 中カテゴリー選択")
        
        # カテゴリーボタンの基本設定
        mercari_coords['category_button'] = self.get_coordinate_with_guidance(
            'category_button',
            'カテゴリーボタンの位置',
            "メインページのカテゴリーボタンをクリックしてください"
        )
        
        # 大カテゴリーの段階的設定
        print("\n【大カテゴリー設定】")
        categories_level1 = [
            ('category_electronics', '家電・スマホ・カメラ'),
            ('category_toys', 'おもちゃ・ホビー・グッズ'),
            ('category_sports', 'スポーツ・レジャー'),
        ]
        
        for cat_id, cat_name in categories_level1:
            print(f"\n--- {cat_name} の設定 ---")
            print("手順：")
            print("1. カテゴリーボタンをクリック")
            print(f"2. '{cat_name}' を選択")
            print("3. 必要に応じてサブカテゴリーが表示されるまで待機")
            
            coord = self.get_coordinate_with_manual_steps(cat_id, cat_name)
            if coord:
                mercari_coords[cat_id] = coord
        
        # 中カテゴリー設定
        print("\n【中カテゴリー設定】")
        print("注意：大カテゴリーを選択した後に表示される項目です")
        
        categories_level2 = [
            ('category_pc_tablet', 'PC/タブレット（家電・スマホ・カメラ内）'),
            ('category_toys_general', 'おもちゃ（おもちゃ・ホビー・グッズ内）'),
            ('category_training', 'トレーニング/エクササイズ（スポーツ・レジャー内）'),
        ]
        
        for cat_id, cat_name in categories_level2:
            coord = self.get_coordinate_with_manual_steps(cat_id, cat_name)
            if coord:
                mercari_coords[cat_id] = coord
        
        # フィルター設定（簡略化）
        print("\n【フィルター設定】")
        filter_elements = [
            ('filter_button', '詳細検索ボタン'),
            ('condition_new', '新品・未使用チェックボックス'),
            ('price_min', '最低価格入力欄'),
            ('price_max', '最高価格入力欄'),
            ('search_button', '検索実行ボタン'),
        ]
        
        for element_id, description in filter_elements:
            coord = self.get_coordinate_with_guidance(element_id, description)
            if coord:
                mercari_coords[element_id] = coord
        
        # 商品グリッド（最初の5個のみ設定）
        print("\n【商品グリッド設定】")
        print("検索結果画面で商品の位置を設定します")
        
        for i in range(1, 6):  # 最初の5個のみ
            coord = self.get_coordinate_with_guidance(
                f'product_grid_{i}',
                f'{i}番目の商品位置',
                f"検索結果の{i}番目の商品をクリックしてください"
            )
            if coord:
                mercari_coords[f'product_grid_{i}'] = coord
        
        # 商品詳細ページ要素
        print("\n【商品詳細ページ要素】")
        detail_elements = [
            ('product_title', '商品タイトル位置'),
            ('product_price', '商品価格位置'),
            ('product_image_main', 'メイン商品画像の中心'),
            ('seller_name', '販売者名表示位置'),
        ]
        
        for element_id, description in detail_elements:
            coord = self.get_coordinate_with_guidance(element_id, description)
            if coord:
                mercari_coords[element_id] = coord
        
        # 保存
        self.save_coordinates(mercari_coords, 'mercari')
        print(f"\n✓ メルカリ座標設定完了: {len(mercari_coords)}項目")

    def get_coordinate_with_guidance(self, name: str, description: str, guidance: str = "") -> Optional[Tuple[int, int]]:
        """ガイダンス付き座標取得"""
        print(f"\n{'=' * 60}")
        print(f"設定項目: {name}")
        print(f"説明: {description}")
        if guidance:
            print(f"手順: {guidance}")
        print("-" * 60)
        
        return self.get_coordinate(name, description)

    def get_coordinate_with_manual_steps(self, name: str, description: str) -> Optional[Tuple[int, int]]:
        """手動ステップ付き座標取得"""
        print(f"\n{'=' * 60}")
        print(f"設定項目: {name}")
        print(f"説明: {description}")
        print("-" * 60)
        print("【重要】複数ステップが必要な可能性があります")
        print("  p: 一時停止して手動操作")
        print("  m: 複数座標モード")
        print("  通常通り座標を設定する場合はそのまま進んでください")
        
        return self.get_coordinate(name, description)

    def get_coordinate_with_history(self, name: str, description: str, history: list) -> Optional[Tuple[int, int]]:
        """履歴管理付き座標取得"""
        result = self.get_coordinate(name, description)
        if result and result != 'BACK':
            history.append(name)
        return result

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