"""
スプレッドシート管理モジュール
Googleスプレッドシートとの連携（RPAベース）
"""
import pyautogui
import pyperclip
import time
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from core.rpa_engine import RPAEngine
from core.human_behavior import HumanBehavior
from utils.logger import setup_logger

class SpreadsheetManager:
    """
    スプレッドシート管理クラス
    GoogleスプレッドシートをRPAで操作
    """
    
    def __init__(self, spreadsheet_url: str = None):
        """
        初期化
        Args:
            spreadsheet_url: スプレッドシートのURL
        """
        self.logger = setup_logger(__name__)
        self.spreadsheet_url = spreadsheet_url
        
        # 座標読み込み
        coord_file = Path('config/coordinate_sets/spreadsheet.json')
        if coord_file.exists():
            with open(coord_file, 'r', encoding='utf-8') as f:
                self.coords = json.load(f)
        else:
            self.coords = {}
            self.logger.warning("スプレッドシート座標が未設定です")
        
        # モジュール初期化
        self.rpa = RPAEngine(self.coords)
        self.human = HumanBehavior()
        
        # 現在の行位置（データ追加用）
        self.current_row = 2  # ヘッダーは1行目なので2行目から開始

    def open_spreadsheet(self, url: str = None):
        """
        スプレッドシートを開く
        Args:
            url: スプレッドシートURL
        """
        target_url = url or self.spreadsheet_url
        if not target_url:
            self.logger.error("スプレッドシートURLが設定されていません")
            return False
        
        self.logger.info("スプレッドシートを開きます")
        
        try:
            # 新しいタブを開く
            pyautogui.hotkey('ctrl', 't')
            time.sleep(1)
            
            # URLバーにフォーカス
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.5)
            
            # URL入力
            self.human.type_like_human(target_url)
            pyautogui.press('enter')
            
            # ページ読み込み待機
            time.sleep(5)
            
            self.logger.info("スプレッドシート開放完了")
            return True
            
        except Exception as e:
            self.logger.error(f"スプレッドシート開放エラー: {e}")
            return False

    def setup_headers(self):
        """ヘッダー行を設定"""
        self.logger.info("ヘッダー行を設定します")
        
        headers = [
            'キーワード',        # A1
            '予想販売数/月',      # B1
            'メルカリ相場',       # C1
            '検索結果URL',       # D1
            '商品URL',          # E1
            '画像検索URL',       # F1
            '仕入URL',          # G1
            '仕入価格',         # H1
            'MOQ',             # I1
            '重量(kg)',         # J1
            'サイズ',           # K1
            '配送方法',         # L1
            '利益率',           # M1
            '月間利益',         # N1
            'ステータス'        # O1
        ]
        
        # A1セルから開始
        if 'header_a1' in self.coords:
            self.human.move_and_click(self.coords['header_a1'])
            time.sleep(0.5)
        
        # ヘッダーを順番に入力
        for i, header in enumerate(headers):
            if i > 0:
                pyautogui.press('tab')  # 次のセルへ
                time.sleep(0.2)
            
            # セルをクリアしてから入力
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            self.human.type_like_human(header)
            time.sleep(0.3)
        
        # 保存
        pyautogui.hotkey('ctrl', 's')
        time.sleep(1)
        
        self.logger.info("ヘッダー行設定完了")

    def append_row(self, data: List[str]):
        """
        データ行を追加
        Args:
            data: 追加するデータのリスト
        """
        self.logger.debug(f"データ行追加: 行{self.current_row}")
        
        try:
            # A列の現在行をクリック
            if 'cell_a2' in self.coords:
                # 基準座標から現在行を計算（行の高さを25pxと仮定）
                base_x, base_y = self.coords['cell_a2']
                current_y = base_y + (self.current_row - 2) * 25
                self.human.move_and_click((base_x, current_y))
                time.sleep(0.5)
            
            # データを順番に入力
            for i, value in enumerate(data):
                if i > 0:
                    pyautogui.press('tab')  # 次のセルへ
                    time.sleep(0.2)
                
                # データ入力
                if value:  # 空でない場合のみ入力
                    pyautogui.hotkey('ctrl', 'a')
                    time.sleep(0.1)
                    self.human.type_like_human(str(value))
                    time.sleep(0.3)
            
            # 次の行へ
            self.current_row += 1
            
            # 定期的に保存
            if self.current_row % 10 == 0:
                pyautogui.hotkey('ctrl', 's')
                time.sleep(1)
            
            self.logger.debug(f"データ行追加完了: 行{self.current_row - 1}")
            
        except Exception as e:
            self.logger.error(f"データ行追加エラー: {e}")

    def update_cell(self, cell_coord: str, value: str):
        """
        特定セルを更新
        Args:
            cell_coord: セル座標（例: 'cell_m2'）
            value: 更新する値
        """
        if cell_coord in self.coords:
            try:
                self.human.move_and_click(self.coords[cell_coord])
                time.sleep(0.3)
                
                # セルをクリアして新しい値を入力
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.1)
                self.human.type_like_human(str(value))
                time.sleep(0.3)
                
                # Enter で確定
                pyautogui.press('enter')
                time.sleep(0.2)
                
                self.logger.debug(f"セル更新: {cell_coord} = {value}")
                
            except Exception as e:
                self.logger.error(f"セル更新エラー: {e}")
        else:
            self.logger.warning(f"座標未定義: {cell_coord}")

    def find_row_by_url(self, url: str) -> Optional[int]:
        """
        URLで行を検索
        Args:
            url: 検索するURL
        Returns:
            見つかった行番号
        """
        # 簡易実装：現在は線形検索
        # 実際の実装ではCtrl+Fで検索機能を使用
        try:
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)
            
            # 検索ボックスにURL入力
            self.human.type_like_human(url[:50])  # 最初の50文字で検索
            pyautogui.press('enter')
            time.sleep(1)
            
            # 検索結果があるかチェック（簡易実装）
            # 実際の行番号取得は困難なため、現在は固定値返却
            pyautogui.press('escape')  # 検索ボックスを閉じる
            
            return self.current_row  # 簡易実装
            
        except Exception as e:
            self.logger.error(f"行検索エラー: {e}")
            return None

    def update_product_sourcing(self, product_url: str, update_data: Dict):
        """
        商品の仕入れ情報を更新
        Args:
            product_url: 商品のURL
            update_data: 更新データ
        """
        self.logger.info(f"仕入れ情報更新: {product_url[:50]}...")
        
        # 該当行を検索
        row_num = self.find_row_by_url(product_url)
        if not row_num:
            self.logger.warning("該当商品が見つかりません")
            return
        
        # 各セルを更新
        for column, value in update_data.items():
            cell_coord = f'cell_{column.lower()}{row_num}'
            self.update_cell(cell_coord, value)
        
        # 保存
        pyautogui.hotkey('ctrl', 's')
        time.sleep(1)

    def get_statistics(self) -> Dict:
        """
        統計情報取得（簡易版）
        Returns:
            統計情報
        """
        # 実際の実装では関数を使用して計算
        # ここでは簡易的な値を返却
        return {
            'total_products': self.current_row - 2,  # ヘッダー行を除く
            'active_listings': 0,
            'sold': 0,
            'total_sales': 0,
            'total_profit': 0,
            'avg_profit_rate': 0
        }

    def load_products_for_sourcing(self) -> List[Dict]:
        """
        仕入れ判断用の商品データを読み込み
        Returns:
            商品データのリスト
        """
        # 簡易実装：空リストを返却
        # 実際の実装ではスプレッドシートから読み取り
        self.logger.warning("load_products_for_sourcing は簡易実装です")
        return []

    def load_products_for_listing(self) -> List[Dict]:
        """
        出品用の商品データを読み込み
        Returns:
            商品データのリスト
        """
        # 簡易実装：空リストを返却
        self.logger.warning("load_products_for_listing は簡易実装です")
        return []

    def get_active_listings(self) -> List[Dict]:
        """
        アクティブな出品を取得
        Returns:
            出品データのリスト
        """
        # 簡易実装：空リストを返却
        self.logger.warning("get_active_listings は簡易実装です")
        return []

    def has_active_listing(self, title: str) -> bool:
        """
        アクティブな出品が存在するかチェック
        Args:
            title: 商品タイトル
        Returns:
            存在すればTrue
        """
        # 簡易実装：常にFalseを返却
        return False

    def update_listing_status(self, identifier: str, status_data: Dict):
        """
        出品ステータスを更新
        Args:
            identifier: 商品識別子（URLなど）
            status_data: ステータスデータ
        """
        self.logger.info(f"出品ステータス更新: {identifier[:50]}...")
        # 簡易実装：ログのみ出力

    def record_relisting(self, old_id: str, new_id: str):
        """
        再出品を記録
        Args:
            old_id: 旧出品ID
            new_id: 新出品ID
        """
        self.logger.info(f"再出品記録: {old_id} -> {new_id}")
        # 簡易実装：ログのみ出力

    def update_price_history(self, listing_id: str, price_data: Dict):
        """
        価格履歴を更新
        Args:
            listing_id: 出品ID
            price_data: 価格データ
        """
        self.logger.info(f"価格履歴更新: {listing_id}")
        # 簡易実装：ログのみ出力

    def get_product_by_listing_id(self, listing_id: str) -> Optional[Dict]:
        """
        出品IDで商品を検索
        Args:
            listing_id: 出品ID
        Returns:
            商品データ
        """
        # 簡易実装：Noneを返却
        return None

    def export_to_excel(self, filepath: str):
        """
        Excelファイルにエクスポート
        Args:
            filepath: エクスポート先ファイルパス
        """
        self.logger.info(f"Excel エクスポート: {filepath}")
        # 簡易実装：ログのみ出力

    def export_to_csv(self, filepath: str):
        """
        CSVファイルにエクスポート
        Args:
            filepath: エクスポート先ファイルパス
        """
        self.logger.info(f"CSV エクスポート: {filepath}")
        # 簡易実装：ログのみ出力

    def export_to_json(self, filepath: str):
        """
        JSONファイルにエクスポート
        Args:
            filepath: エクスポート先ファイルパス
        """
        self.logger.info(f"JSON エクスポート: {filepath}")
        # 簡易実装：ログのみ出力