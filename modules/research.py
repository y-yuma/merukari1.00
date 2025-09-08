"""
メルカリリサーチモジュール（改訂版）
- カテゴリーベース検索
- 3日間売上カウント必須
- スプレッドシート保存
- 座標モジュール対応
"""
import pyautogui
import pyperclip
import time
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import random

from core.rpa_engine import RPAEngine
from core.human_behavior import HumanBehavior
from utils.ocr_reader import OCRReader
from utils.logger import setup_logger

class MercariResearcher:
    """
    メルカリリサーチクラス
    カテゴリーベースで商品を検索し、業者商品を特定
    """
    
    def __init__(self, spreadsheet_manager=None):
        """
        初期化
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
                "python tools/coordinate_mapper.py を実行してください。"
            )
        
        with open(coord_file, 'r', encoding='utf-8') as f:
            self.coords = json.load(f)
        
        # モジュール初期化
        self.rpa = RPAEngine(self.coords)
        self.ocr = OCRReader()
        self.human = HumanBehavior()
        
        # 設定
        self.max_retries = 3
        self.retry_delay = 5

    def search_by_category(self, category_path: List[str], max_items: int = 100) -> List[Dict]:
        """
        カテゴリー検索（キーワード不使用）
        Args:
            category_path: カテゴリー階層のリスト
            max_items: 最大取得商品数
        Returns:
            商品情報のリスト
        """
        self.logger.info(f"カテゴリー検索開始: {' > '.join(category_path)}")
        products = []
        
        try:
            # メルカリトップページへ
            self.navigate_to_mercari()
            
            # カテゴリー選択
            self.select_category_hierarchy(category_path)
            
            # フィルター適用
            self.apply_search_filters()
            
            # 検索実行
            self.execute_search()
            
            # 商品収集
            page = 1
            while len(products) < max_items:
                self.logger.info(f"ページ{page}の商品を収集中...")
                
                # 現在ページの商品を処理
                page_products = self.process_search_results_page(max_items - len(products))
                if not page_products:
                    self.logger.info("これ以上商品がありません")
                    break
                
                products.extend(page_products)
                
                # 次ページへ
                if len(products) < max_items:
                    if not self.go_to_next_page():
                        break
                    page += 1
                
                # レート制限対策
                if page % 3 == 0:
                    self.logger.info("レート制限対策: 30秒待機")
                    time.sleep(30)
                    
        except Exception as e:
            self.logger.error(f"カテゴリー検索エラー: {e}")
            raise
        
        self.logger.info(f"カテゴリー検索完了: {len(products)}件")
        return products

    def navigate_to_mercari(self):
        """メルカリトップページへ移動（ロゴクリック方式）"""
        self.logger.debug("メルカリトップページへ移動（ロゴクリック）")
        
        # ロゴクリックでトップページに移動
        if 'logo' in self.coords:
            self.logger.debug("ロゴをクリックしてトップページに移動")
            self.human.move_and_click(self.coords['logo'])
            time.sleep(2)  # ページ読み込み待機
            
            # ロゴが表示されているか確認（トップページ移動完了の確認）
            self.rpa.wait_for_element(self.coords['logo'], timeout=10)
            self.logger.info("✓ メルカリトップページ移動完了")
        else:
            self.logger.error("ロゴの座標が設定されていません")
            raise ValueError("ロゴの座標が設定されていません")

    def select_category_hierarchy(self, category_path: List[str]):
        """
        カテゴリー階層を選択
        Args:
            category_path: カテゴリー階層のリスト
        """
        self.logger.debug(f"カテゴリー選択: {category_path}")
        
        # カテゴリーボタンクリック
        if 'category_button' in self.coords:
            self.human.move_and_click(self.coords['category_button'])
            time.sleep(1.5)
        
        # カテゴリー階層を順番に選択
        category_coords_map = {
            '家電・スマホ・カメラ': 'category_electronics',
            'PC/タブレット': 'category_pc_tablet',
            'PC周辺機器': 'category_pc_accessories',
            'おもちゃ・ホビー・グッズ': 'category_toys',
            'スポーツ・レジャー': 'category_sports',
            'おもちゃ': 'category_toys_general',
            'キャラクターグッズ': 'category_character',
            'トレーニング/エクササイズ': 'category_training',
            'トレーニング用品': 'category_training_goods'
        }
        
        for i, category in enumerate(category_path):
            coord_key = category_coords_map.get(category)
            if coord_key and coord_key in self.coords:
                self.logger.debug(f"  階層{i+1}: {category}")
                self.human.move_and_click(self.coords[coord_key])
                time.sleep(1)
            else:
                self.logger.warning(f"カテゴリー座標未定義: {category}")

    def apply_search_filters(self):
        """検索フィルター適用"""
        self.logger.debug("フィルター適用")
        
        # 商品の状態フィルター
        if 'condition_filter' in self.coords:
            self.human.move_and_click(self.coords['condition_filter'])
            time.sleep(0.8)
        
        # 新品・未使用を選択
        if 'condition_new' in self.coords:
            self.human.move_and_click(self.coords['condition_new'])
            time.sleep(0.5)
        
        # 価格範囲設定
        if 'price_min' in self.coords:
            self.human.move_and_click(self.coords['price_min'])
            time.sleep(0.3)
            # 既存テキストクリア
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            # 最低価格入力
            self.human.type_like_human('300')
            time.sleep(0.5)
        
        if 'price_max' in self.coords:
            # Tabキーで次のフィールドへ
            pyautogui.press('tab')
            time.sleep(0.3)
            # 最高価格入力
            self.human.type_like_human('15000')
            time.sleep(0.5)
        
        # 販売状況（売り切れ）
        if 'sold_filter' in self.coords:
            self.human.move_and_click(self.coords['sold_filter'])
            time.sleep(0.8)
        
        if 'sold_out_checkbox' in self.coords:
            self.human.move_and_click(self.coords['sold_out_checkbox'])
            time.sleep(0.5)

    def execute_search(self):
        """検索実行"""
        self.logger.debug("検索実行")
        
        if 'search_button' in self.coords:
            self.human.move_and_click(self.coords['search_button'])
        
        # 検索結果読み込み待機
        time.sleep(3)
        
        # 最初の商品が表示されるまで待機
        if 'product_grid_1' in self.coords:
            self.rpa.wait_for_element(self.coords['product_grid_1'], timeout=10)

    def process_search_results_page(self, max_items: int) -> List[Dict]:
        """
        検索結果ページの商品を処理
        Args:
            max_items: このページで処理する最大商品数
        Returns:
            商品情報のリスト
        """
        products = []
        items_processed = 0
        
        # グリッド位置の商品を順番に処理
        for i in range(1, 21):  # 最大20商品/ページ
            if items_processed >= max_items:
                break
            
            grid_key = f'product_grid_{i}'
            if grid_key not in self.coords:
                continue
                
            try:
                # 商品をクリック
                self.human.move_and_click(self.coords[grid_key])
                time.sleep(2)
                
                # 商品情報抽出
                product = self.extract_product_details()
                if product:
                    # 3日間売上カウント（必須）
                    product['sales_3days'] = self.count_3days_sales()
                    product['monthly_estimate'] = product['sales_3days'] * 10
                    products.append(product)
                    self.logger.debug(
                        f"商品{i}: {product['title'][:30]}... "
                        f"(3日売上: {product['sales_3days']})"
                    )
                
                # 一覧に戻る
                self.go_back_to_list()
                items_processed += 1
                
                # 人間らしい休憩
                if items_processed % 5 == 0:
                    self.human.random_pause(2, 4)
                    
            except Exception as e:
                self.logger.error(f"商品{i}の処理エラー: {e}")
                self.go_back_to_list()
                continue
        
        return products

    def extract_product_details(self) -> Optional[Dict]:
        """
        商品詳細情報を抽出
        Returns:
            商品情報の辞書
        """
        try:
            product = {
                'timestamp': datetime.now().isoformat(),
                'category': None,  # 後で設定
                'sales_3days': 0  # 後で更新
            }
            
            # タイトル取得
            if 'product_title' in self.coords:
                pyautogui.tripleClick(
                    self.coords['product_title'][0], 
                    self.coords['product_title'][1]
                )
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.3)
                product['title'] = pyperclip.paste().strip()
            
            # 価格取得
            if 'product_price' in self.coords:
                pyautogui.doubleClick(
                    self.coords['product_price'][0],
                    self.coords['product_price'][1]
                )
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.3)
                price_text = pyperclip.paste()
                
                # 価格を数値に変換
                price_match = re.search(r'[\d,]+', price_text.replace(',', ''))
                if price_match:
                    product['price'] = int(price_match.group())
                else:
                    product['price'] = 0
            
            # URL取得
            cmd_key = self.human.get_cmd_key()
            pyautogui.hotkey(cmd_key, 'l')
            time.sleep(0.3)
            pyautogui.hotkey(cmd_key, 'c')
            time.sleep(0.3)
            product['url'] = pyperclip.paste()
            
            # 商品画像キャプチャ
            product['image_path'] = self.capture_product_image()
            
            # 販売者情報
            if 'seller_name' in self.coords:
                product['seller'] = self.extract_seller_info()
            
            return product
            
        except Exception as e:
            self.logger.error(f"商品詳細抽出エラー: {e}")
            return None

    def count_3days_sales(self) -> int:
        """
        3日間の売上個数カウント（必須機能）
        Returns:
            3日間の売上個数
        """
        self.logger.debug("3日間売上カウント開始")
        
        try:
            # ページ下部へスクロール
            for _ in range(3):
                pyautogui.scroll(-500)
                time.sleep(0.5)
            
            # 売却履歴エリアをキャプチャ
            if 'sold_history_area' in self.coords:
                area = self.coords['sold_history_area']
                # エリア座標の場合
                if isinstance(area, dict) and 'top_left' in area:
                    region = (
                        area['top_left'][0],
                        area['top_left'][1],
                        area['width'],
                        area['height']
                    )
                else:
                    # 単一座標の場合はデフォルトサイズ
                    region = (100, 400, 800, 600)
                
                screenshot = pyautogui.screenshot(region=region)
                temp_path = 'temp_sales.png'
                screenshot.save(temp_path)
                
                # OCRでテキスト抽出
                text = self.ocr.extract_text(temp_path, lang='jpn')
                
                # 売上カウント
                count = 0
                # 今日の売上パターン
                today_patterns = ['時間前', '分前', 'たった今', '1時間以内']
                # 3日以内の売上パターン
                within_3days_patterns = ['1日前', '2日前', '3日前']
                
                lines = text.split('\n')
                for line in lines:
                    # 今日の売上
                    for pattern in today_patterns:
                        if pattern in line:
                            count += 1
                            self.logger.debug(f"売却検出（今日）: {line[:50]}")
                            break
                    
                    # 3日以内の売上
                    for pattern in within_3days_patterns:
                        if pattern in line:
                            count += 1
                            self.logger.debug(f"売却検出（{pattern}）: {line[:50]}")
                            break
                
                # 一時ファイル削除
                try:
                    Path(temp_path).unlink()
                except:
                    pass
                
                self.logger.info(f"3日間売上: {count}個")
                return count
                
        except Exception as e:
            self.logger.error(f"3日間売上カウントエラー: {e}")
            return 0

    def capture_product_image(self) -> str:
        """
        商品画像をキャプチャ
        Returns:
            保存した画像のパス
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = Path(f'data/images/mercari/{timestamp}.png')
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if 'product_image_area' in self.coords:
                area = self.coords['product_image_area']
                if isinstance(area, dict) and 'top_left' in area:
                    region = (
                        area['top_left'][0],
                        area['top_left'][1],
                        area['width'],
                        area['height']
                    )
                else:
                    # デフォルトサイズ
                    region = (300, 300, 600, 600)
                
                screenshot = pyautogui.screenshot(region=region)
                screenshot.save(filepath)
                self.logger.debug(f"画像保存: {filepath}")
                return str(filepath)
                
        except Exception as e:
            self.logger.error(f"画像キャプチャエラー: {e}")
            return ""

    def extract_seller_info(self) -> Dict:
        """
        販売者情報を抽出
        Returns:
            販売者情報の辞書
        """
        seller_info = {}
        
        try:
            # 販売者名
            if 'seller_name' in self.coords:
                pyautogui.click(
                    self.coords['seller_name'][0], 
                    self.coords['seller_name'][1]
                )
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.3)
                seller_info['name'] = pyperclip.paste().strip()
            
            # 評価
            if 'seller_rating' in self.coords:
                # OCRで評価を読み取る
                region = (
                    self.coords['seller_rating'][0] - 50,
                    self.coords['seller_rating'][1] - 20,
                    100,
                    40
                )
                screenshot = pyautogui.screenshot(region=region)
                temp_path = 'temp_rating.png'
                screenshot.save(temp_path)
                rating_text = self.ocr.extract_text(temp_path)
                seller_info['rating'] = rating_text
                
                # 一時ファイル削除
                try:
                    Path(temp_path).unlink()
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"販売者情報抽出エラー: {e}")
        
        return seller_info

    def go_back_to_list(self):
        """商品一覧に戻る"""
        try:
            # ブラウザの戻るボタン
            pyautogui.hotkey('alt', 'left')
            time.sleep(2)
            
            # 商品グリッドが表示されるまで待機
            if 'product_grid_1' in self.coords:
                self.rpa.wait_for_element(self.coords['product_grid_1'], timeout=5)
                
        except Exception as e:
            self.logger.error(f"一覧に戻るエラー: {e}")
            # エラー時はメルカリトップから再開
            self.navigate_to_mercari()

    def go_to_next_page(self) -> bool:
        """
        次のページへ移動
        Returns:
            次ページが存在すればTrue
        """
        try:
            # ページ下部へスクロール
            for _ in range(5):
                pyautogui.scroll(-500)
                time.sleep(0.3)
            
            # 次ページボタンを探す
            if 'next_page' in self.coords:
                # ボタンが有効か確認（色などで判定）
                self.human.move_and_click(self.coords['next_page'])
                time.sleep(3)
                
                # 新しい商品が読み込まれたか確認
                if 'product_grid_1' in self.coords:
                    return self.rpa.wait_for_element(
                        self.coords['product_grid_1'], timeout=5
                    )
            
            return False
            
        except Exception as e:
            self.logger.error(f"次ページ移動エラー: {e}")
            return False

    def filter_by_seller_type(self, products: List[Dict]) -> List[Dict]:
        """
        出品者タイプでフィルタリング（業者のみ抽出）
        簡易実装：月間予測が高い商品を業者商品とする
        Args:
            products: 商品リスト
        Returns:
            業者商品のリスト
        """
        filtered = []
        
        for product in products:
            # 月間予測が30個以上の商品を業者商品と判定
            if product.get('monthly_estimate', 0) >= 30:
                product['seller_type'] = 'business'
                filtered.append(product)
                self.logger.debug(f"業者商品: {product['title'][:30]}...")
            else:
                product['seller_type'] = 'individual'
                self.logger.debug(f"個人商品（除外）: {product['title'][:30]}...")
        
        self.logger.info(f"業者商品フィルタリング: {len(filtered)}/{len(products)}件")
        return filtered

    def analyze_3days_sales(self, products: List[Dict]) -> List[Dict]:
        """
        3日間売上分析（月間予測計算）
        Args:
            products: 商品リスト
        Returns:
            分析済み商品リスト
        """
        analyzed = []
        
        for product in products:
            # 3日間売上データ必須
            if 'sales_3days' not in product:
                self.logger.warning(
                    f"3日間売上データなし: {product.get('title', 'Unknown')}"
                )
                continue
            
            # 月間予測計算（3日×10）
            product['monthly_estimate'] = product['sales_3days'] * 10
            
            # 予測精度スコア（参考値）
            if product['sales_3days'] >= 5:
                product['forecast_confidence'] = 'high'
            elif product['sales_3days'] >= 2:
                product['forecast_confidence'] = 'medium'
            else:
                product['forecast_confidence'] = 'low'
            
            analyzed.append(product)
            
            self.logger.debug(
                f"売上分析: {product['title'][:30]}... "
                f"3日: {product['sales_3days']}個, "
                f"月間予測: {product['monthly_estimate']}個"
            )
        
        return analyzed

    def save_to_spreadsheet(self, products: List[Dict]):
        """
        スプレッドシートに保存
        Args:
            products: 商品リスト
        """
        if not self.spreadsheet:
            self.logger.warning("スプレッドシート管理オブジェクトが設定されていません")
            return
            
        self.logger.info(f"スプレッドシートに{len(products)}件保存")
        
        for product in products:
            try:
                # データ整形
                row_data = [
                    '',  # A列: キーワード（カテゴリー検索なので空）
                    str(product.get('monthly_estimate', 0)),  # B列: 予想販売数/月
                    str(product.get('price', 0)),  # C列: メルカリ相場
                    '',  # D列: 検索結果URL（カテゴリー検索）
                    product.get('url', ''),  # E列: 商品URL
                    '',  # F列: 画像検索URL（後で追加）
                    '',  # G列: 仕入URL（後で追加）
                    '',  # H列: 仕入価格（後で追加）
                    '',  # I列: MOQ（後で追加）
                    '',  # J列: 重量（後で追加）
                    '',  # K列: サイズ（後で追加）
                    '',  # L列: 配送方法（後で追加）
                    '',  # M列: 利益率（後で計算）
                    '',  # N列: 月間利益（後で計算）
                    'リサーチ済'  # O列: ステータス
                ]
                
                # スプレッドシートに追加
                self.spreadsheet.append_row(row_data)
                self.logger.debug(f"保存: {product['title'][:30]}...")
                time.sleep(1)  # API制限対策
                
            except Exception as e:
                self.logger.error(f"スプレッドシート保存エラー: {e}")
                continue