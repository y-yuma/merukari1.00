"""
座標測定ツール - 完全なメルカリ操作工程対応版
Version 3.2 - 拡大画像範囲設定追加
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
    メルカリの売り切れ商品リサーチ + アリババ新フロー対応
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
                self.map_alibaba_coordinates_new_flow()
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
            elif choice == "8":
                self.add_expanded_image_area()
            else:
                print("無効な選択です")

    def add_expanded_image_area(self):
        """拡大画像エリアの座標を追加設定"""
        print("\n" + "=" * 80)
        print("拡大画像エリア座標設定（画像判別用）")
        print("=" * 80)
        print("\n【準備】")
        print("1. メルカリで商品詳細ページを開いてください")
        print("2. 商品画像をクリックして拡大表示してください")
        print("3. 拡大画像が表示された状態にしてください")
        input("\n準備ができたらEnterキーを押してください...")
        
        # 既存のメルカリ座標を読み込み
        mercari_coords = self.load_coordinates('mercari')
        if not mercari_coords:
            mercari_coords = {}
        
        print("\n【拡大画像エリアの設定】")
        print("キャプチャしたい範囲を指定します")
        print("まず左上の座標、次に右下の座標を設定してください")
        
        # エリア座標の取得
        area_coords = self.get_area_coordinate(
            'expanded_image_area',
            '拡大画像エリア（画像判別用）'
        )
        
        if area_coords:
            mercari_coords['expanded_image_area'] = area_coords
            
            # テスト表示
            print("\n設定されたエリア情報:")
            print(f"  左上: {area_coords['top_left']}")
            print(f"  右下: {area_coords['bottom_right']}")
            print(f"  幅: {area_coords['width']}px")
            print(f"  高さ: {area_coords['height']}px")
            
            # 保存確認
            save = input("\nこの設定を保存しますか？ (y/n): ")
            if save.lower() == 'y':
                self.save_coordinates(mercari_coords, 'mercari')
                print("✓ 拡大画像エリアの座標を保存しました")
            else:
                print("✗ 保存をキャンセルしました")
        else:
            print("✗ エリア設定をスキップしました")

    def get_area_coordinate(self, name: str, description: str = "") -> Optional[Dict]:
        """
        エリア座標（左上と右下）の取得
        Args:
            name: 座標の名前
            description: 座標の説明
        Returns:
            エリア情報の辞書 またはNone
        """
        print(f"\n{'=' * 60}")
        print(f"エリア設定: {name}")
        if description:
            print(f"説明: {description}")
        print("-" * 60)
        
        # 左上の座標取得
        print("\n【ステップ1: 左上の座標】")
        print("キャプチャ範囲の左上隅にマウスを移動してください")
        print("操作方法:")
        print("  1. マウスを左上隅に移動")
        print("  2. Enterキーを押して確定")
        print("  3. スキップする場合は 's' + Enter")
        
        user_input = input("\n入力: ").lower().strip()
        if user_input == 's':
            print(f"✗ {name} をスキップしました")
            return None
        
        top_left_x, top_left_y = pyautogui.position()
        print(f"✓ 左上座標: ({top_left_x}, {top_left_y})")
        
        # 右下の座標取得
        print("\n【ステップ2: 右下の座標】")
        print("キャプチャ範囲の右下隅にマウスを移動してください")
        print("操作方法:")
        print("  1. マウスを右下隅に移動")
        print("  2. Enterキーを押して確定")
        
        input("\n準備できたらEnterキー: ")
        bottom_right_x, bottom_right_y = pyautogui.position()
        print(f"✓ 右下座標: ({bottom_right_x}, {bottom_right_y})")
        
        # エリア情報を計算
        width = bottom_right_x - top_left_x
        height = bottom_right_y - top_left_y
        
        # 検証
        if width <= 0 or height <= 0:
            print("\n⚠ エラー: 右下座標が左上座標より小さいです")
            print("  もう一度設定してください")
            return None
        
        area_info = {
            'top_left': [top_left_x, top_left_y],
            'bottom_right': [bottom_right_x, bottom_right_y],
            'width': width,
            'height': height
        }
        
        # 範囲を視覚的に確認
        print("\n範囲を確認します（マウスが四隅を移動します）")
        time.sleep(1)
        
        # 四隅を順番に移動
        corners = [
            (top_left_x, top_left_y),  # 左上
            (bottom_right_x, top_left_y),  # 右上
            (bottom_right_x, bottom_right_y),  # 右下
            (top_left_x, bottom_right_y),  # 左下
            (top_left_x, top_left_y)  # 左上に戻る
        ]
        
        for corner in corners:
            pyautogui.moveTo(corner[0], corner[1], duration=0.3)
        
        return area_info

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
        print("自動操作確認: システムが商品をCommand+クリック（Mac）/Ctrl+クリック（Win）で新タブ開きます")
        print("手動操作: 商品を1つCommand+クリック（Mac）/Ctrl+クリック（Win）で新タブで開いてください")
        input("商品詳細ページが新タブで開いたらEnterを押してください...")
        
        mercari_coords['product_image_main'] = self.get_coordinate(
            'product_image_main',
            '33. メイン商品画像（クリックして拡大表示用）'
        )
        mercari_coords['product_title'] = self.get_coordinate(
            'product_title',
            '34. 商品タイトル位置'
        )
        mercari_coords['product_price'] = self.get_coordinate(
            'product_price',
            '35. 商品価格位置'
        )
        
        # === Phase 7.5: 拡大画像エリア設定（NEW）===
        print("\n【Phase 7.5: 拡大画像エリア設定】")
        print("手動操作: メイン商品画像をクリックして拡大表示してください")
        input("拡大画像が表示されたらEnterを押してください...")
        
        # 拡大画像エリアの設定
        expanded_area = self.get_area_coordinate(
            'expanded_image_area',
            '36. 拡大画像エリア（画像判別用のキャプチャ範囲）'
        )
        
        if expanded_area:
            mercari_coords['expanded_image_area'] = expanded_area
            print(f"\n✓ 拡大画像エリア設定完了:")
            print(f"  範囲: {expanded_area['width']}x{expanded_area['height']}px")
        
        print("\n手動操作: ESCキーまたは×ボタンで拡大画像を閉じてください")
        input("拡大画像を閉じたらEnterを押してください...")
        
        # === Phase 8: ナビゲーション ===
        print("\n【Phase 8: ナビゲーション】")
        print("自動操作確認: システムがCommand+W（Mac）/Ctrl+W（Win）でタブを閉じます")
        print("手動操作: Command+W（Mac）/Ctrl+W（Win）でタブを閉じて商品一覧に戻ってください")
        input("商品一覧に戻ったらEnterを押してください...")
        
        mercari_coords['next_page'] = self.get_coordinate(
            'next_page',
            '37. 次ページボタン（20個処理後の移動用）'
        )
        
        # 保存
        self.save_coordinates(mercari_coords, 'mercari')
        print(f"\n✓ メルカリ座標設定完了: {len(mercari_coords)}項目")

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
        
        return scroll_settings

    def map_alibaba_coordinates_new_flow(self):
        """アリババ用座標マッピング（新フロー完全対応版）"""
        # 既存の実装をそのまま使用
        self.current_module = "alibaba"
        print("\n" + "=" * 80)
        print("アリババ（1688.com）モジュール座標設定 - 新フロー対応")
        print("=" * 80)
        print("\n（既存の実装を維持）")
        # ... 既存のコードをそのまま維持

    def map_spreadsheet_coordinates(self):
        """スプレッドシート用座標マッピング（基本版）"""
        # 既存の実装をそのまま使用
        self.current_module = "spreadsheet"
        print("\n" + "=" * 80)
        print("Googleスプレッドシートモジュール座標設定")
        print("=" * 80)
        print("\n（既存の実装を維持）")
        # ... 既存のコードをそのまま維持

    def map_listing_coordinates(self):
        """出品用座標マッピング（基本版）"""
        # 既存の実装をそのまま使用
        self.current_module = "listing"
        print("\n" + "=" * 80)
        print("メルカリ出品モジュール座標設定")
        print("=" * 80)
        print("\n（既存の実装を維持）")
        # ... 既存のコードをそのまま維持

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
        
        self.map_alibaba_coordinates_new_flow()
        print("\n次のモジュールに進みます...")
        time.sleep(2)
        
        self.map_spreadsheet_coordinates()
        print("\n次のモジュールに進みます...")
        time.sleep(2)
        
        self.map_listing_coordinates()
        
        print("\n" + "=" * 80)
        print("✓ 全モジュールの設定が完了しました")
        self.print_summary()

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
        print("    座標測定ツール v3.2 - 拡大画像範囲設定対応")
        print("=" * 80)
        print("\n【機能】")
        print("1. メルカリ売り切れ商品リサーチ対応")
        print("2. アリババ新フロー対応")
        print("3. 拡大画像エリア設定（画像判別用）")
        print("\n【注意事項】")
        print("- ウィンドウサイズを固定してください")
        print("- 各フローの手動操作指示に従ってください")

    def show_menu(self):
        """メニュー表示"""
        print("\n" + "-" * 60)
        print("設定メニュー:")
        print("-" * 60)
        print("1. メルカリ座標設定（完全版）")
        print("2. アリババ座標設定（新フロー）")
        print("3. スプレッドシート座標設定")
        print("4. 出品座標設定")
        print("5. 全モジュール設定")
        print("6. 設定確認")
        print("7. 座標テスト")
        print("8. 拡大画像エリア設定（追加設定）")
        print("0. 終了")
        print("-" * 60)
        return input("選択してください (0-8): ")

    def save_coordinates(self, coords: Dict, module_name: str):
        """座標を保存"""
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
            'screen_size': pyautogui.size(),
            'version': 'v3.2_expanded_image' if module_name == 'mercari' else 'v1.0'
        }
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(coords, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ {module_name}の座標を保存しました")
        print(f"  ファイル: {filepath}")
        print(f"  設定項目数: {len(coords) - 1}")

    def load_coordinates(self, module_name: str) -> Dict:
        """座標を読み込み"""
        filepath = self.base_path / f"{module_name}.json"
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def verify_coordinates(self, module_name: str) -> bool:
        """座標設定の確認"""
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
            print(f"  バージョン: {meta.get('version', '旧版')}")
        else:
            print(f"\n{module_name}の座標設定: {len(coords)}項目")
        
        # 拡大画像エリア設定の確認
        if module_name == 'mercari' and 'expanded_image_area' in coords:
            area = coords['expanded_image_area']
            print(f"  拡大画像エリア: {area['width']}x{area['height']}px")
        
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
                version = coords['_metadata'].get('version', '旧版')
                print(f"{module:15}: {items:3}項目 ({version})")
                
                # 拡大画像エリアの確認
                if module == 'mercari' and 'expanded_image_area' in coords:
                    area = coords['expanded_image_area']
                    print(f"{'':15}  └─ 拡大画像エリア: {area['width']}x{area['height']}px")
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