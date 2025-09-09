"""
座標測定ツール - 完全なメルカリ操作工程対応版
Version 3.0 - 売り切れ商品リサーチ対応 + スクロール設定機能追加
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
    メルカリの売り切れ商品リサーチに特化した座標管理
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
                self.map_mercari_coordinates_complete()
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

    def map_mercari_coordinates_complete(self):
        """メルカリ用座標マッピング（完全版）- 売り切れ商品リサーチ対応"""
        self.current_module = "mercari"
        print("\n" + "=" * 80)
        print("メルカリモジュール座標設定（売り切れ商品リサーチ対応）")
        print("=" * 80)
        print("\nメルカリのトップページを開いて準備してください")
        print("注意：売り切れ商品のみを表示する設定で進めます")
        input("準備ができたらEnterキーを押してください...")
        
        mercari_coords = {}
        
        # === Phase 1: 基本ナビゲーション ===
        print("\n【Phase 1: 基本ナビゲーション】")
        mercari_coords['logo'] = self.get_coordinate(
            'logo',
            '0. メルカリロゴ（ホームに戻る用）'
        )
        mercari_coords['search_bar'] = self.get_coordinate(
            'search_bar',
            '1. 検索ボタン（検索ページ表示用）'
        )
        
        # === Phase 2: カテゴリー選択 ===
        print("\n【Phase 2: カテゴリー選択】")
        mercari_coords['category_button'] = self.get_coordinate(
            'category_button',
            '2. カテゴリーボタンの位置'
        )
        
        print("\n手動操作: カテゴリーボタンをクリックしてメニューを開いてください")
        input("カテゴリーメニューが開いたらEnterを押してください...")
        
        mercari_coords['all_categories_button'] = self.get_coordinate(
            'all_categories_button',
            '3. 全て（最初のボタン）'
        )
        
        print("\n手動操作: 「全て」をクリックしてください")
        input("次の画面が表示されたらEnterを押してください...")
        
        mercari_coords['category_smartphone_tablet_pc'] = self.get_coordinate(
            'category_smartphone_tablet_pc',
            '4. スマホ・タブレット・パソコン'
        )
        
        print("\n手動操作: 「スマホ・タブレット・パソコン」をクリックしてください")
        input("サブカテゴリーが表示されたらEnterを押してください...")
        
        mercari_coords['category_all_second'] = self.get_coordinate(
            'category_all_second',
            '5. カテゴリー全て（2回目のボタン）'
        )
        
        print("\n手動操作: 「カテゴリー全て」をクリックしてください")
        input("PC周辺機器が表示されたらEnterを押してください...")
        
        mercari_coords['category_pc_accessories'] = self.get_coordinate(
            'category_pc_accessories',
            '6. PC周辺機器'
        )
        
        # === Phase 3: フィルター設定 ===
        print("\n【Phase 3: フィルター設定】")
        print("手動操作: PC周辺機器をクリックして検索結果ページに移動してください")
        input("検索結果ページが表示されたらEnterを押してください...")
        
        mercari_coords['sold_filter'] = self.get_coordinate(
            'sold_filter',
            '7. 販売状況（フィルターメニュー）'
        )
        
        print("\n手動操作: 販売状況をクリックしてメニューを開いてください")
        input("販売状況メニューが開いたらEnterを押してください...")
        
        mercari_coords['sold_out_checkbox'] = self.get_coordinate(
            'sold_out_checkbox',
            '8. 売り切れ（チェックボックス）'
        )
        
        mercari_coords['condition_filter'] = self.get_coordinate(
            'condition_filter',
            '9. 商品の状態（フィルターメニュー）'
        )
        
        print("\n手動操作: 商品の状態をクリックしてメニューを開いてください")
        input("商品の状態メニューが開いたらEnterを押してください...")
        
        mercari_coords['condition_new'] = self.get_coordinate(
            'condition_new',
            '10. 新品・未使用（チェックボックス）'
        )
        
        mercari_coords['sort_order'] = self.get_coordinate(
            'sort_order',
            '11. 順番変更（並び順ボタン）'
        )
        
        print("\n手動操作: 順番変更をクリックしてメニューを開いてください")
        input("並び順メニューが開いたらEnterを押してください...")
        
        mercari_coords['sort_newest'] = self.get_coordinate(
            'sort_newest',
            '12. 新しい順（並び順選択）'
        )
        
        mercari_coords['search_button'] = self.get_coordinate(
            'search_button',
            '13. 検索実行ボタン（フィルター適用後にクリック）'
        )
        
        # === Phase 4: 商品グリッド（1-10番目）===
        print("\n【Phase 4: 商品グリッド（1-10番目）】")
        print("手動操作: 売り切れ・新品・新しい順の条件で検索結果を表示してください")
        input("商品一覧が表示されたらEnterを押してください...")
        
        for i in range(1, 11):
            mercari_coords[f'product_grid_{i}'] = self.get_coordinate(
                f'product_grid_{i}',
                f'{13+i}. 商品{i}番目の位置'
            )
        
        # === Phase 5: スクロール処理とスクロール設定 ===
        print("\n【Phase 5: スクロール処理とスクロール設定】")
        mercari_coords['scroll_position'] = self.get_coordinate(
            'scroll_position',
            'スクロール基準位置（10個表示後のスクロール用）'
        )
        
        # スクロール設定をテスト
        scroll_settings = self.test_scroll_settings()
        mercari_coords['scroll_settings'] = scroll_settings
        
        print("\n手動操作: ページを下にスクロールして次の商品を表示してください")
        input("11-20番目の商品が表示されたらEnterを押してください...")
        
        # === Phase 6: 商品グリッド（11-20番目）===
        print("\n【Phase 6: 商品グリッド（11-20番目）】")
        for i in range(11, 21):
            mercari_coords[f'product_grid_{i}'] = self.get_coordinate(
                f'product_grid_{i}',
                f'{13+i}. 商品{i}番目の位置（スクロール後）'
            )
        
        # === Phase 7: 商品詳細ページ ===
        print("\n【Phase 7: 商品詳細ページ】")
        print("手動操作: 商品をCtrl+クリックで新タブで開いてください")
        input("商品詳細ページが新タブで開いたらEnterを押してください...")
        
        mercari_coords['product_image_main'] = self.get_coordinate(
            'product_image_main',
            '33. メイン商品画像（画像判別用）'
        )
        mercari_coords['product_title'] = self.get_coordinate(
            'product_title',
            '34. 商品タイトル位置'
        )
        mercari_coords['product_price'] = self.get_coordinate(
            'product_price',
            '35. 商品価格位置'
        )
        
        # === Phase 8: ナビゲーション ===
        print("\n【Phase 8: ナビゲーション】")
        print("手動操作: タブを閉じて商品一覧に戻ってください")
        input("商品一覧に戻ったらEnterを押してください...")
        
        mercari_coords['next_page'] = self.get_coordinate(
            'next_page',
            '36. 次ページボタン（20個処理後の移動用）'
        )
        
        # 保存
        self.save_coordinates(mercari_coords, 'mercari')
        print(f"\n✓ メルカリ座標設定完了: {len(mercari_coords)}項目")
        print("設定された工程:")
        print("  - 基本ナビゲーション: 3項目")
        print("  - カテゴリー選択: 4項目") 
        print("  - フィルター設定: 7項目")
        print("  - 商品グリッド: 21項目")
        print("  - 商品詳細: 3項目")
        print("  - ナビゲーション: 1項目")
        print("  - スクロール設定: 1項目")

    def test_scroll_settings(self) -> Dict:
        """
        スクロール設定のテスト
        Returns:
            スクロール設定の辞書
        """
        print("\n" + "=" * 60)
        print("スクロール設定テスト")
        print("=" * 60)
        print("商品一覧ページでスクロール量を調整します")
        print("マウス/パッドの違いを考慮して最適な値を設定してください")
        input("\n準備完了後、Enterを押してください...")
        
        # テスト用座標取得（現在のマウス位置）
        test_x, test_y = pyautogui.position()
        print(f"テスト位置: ({test_x}, {test_y})")
        
        # 初回スクロールテスト
        print("\n【初回スクロールテスト（1-10から11-20へ移動用）】")
        print("軽めのスクロールを設定します")
        first_scroll = None
        for amount in [-300, -400, -500, -600]:
            print(f"\nスクロール量: {amount}px をテスト中...")
            print("3秒後にスクロールします")
            time.sleep(3)
            
            pyautogui.moveTo(test_x, test_y)
            time.sleep(0.3)
            pyautogui.scroll(amount)
            time.sleep(1)
            
            choice = input("この量で11-20番目の商品が見えますか？ (y/n): ")
            if choice.lower() == 'y':
                first_scroll = amount
                print(f"✓ 初回スクロール量: {amount}px に設定")
                break
        
        if first_scroll is None:
            first_scroll = -400  # デフォルト値
            print(f"デフォルト値を使用: {first_scroll}px")
        
        # 元の位置に戻る
        print("\n元の位置に戻すため、逆方向にスクロールします...")
        pyautogui.scroll(-first_scroll)
        time.sleep(2)
        
        # 通常スクロールテスト
        print("\n【通常スクロールテスト（ページ移動用）】")
        print("強めのスクロールを設定します")
        regular_scroll = None
        for amount in [-500, -600, -700, -800]:
            print(f"\nスクロール量: {amount}px をテスト中...")
            print("3秒後にスクロールします")
            time.sleep(3)
            
            pyautogui.moveTo(test_x, test_y)
            time.sleep(0.3)
            pyautogui.scroll(amount)
            time.sleep(1)
            
            choice = input("この量で次ページの商品が見えるようになりますか？ (y/n): ")
            if choice.lower() == 'y':
                regular_scroll = amount
                print(f"✓ 通常スクロール量: {amount}px に設定")
                break
        
        if regular_scroll is None:
            regular_scroll = -600  # デフォルト値
            print(f"デフォルト値を使用: {regular_scroll}px")
        
        # スクロール回数設定
        print("\n【スクロール回数設定】")
        print("初回スクロール回数（デフォルト: 2回）")
        try:
            first_count = int(input("回数を入力 (1-5, デフォルト2): ") or "2")
            if first_count < 1 or first_count > 5:
                first_count = 2
        except:
            first_count = 2
        
        print("通常スクロール回数（デフォルト: 3回）")
        try:
            regular_count = int(input("回数を入力 (1-5, デフォルト3): ") or "3")
            if regular_count < 1 or regular_count > 5:
                regular_count = 3
        except:
            regular_count = 3
        
        scroll_settings = {
            'first_scroll': first_scroll,
            'regular_scroll': regular_scroll,
            'scroll_count_first': first_count,
            'scroll_count_regular': regular_count
        }
        
        print("\n✓ スクロール設定完了:")
        print(f"  初回スクロール: {first_scroll}px × {first_count}回")
        print(f"  通常スクロール: {regular_scroll}px × {regular_count}回")
        
    def get_area_coordinates(self, name: str, description: str = "") -> Optional[Dict]:
        """
        エリア座標の取得（左上と右下の2点で範囲指定）
        Args:
            name: 座標の名前
            description: 座標の説明
        Returns:
            エリア座標の辞書またはNone
        """
        print(f"\n{'=' * 60}")
        print(f"エリア設定: {name}")
        if description:
            print(f"説明: {description}")
        print("-" * 60)
        print("操作方法:")
        print("  1. まず左上角にマウスを移動してEnterを押す")
        print("  2. 次に右下角にマウスを移動してEnterを押す")
        print("  3. スキップする場合は 's' + Enter")
        
        user_input = input("\n左上角の設定を開始しますか？ (Enter/s): ").lower().strip()
        
        if user_input == 's':
            print(f"✗ {name} をスキップしました")
            return None
        
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

    def print_header(self):
        """ヘッダー表示"""
        print("=" * 80)
        print("    座標測定ツール v3.0 - 売り切れ商品リサーチ対応")
        print("=" * 80)
        print("\n【使い方】")
        print("1. メルカリの売り切れ商品リサーチに特化した座標設定")
        print("2. 商品グリッド1-20個、スクロール処理、画像判別に対応")
        print("3. 各フェーズごとに手動操作の指示に従ってください")
        print("\n【注意事項】")
        print("- ウィンドウサイズを固定してください")
        print("- 売り切れ商品のみを対象とした操作フローです")

    def show_menu(self):
        """メニュー表示"""
        print("\n" + "-" * 60)
        print("設定メニュー:")
        print("-" * 60)
        print("1. メルカリ座標設定（完全版）")
        print("2. アリババ座標設定")
        print("3. スプレッドシート座標設定")
        print("4. 出品座標設定")
        print("5. 全モジュール設定")
        print("6. 設定確認")
        print("7. 座標テスト")
        print("0. 終了")
        print("-" * 60)
        return input("選択してください (0-7): ")

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
        print("これには約30-45分かかる場合があります")
        confirm = input("\n続行しますか？ (y/n): ")
        if confirm.lower() != 'y':
            print("キャンセルしました")
            return
        
        self.map_mercari_coordinates_complete()
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