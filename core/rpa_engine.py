"""
RPA基盤エンジン
座標ベースの画面操作と要素待機を管理
"""
import pyautogui
import time
from typing import Tuple, Optional, Dict
from pathlib import Path
import cv2
import numpy as np
from utils.logger import setup_logger

class RPAEngine:
    """
    RPA基盤クラス
    画面要素の検出と操作を管理
    """
    def __init__(self, coordinates: Dict):
        """
        初期化
        Args:
            coordinates: 座標辞書
        """
        self.logger = setup_logger(__name__)
        self.coords = coordinates
        
        # PyAutoGUI設定
        pyautogui.FAILSAFE = True  # 画面端でのフェイルセーフ
        pyautogui.PAUSE = 0.5  # デフォルト待機時間
        
        # 画像認識設定
        self.confidence = 0.8  # 画像マッチング信頼度
    
    def wait_for_element(self, coords: Tuple[int, int], timeout: int = 10) -> bool:
        """
        要素の出現を待機
        Args:
            coords: 要素の座標
            timeout: タイムアウト時間（秒）
        Returns:
            要素が見つかったらTrue
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 座標の色を取得して変化を検出
                pixel_color = pyautogui.pixel(coords[0], coords[1])
                # 背景色でないことを確認（簡易チェック）
                if sum(pixel_color) > 100:  # 黒でない
                    return True
            except Exception as e:
                self.logger.debug(f"要素待機エラー: {e}")
            time.sleep(0.5)
        
        self.logger.warning(f"要素待機タイムアウト: {coords}")
        return False
    
    def find_element_by_image(self, image_path: str, region: Optional[Tuple] = None) -> Optional[Tuple]:
        """
        画像による要素検索
        Args:
            image_path: 検索画像パス
            region: 検索領域
        Returns:
            見つかった要素の中心座標
        """
        try:
            # 画像検索
            location = pyautogui.locateCenterOnScreen(
                image_path,
                confidence=self.confidence,
                region=region
            )
            if location:
                self.logger.debug(f"画像要素発見: {location}")
                return location
        except Exception as e:
            self.logger.debug(f"画像検索エラー: {e}")
        return None
    
    def check_element_exists(self, coords: Tuple[int, int]) -> bool:
        """
        要素の存在確認
        Args:
            coords: 確認する座標
        Returns:
            要素が存在すればTrue
        """
        try:
            # スクリーンショットを取得
            screenshot = pyautogui.screenshot()
            # 座標の周辺領域を確認
            x, y = coords
            region_size = 10
            
            # 領域の平均色を計算
            region = screenshot.crop((
                x - region_size,
                y - region_size,
                x + region_size,
                y + region_size
            ))
            
            # numpy配列に変換
            region_array = np.array(region)
            mean_color = np.mean(region_array, axis=(0, 1))
            
            # 背景色でないことを確認
            if np.sum(mean_color) > 150:
                return True
        except Exception as e:
            self.logger.debug(f"要素確認エラー: {e}")
        return False
    
    def scroll_to_element(self, coords: Tuple[int, int], max_scrolls: int = 10) -> bool:
        """
        要素までスクロール
        Args:
            coords: 目標要素の座標
            max_scrolls: 最大スクロール回数
        """
        for i in range(max_scrolls):
            if self.check_element_exists(coords):
                self.logger.debug(f"要素発見（スクロール{i}回）")
                return True
            
            # 下にスクロール
            pyautogui.scroll(-300)
            time.sleep(0.5)
        
        self.logger.warning("スクロールしても要素が見つかりません")
        return False
    
    def take_screenshot(self, filename: Optional[str] = None, region: Optional[Tuple] = None) -> str:
        """
        スクリーンショット撮影
        Args:
            filename: ファイル名
            region: 撮影領域
        Returns:
            保存したファイルパス
        """
        if filename is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f'screenshot_{timestamp}.png'
        
        filepath = Path('logs/screenshots') / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()
        
        screenshot.save(filepath)
        self.logger.debug(f"スクリーンショット保存: {filepath}")
        return str(filepath)
    
    def get_screen_size(self) -> Tuple[int, int]:
        """画面サイズ取得"""
        return pyautogui.size()
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """マウス位置取得"""
        return pyautogui.position()