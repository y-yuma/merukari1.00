# tools/coordinate_mapper.py
"""
座標測定ツール - 各モジュールごとに座標を設定可能
Version 2.0 - モジュール別管理対応
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional, Any

import pyautogui
# 計画では keyboard を使う例がありますが、ここでは input() 駆動です（Mac可）。
# import keyboard  # not required

class CoordinateMapper:
    """
    座標マッピングツール
    各モジュールの画面要素の座標を記録・管理
    """

    def __init__(self):
        """初期化処理"""
        self.coordinates: Dict[str, Any] = {}
        self.current_module: Optional[str] = None
        self.base_path = Path("config/coordinate_sets")
        self.base_path.mkdir(parents=True, exist_ok=True)

        # PyAutoGUIの安全設定
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5

    # --------- セッション/UI ---------
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
                module = input("テストするモジュール名を入力してください（mercari/alibaba/spreadsheet/listing）: ").strip()
                if module:
                    self.test_coordinates(module)
            else:
                print("無効な選択です")

    def print_header(self):
        """ヘッダー表示"""
        print("=" * 80)
        print("  座標測定ツール v2.0 - メルカリ自動化システム")
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

    def show_menu(self) -> str:
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
        return input("選択してください (0-7): ").strip()

    # --------- 取得系 ---------
    def get_coordinate(self, name: str, description: str = "") -> Optional[Tuple[int, int]]:
        """
        単一座標の取得

        Args:
            name: 座標の名前
            description: 座標の説明

        Returns:
            座標のタプル (x, y) または None
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
        print("  4. 3秒後に自動取得する場合は 't' + Enter")

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

    def get_area_coordinates(self, name: str, description: str = "") -> Optional[Dict]:
        """
        エリア座標の取得（左上と右下）
        Returns: {"top_left": (x, y), "bottom_right": (x, y), "width": w, "height": h}
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
            "height": bottom_right[1] - top_left[1],
        }

    # --------- 保存/読取 ---------
    def _serialize_coords(self, coords: Dict[str, Any]) -> Dict[str, Any]:
        """JSON保存可能な形に変換（tuple→list）"""
        def conv(v):
            if isinstance(v, tuple):
                return list(v)
            if isinstance(v, dict):
                return {k: conv(val) for k, val in v.items()}
            return v
        return {k: conv(v) for k, v in coords.items()}

    def save_coordinates(self, coords: Dict[str, Any], module_name: str):
        """座標ファイル保存 + メタデータ付与"""
        data = self._serialize_coords(coords)
        total_items = sum(
            1 for k, v in data.items()
            if (isinstance(v, (list, tuple)) and len(v) == 2) or (isinstance(v, dict) and 'top_left' in v)
        )
        data["_metadata"] = {
            "module": module_name,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_items": total_items,
        }
        out = self.base_path / f"{module_name}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 保存しました: {out}（{total_items}項目）")

    def load_coordinates(self, module_name: str) -> Optional[Dict[str, Any]]:
        """座標ファイル読取"""
        p = self.base_path / f"{module_name}.json"
        if not p.exists():
            return None
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)

    # --------- 個別モジュール設定 ---------
    def map_mercari_coordinates(self):
        """メルカリ用座標マッピング（詳細版）"""
        self.current_module = "mercari"
        print("\n" + "=" * 80)
        print("メルカリモジュール座標設定")
        print("=" * 80)
        print("\nメルカリのページを開いて準備してください")
        input("準備ができたらEnterキーを押してください...")

        mercari_coords: Dict[str, Any] = {}

        # トップページ要素
        print("\n【トップページ要素】")
        mercari_coords['logo'] = self.get_coordinate('logo', 'メルカリロゴ（ホームに戻る用）')
        mercari_coords['search_bar'] = self.get_coordinate('search_bar', '検索バー（使用しないが位置確認用）')

        # カテゴリー関連
        print("\n【カテゴリー設定】")
        mercari_coords['category_button'] = self.get_coordinate('category_button', 'カテゴリーボタンの位置')

        # 大カテゴリ（例）
        print("\n【大カテゴリー（第1階層）】")
        categories_level1 = [
            ('category_electronics', '家電・スマホ・カメラ'),
            ('category_toys', 'おもちゃ・ホビー・グッズ'),
            ('category_sports', 'スポーツ・レジャー'),
            ('category_mens', 'メンズ'),
            ('category_ladies', 'レディース'),
            ('category_baby', 'ベビー・キッズ'),
        ]
        for cat_id, cat_name in categories_level1:
            mercari_coords[cat_id] = self.get_coordinate(cat_id, cat_name)

        # 中カテゴリ（例）
        print("\n【中カテゴリー（第2階層）】")
        categories_level2 = [
            ('category_pc_tablet', 'PC/タブレット'),
            ('category_smartphone', 'スマートフォン本体'),
            ('category_camera', 'カメラ'),
            ('category_toys_general', 'おもちゃ'),
            ('category_character', 'キャラクターグッズ'),
            ('category_training', 'トレーニング/エクササイズ'),
        ]
        for cat_id, cat_name in categories_level2:
            mercari_coords[cat_id] = self.get_coordinate(cat_id, cat_name)

        # 小カテゴリ（例）
        print("\n【小カテゴリー（第3階層）】")
        categories_level3 = [
            ('category_pc_accessories', 'PC周辺機器'),
            ('category_tablet_accessories', 'タブレット'),
            ('category_smartphone_accessories', 'スマホアクセサリー'),
            ('category_training_goods', 'トレーニング用品'),
            ('category_yoga', 'ヨガ'),
            ('category_running', 'ランニング'),
        ]
        for cat_id, cat_name in categories_level3:
            mercari_coords[cat_id] = self.get_coordinate(cat_id, cat_name)

        # フィルター
        print("\n【フィルター設定】")
        mercari_coords['filter_button'] = self.get_coordinate('filter_button', '詳細検索ボタン')
        mercari_coords['condition_filter'] = self.get_coordinate('condition_filter', '商品の状態フィルター')
        mercari_coords['condition_new'] = self.get_coordinate('condition_new', '新品・未使用チェックボックス')
        mercari_coords['condition_unused'] = self.get_coordinate('condition_unused', '未使用に近いチェックボックス')
        mercari_coords['price_range'] = self.get_coordinate('price_range', '価格帯選択')
        mercari_coords['price_min'] = self.get_coordinate('price_min', '最低価格入力欄')
        mercari_coords['price_max'] = self.get_coordinate('price_max', '最高価格入力欄')
        mercari_coords['sold_filter'] = self.get_coordinate('sold_filter', '販売状況フィルター')
        mercari_coords['sold_out_checkbox'] = self.get_coordinate('sold_out_checkbox', '売り切れチェックボックス')
        mercari_coords['search_button'] = self.get_coordinate('search_button', '検索実行ボタン')
        mercari_coords['clear_filter'] = self.get_coordinate('clear_filter', 'フィルタークリアボタン')

        # 商品グリッド（最大20）
        print("\n【商品グリッド設定】")
        print("※商品一覧の各商品の中心位置をクリック")
        for i in range(1, 21):
            coord = self.get_coordinate(f'product_grid_{i}', f'{i}番目の商品位置（{(i-1)//5 + 1}行{(i-1)%5 + 1}列目）')
            if coord:
                mercari_coords[f'product_grid_{i}'] = coord
            else:
                if i <= 10:
                    print(f"警告: 商品グリッド{i}は必須項目です")

        # 商品詳細ページ
        print("\n【商品詳細ページ要素】")
        mercari_coords['product_title'] = self.get_coordinate('product_title', '商品タイトル位置')
        mercari_coords['product_price'] = self.get_coordinate('product_price', '商品価格位置')
        mercari_coords['product_description'] = self.get_coordinate('product_description', '商品説明文エリア')

        # 画像エリア
        print("\n【商品画像エリア】")
        image_area = self.get_area_coordinates('product_image_area', '商品画像表示エリア（複数画像対応）')
        if image_area:
            mercari_coords['product_image_area'] = image_area
        mercari_coords['product_image_main'] = self.get_coordinate('product_image_main', 'メイン商品画像の中心')
        mercari_coords['product_image_thumb_1'] = self.get_coordinate('product_image_thumb_1', 'サムネイル画像1')
        mercari_coords['product_image_thumb_2'] = self.get_coordinate('product_image_thumb_2', 'サムネイル画像2')

        # 販売者情報
        print("\n【販売者情報】")
        mercari_coords['seller_name'] = self.get_coordinate('seller_name', '販売者名表示位置')
        mercari_coords['seller_rating'] = self.get_coordinate('seller_rating', '販売者評価表示位置')
        mercari_coords['seller_items'] = self.get_coordinate('seller_items', '出品者の他の商品リンク')

        # 売却情報
        print("\n【売却情報エリア】")
        mercari_coords['sold_label'] = self.get_coordinate('sold_label', 'SOLDラベル位置')
        sold_history_area = self.get_area_coordinates('sold_history_area', '売却履歴表示エリア（3日間売上カウント用）')
        if sold_history_area:
            mercari_coords['sold_history_area'] = sold_history_area
        mercari_coords['purchase_button'] = self.get_coordinate('purchase_button', '購入手続きボタン（参考用）')

        # いいね・コメント
        print("\n【いいね・コメント機能】")
        mercari_coords['like_button'] = self.get_coordinate('like_button', 'いいねボタン')
        mercari_coords['like_count'] = self.get_coordinate('like_count', 'いいね数表示')
        mercari_coords['comment_button'] = self.get_coordinate('comment_button', 'コメントボタン')
        mercari_coords['comment_area'] = self.get_coordinate('comment_area', 'コメント入力エリア')

        # ナビゲーション・スクロール
        print("\n【ナビゲーション】")
        mercari_coords['back_button'] = self.get_coordinate('back_button', '戻るボタン位置')
        mercari_coords['next_page'] = self.get_coordinate('next_page', '次のページボタン')
        mercari_coords['prev_page'] = self.get_coordinate('prev_page', '前のページボタン')
        mercari_coords['page_number'] = self.get_coordinate('page_number', 'ページ番号表示')
        print("\n【スクロール設定】")
        mercari_coords['scroll_top'] = self.get_coordinate('scroll_top', 'スクロール基準位置（上部）')
        mercari_coords['scroll_bottom'] = self.get_coordinate('scroll_bottom', 'スクロール基準位置（下部）')

        # 保存
        self.save_coordinates(mercari_coords, 'mercari')
        print(f"\n✓ メルカリ座標設定完了")

    def map_alibaba_coordinates(self):
        """アリババ用座標マッピング（必要最小限の雛形）"""
        self.current_module = "alibaba"
        print("\n" + "=" * 80)
        print("アリババ（1688.com）モジュール座標設定")
        print("=" * 80)
        input("1688.com を開いて準備できたら Enter ...")
        alibaba_coords: Dict[str, Any] = {}
        alibaba_coords['logo'] = self.get_coordinate('logo', '1688ロゴ（ホーム）')
        alibaba_coords['search_bar'] = self.get_coordinate('search_bar', 'テキスト検索バー')
        alibaba_coords['image_search_button'] = self.get_coordinate('image_search_button', 'カメラアイコン（画像検索）')
        upload_area = self.get_area_coordinates('upload_area', '画像アップロードエリア')
        if upload_area:
            alibaba_coords['upload_area'] = upload_area
        self.save_coordinates(alibaba_coords, 'alibaba')

    def map_spreadsheet_coordinates(self):
        """スプレッドシート用座標（必要最小限の雛形）"""
        self.current_module = "spreadsheet"
        print("\n" + "=" * 80)
        print("スプレッドシート モジュール座標設定")
        print("=" * 80)
        input("スプレッドシートを開いて準備できたら Enter ...")
        sheet_coords: Dict[str, Any] = {}
        sheet_coords['sheet_tab'] = self.get_coordinate('sheet_tab', '対象シートのタブ')
        sheet_coords['append_row_button'] = self.get_coordinate('append_row_button', '行追加（任意）')
        self.save_coordinates(sheet_coords, 'spreadsheet')

    def map_listing_coordinates(self):
        """出品用座標（必要最小限の雛形）"""
        self.current_module = "listing"
        print("\n" + "=" * 80)
        print("出品 モジュール座標設定")
        print("=" * 80)
        input("メルカリ出品画面を開いて準備できたら Enter ...")
        listing_coords: Dict[str, Any] = {}
        listing_coords['sell_button'] = self.get_coordinate('sell_button', '出品ボタン')
        self.save_coordinates(listing_coords, 'listing')

    def map_all_coordinates(self):
        """全モジュール設定"""
        self.map_mercari_coordinates()
        self.map_alibaba_coordinates()
        self.map_spreadsheet_coordinates()
        self.map_listing_coordinates()

    # --------- 検証/テスト ---------
    def verify_all_coordinates(self):
        """設定済み座標の確認"""
        print("\n=== 設定確認 ===")
        for module in ['mercari', 'alibaba', 'spreadsheet', 'listing']:
            coords = self.load_coordinates(module)
            if coords and '_metadata' in coords:
                print(f"{module:15}: {coords['_metadata'].get('total_items', 0)} 項目")
            else:
                print(f"{module:15}: 未設定")

    def test_coordinates(self, module_name: str):
        """特定モジュールの座標をテスト"""
        coords = self.load_coordinates(module_name)
        if not coords:
            print(f"{module_name}の座標が設定されていません")
            return

        print(f"\n{module_name}の座標をテストします")
        print("各座標にマウスが移動します（Ctrl+Cで中断）")
        test_coords = {k: v for k, v in coords.items() if k != '_metadata'}

        for name, coord in test_coords.items():
            if isinstance(coord, (list, tuple)) and len(coord) == 2:
                print(f"\nテスト: {name} -> {coord}")
                pyautogui.moveTo(coord[0], coord[1], duration=0.5)
                time.sleep(0.5)
            elif isinstance(coord, dict) and 'top_left' in coord:
                print(f"\nテスト: {name} (エリア)")
                tl = coord['top_left']; br = coord['bottom_right']
                pyautogui.moveTo(tl[0], tl[1], duration=0.3)
                pyautogui.moveTo(br[0], tl[1], duration=0.3)
                pyautogui.moveTo(br[0], br[1], duration=0.3)
                pyautogui.moveTo(tl[0], br[1], duration=0.3)
                pyautogui.moveTo(tl[0], tl[1], duration=0.3)
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


if __name__ == "__main__":
    print("座標測定ツールを起動します.")
    mapper = CoordinateMapper()
    mapper.start_mapping_session()
