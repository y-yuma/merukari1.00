# modules/research.py
"""
メルカリリサーチモジュール（改訂版）
- カテゴリーベース検索（キーワードは使用しない）
- 3日間売上カウント必須
- スプレッドシート保存
- 座標モジュール対応
"""

import re
import time
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

import pyautogui
import pyperclip

from core.rpa_engine import RPAEngine
from core.image_analyzer import ImageAnalyzer
from core.spreadsheet import SpreadsheetManager
from core.human_behavior import HumanBehavior
from utils.ocr_reader import OCRReader
from utils.logger import setup_logger


class MercariResearcher:
    """
    メルカリリサーチクラス
    カテゴリーベースで商品を検索し、業者商品を特定
    """

    def __init__(self, spreadsheet_manager: SpreadsheetManager):
        """
        Args:
            spreadsheet_manager: スプレッドシート管理オブジェクト
        """
        self.spreadsheet = spreadsheet_manager
        self.logger = setup_logger(__name__)

        # 座標読み込み（モジュール別）
        coord_file = Path('config/coordinate_sets/mercari.json')
        if not coord_file.exists():
            raise FileNotFoundError(
                "メルカリの座標が設定されていません。"
                "tools/coordinate_setup.pyを実行してください。"
            )

        with coord_file.open('r', encoding='utf-8') as f:
            self.coords = json.load(f)

        # モジュール初期化
        self.rpa = RPAEngine(self.coords)
        self.analyzer = ImageAnalyzer()
        self.ocr = OCRReader()
        self.human = HumanBehavior()

        # 設定
        self.max_retries = 3
        self.retry_delay = 5

    # ========= パブリックAPI =========
    def search_by_category(self, category_path: List[str], max_items: int = 100) -> List[Dict]:
        """
        カテゴリー検索（キーワード不使用）
        Args:
            category_path: カテゴリー階層の「座標キー」リスト（例:
              ["category_button", "category_electronics", "category_pc_tablet", "category_pc_accessories"]）
            max_items: 最大取得商品数
        Returns:
            商品情報のリスト（最低限: url / image_path / sales_3days）
        """
        self.logger.info(f"カテゴリー検索: {' > '.join(category_path)}")
        products: List[Dict] = []

        # 1) カテゴリーパネルを開く
        self._click_if_exists('category_button')
        time.sleep(1)

        # 2) 各階層を順番にクリック（category_button を含むpathを想定）
        for key in category_path:
            if key == "category_button":
                continue
            self._click_if_exists(key)
            time.sleep(0.8)

        # 3) フィルタ（必要なら）
        self._apply_filters()

        # 4) 商品グリッドから順に開いて詳細を取得
        count = 0
        grid_keys = [k for k in self.coords.keys() if k.startswith("product_grid_")]
        grid_keys = sorted(grid_keys, key=lambda x: int(x.split("_")[-1]))

        for grid_key in grid_keys:
            if count >= max_items:
                break
            self.human.move_and_click(self.coords[grid_key])
            time.sleep(2.0)

            # 商品詳細を抽出
            info = self._extract_product_detail()
            if info:
                products.append(info)
                count += 1

            # 一覧に戻る
            self.go_back_to_list()

        # ページャで次ページへ（座標がある場合のみ）
        while count < max_items and self.go_to_next_page():
            for grid_key in grid_keys:
                if count >= max_items:
                    break
                self.human.move_and_click(self.coords[grid_key])
                time.sleep(2.0)
                info = self._extract_product_detail()
                if info:
                    products.append(info)
                    count += 1
                self.go_back_to_list()

        self.logger.info(f"検索結果: {len(products)}件")
        return products

    def filter_by_seller_type(self, products: List[Dict]) -> List[Dict]:
        """
        出品者タイプでフィルタリング（業者のみ抽出）
        """
        filtered: List[Dict] = []
        for product in products:
            if not product.get('image_path'):
                continue
            is_business = self.analyzer.is_business_seller(product['image_path'])
            if is_business:
                product['seller_type'] = 'business'
                filtered.append(product)
                self.logger.debug(f"業者商品: {product.get('title','')[:30]}.")
            else:
                product['seller_type'] = 'individual'
        self.logger.info(f"業者商品フィルタリング: {len(filtered)}/{len(products)}件")
        return filtered

    def analyze_3days_sales(self, products: List[Dict]) -> List[Dict]:
        """
        3日間売上分析（月間予測は main 側で×10。もしくはここで付けてもよい）
        """
        analyzed: List[Dict] = []
        for p in products:
            if 'sales_3days' not in p:
                self.logger.warning(f"3日間売上データなし: {p.get('title','Unknown')}")
                continue
            # ここで月間予測を計算する場合
            p['monthly_estimate'] = p['sales_3days'] * 10
            # 簡易信頼度
            if p['sales_3days'] >= 5:
                p['forecast_confidence'] = 'high'
            elif p['sales_3days'] >= 2:
                p['forecast_confidence'] = 'medium'
            else:
                p['forecast_confidence'] = 'low'
            analyzed.append(p)
        return analyzed

    def save_to_spreadsheet(self, products: List[Dict]):
        """
        スプレッドシートに保存（最低限の列セット）
        """
        self.logger.info(f"スプレッドシートに{len(products)}件保存")
        for product in products:
            try:
                row_data = [
                    "",  # A: キーワード（カテゴリ検索のため空）
                    str(product.get("monthly_estimate", 0)),  # B: 予想販売数/月
                    str(product.get("price", 0)),             # C: メルカリ相場（OCR/未設定なら空）
                    "",                                        # D: 検索結果URL（カテゴリ検索なので空）
                    product.get("url", ""),                    # E: 商品URL
                    "", "", "", "", "", "", "", "",            # F〜N: 仕入/利益などは後工程
                    "リサーチ済",                               # O: ステータス
                ]
                self.spreadsheet.append_row(row_data)
                time.sleep(1)  # APIレート対策
            except Exception as e:
                self.logger.error(f"スプレッドシート保存エラー: {e}")
                continue

    # ========= 内部処理 =========
    def _apply_filters(self):
        """必要に応じて状態/価格/売切済などのフィルターをクリック"""
        # 座標が存在する場合のみクリック（計画書のフィルタ座標セットに対応）
        for key in ["filter_button", "condition_filter", "condition_new", "condition_unused",
                    "price_range", "sold_filter", "sold_out_checkbox", "search_button"]:
            self._click_if_exists(key)
            time.sleep(0.5)

    def _extract_product_detail(self) -> Optional[Dict]:
        """商品詳細ページから最小限の情報を抽出"""
        info: Dict = {}

        # URL取得（Win前提のCtrl+L → Ctrl+C。Macは Command 系に要変更）
        try:
            pyautogui.hotkey('ctrl', 'l')  # Macでは 'command','l' が必要（※後述の注意点）
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.2)
            info['url'] = pyperclip.paste()
        except Exception:
            info['url'] = ""

        # メイン画像 or 画像エリアをスクリーンショット保存
        img_path = None
        img_dir = Path("data/images/mercari")
        img_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        if "product_image_area" in self.coords and isinstance(self.coords["product_image_area"], dict):
            img_path = self.rpa.screenshot_region(self.coords["product_image_area"], img_dir / f"merc_{timestamp}.png")
        elif "product_image_main" in self.coords:
            # 単点座標の場合は小さめの固定領域を切り出す（簡易）
            center = self.coords["product_image_main"]
            region = {
                "top_left": (center[0]-150, center[1]-150),
                "bottom_right": (center[0]+150, center[1]+150),
            }
            img_path = self.rpa.screenshot_region(region, img_dir / f"merc_{timestamp}.png")
        info["image_path"] = str(img_path) if img_path else ""

        # 売却履歴エリアのOCR→3日売上カウント
        sales_3 = 0
        if "sold_history_area" in self.coords and isinstance(self.coords["sold_history_area"], dict):
            txt = self.rpa.ocr_region_text(self.coords["sold_history_area"])
            sales_3 = self._count_recent_sales_from_text(txt)
        info["sales_3days"] = sales_3

        # 価格（オプション: OCR）
        if "product_price" in self.coords:
            price_text = self.rpa.ocr_point_text(self.coords["product_price"])
            price_num = self._parse_price(price_text)
            info["price"] = price_num

        # タイトル（オプション: OCR）
        if "product_title" in self.coords:
            title_text = self.rpa.ocr_point_text(self.coords["product_title"])
            info["title"] = title_text.strip() if title_text else ""

        return info

    def _parse_price(self, text: str) -> int:
        """価格テキストから数値を抽出"""
        if not text:
            return 0
        m = re.search(r"(\d[\d,]*)", text.replace(",", ""))
        try:
            return int(m.group(1)) if m else 0
        except Exception:
            return 0

    def _count_recent_sales_from_text(self, text: str) -> int:
        """
        売却履歴テキストから「直近3日」での販売回数を数える
        例： '2時間前', '5時間前', '1日前', '3日前', '4日前' など
        """
        if not text:
            return 0
        now = datetime.now()
        cnt = 0
        # 行単位でざっくり見る
        for line in text.splitlines():
            line = line.strip()
            # “分前/時間前/日前” のいずれかを拾う
            if any(s in line for s in ["分前", "時間前", "日前"]):
                delta = timedelta(days=10)  # 初期大きめ
                mm = re.search(r"(\d+)\s*分前", line)
                hh = re.search(r"(\d+)\s*時間前", line)
                dd = re.search(r"(\d+)\s*日前", line)
                if mm:
                    delta = timedelta(minutes=int(mm.group(1)))
                elif hh:
                    delta = timedelta(hours=int(hh.group(1)))
                elif dd:
                    delta = timedelta(days=int(dd.group(1)))
                # 3日以内のみカウント
                if delta <= timedelta(days=3):
                    cnt += 1
        return cnt

    # ========= 画面遷移 =========
    def go_back_to_list(self):
        """商品一覧に戻る（Windows想定のAlt+Left）"""
        try:
            pyautogui.hotkey('alt', 'left')  # Macは command + '[' が必要（※注意点）
            time.sleep(2)
            if 'product_grid_1' in self.coords:
                self.rpa.wait_for_element(self.coords['product_grid_1'], timeout=5)
        except Exception as e:
            self.logger.error(f"一覧に戻るエラー: {e}")

    def go_to_next_page(self) -> bool:
        """次ページへ移動"""
        try:
            for _ in range(5):
                pyautogui.scroll(-500)
                time.sleep(0.2)
            if 'next_page' in self.coords:
                self.human.move_and_click(self.coords['next_page'])
                time.sleep(3)
                if 'product_grid_1' in self.coords:
                    return self.rpa.wait_for_element(self.coords['product_grid_1'], timeout=5)
            return False
        except Exception as e:
            self.logger.error(f"次ページ移動エラー: {e}")
            return False

    # ========= 汎用 =========
    def _click_if_exists(self, key: str):
        """座標キーがあればクリック"""
        coord = self.coords.get(key)
        if isinstance(coord, (list, tuple)) and len(coord) == 2:
            self.human.move_and_click(coord)
