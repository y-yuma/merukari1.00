"""
マルチディスプレイ対応スクリーンショットヘルパー
macOS Retina + Windows両対応

問題解決：
- 右画面でRPAは動くのにスクショだけ左画面になる問題を修正
- macOSのマルチディスプレイ＋Retinaスケール問題に対応
- 画像判定スコアが52-55点で固定される問題を解決
"""
import platform
import subprocess
import pyautogui
from PIL import Image
import tempfile
from pathlib import Path
import time
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ScreenshotHelper:
    """
    マルチディスプレイ環境でのスクリーンショット問題を解決するヘルパークラス
    """
    
    def __init__(self):
        self.os_type = platform.system()
        self.is_mac = self.os_type == 'Darwin'
        self.is_windows = self.os_type == 'Windows'
        
        # Retinaスケール検出（Mac用）
        self.retina_scale = self._detect_retina_scale() if self.is_mac else 1
        
        logger.info(f"ScreenshotHelper初期化: OS={self.os_type}, Retina Scale={self.retina_scale}")
    
    def _detect_retina_scale(self) -> int:
        """macOSのRetinaスケールを検出"""
        try:
            # システムプロファイラーからディスプレイ情報を取得
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True,
                text=True
            )
            
            # Retinaディスプレイかチェック
            if 'Retina' in result.stdout or 'Resolution: ' in result.stdout:
                # 簡易的に2倍と仮定（実際には解像度から計算すべき）
                return 2
            return 1
        except:
            # エラー時はデフォルト値
            return 1
    
    def capture_region(self, 
                       left: int, 
                       top: int, 
                       width: int, 
                       height: int,
                       use_native: bool = True) -> Image.Image:
        """
        指定範囲のスクリーンショットを取得
        
        Args:
            left: 左端のX座標
            top: 上端のY座標
            width: 幅
            height: 高さ
            use_native: ネイティブツールを使用するか
            
        Returns:
            PIL.Image オブジェクト
        """
        if self.is_mac and use_native:
            return self._capture_mac_native(left, top, width, height)
        elif self.is_windows and use_native:
            return self._capture_windows_native(left, top, width, height)
        else:
            # フォールバック：pyautogui使用
            return self._capture_pyautogui(left, top, width, height)
    
    def _capture_mac_native(self, left: int, top: int, width: int, height: int) -> Image.Image:
        """
        macOS screencapture コマンドを使用した範囲指定キャプチャ
        """
        try:
            # 一時ファイル作成
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
            
            # screencaptureコマンドで範囲指定
            # -R オプション: x,y,width,height の形式で範囲指定
            cmd = [
                'screencapture',
                '-x',  # 音を出さない
                '-R', f'{left},{top},{width},{height}',
                tmp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and Path(tmp_path).exists():
                # 画像読み込み
                image = Image.open(tmp_path)
                
                # 一時ファイル削除
                Path(tmp_path).unlink()
                
                logger.debug(f"Mac native capture成功: {width}x{height} at ({left},{top})")
                return image
            else:
                logger.warning("Mac native capture失敗、pyautogui使用")
                return self._capture_pyautogui(left, top, width, height)
                
        except Exception as e:
            logger.error(f"Mac native captureエラー: {e}")
            return self._capture_pyautogui(left, top, width, height)
    
    def _capture_windows_native(self, left: int, top: int, width: int, height: int) -> Image.Image:
        """
        Windows用の改善されたキャプチャ（win32api使用可能な場合）
        """
        try:
            # まずはpyautogui.screenshotで試す（Windowsでは通常問題ない）
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            logger.debug(f"Windows capture成功: {width}x{height} at ({left},{top})")
            return screenshot
            
        except Exception as e:
            logger.error(f"Windows captureエラー: {e}")
            # フォールバック：全画面撮影してクロップ
            return self._capture_and_crop(left, top, width, height)
    
    def _capture_pyautogui(self, left: int, top: int, width: int, height: int) -> Image.Image:
        """
        pyautogui標準のキャプチャ（フォールバック）
        """
        try:
            # Retinaスケールを考慮
            if self.is_mac and self.retina_scale > 1:
                # Retina用の座標調整
                actual_left = left // self.retina_scale
                actual_top = top // self.retina_scale
                actual_width = width // self.retina_scale
                actual_height = height // self.retina_scale
                
                screenshot = pyautogui.screenshot(
                    region=(actual_left, actual_top, actual_width, actual_height)
                )
                
                # 元のサイズにリサイズ
                screenshot = screenshot.resize((width, height), Image.LANCZOS)
            else:
                screenshot = pyautogui.screenshot(region=(left, top, width, height))
            
            logger.debug(f"pyautogui capture: {width}x{height} at ({left},{top})")
            return screenshot
            
        except Exception as e:
            logger.error(f"pyautogui captureエラー: {e}")
            # 最終フォールバック：全画面撮影してクロップ
            return self._capture_and_crop(left, top, width, height)
    
    def _capture_and_crop(self, left: int, top: int, width: int, height: int) -> Image.Image:
        """
        全画面キャプチャしてクロップ（最終フォールバック）
        """
        try:
            # 全画面キャプチャ
            full_screenshot = pyautogui.screenshot()
            
            # 指定範囲をクロップ
            right = left + width
            bottom = top + height
            
            # 画面サイズを超えないよう調整
            screen_width, screen_height = pyautogui.size()
            right = min(right, screen_width)
            bottom = min(bottom, screen_height)
            
            cropped = full_screenshot.crop((left, top, right, bottom))
            
            logger.debug(f"全画面クロップ: {width}x{height} at ({left},{top})")
            return cropped
            
        except Exception as e:
            logger.error(f"クロップエラー: {e}")
            # エラー時は全画面を返す
            return pyautogui.screenshot()
    
    def click_and_capture(self,
                         click_coords: Tuple[int, int],
                         capture_area: dict,
                         wait_time: float = 2.0) -> Optional[Image.Image]:
        """
        クリックしてモーダルを開き、指定範囲をキャプチャ
        
        Args:
            click_coords: クリックする座標 (x, y)
            capture_area: キャプチャエリア情報 {'top_left': [x,y], 'width': w, 'height': h}
            wait_time: クリック後の待機時間
            
        Returns:
            キャプチャした画像またはNone
        """
        try:
            # クリック実行
            pyautogui.click(click_coords[0], click_coords[1])
            time.sleep(wait_time)
            
            # キャプチャ範囲取得
            left = capture_area['top_left'][0]
            top = capture_area['top_left'][1]
            width = capture_area['width']
            height = capture_area['height']
            
            # スクリーンショット取得
            screenshot = self.capture_region(left, top, width, height)
            
            # モーダルを閉じる
            pyautogui.press('escape')
            time.sleep(0.5)
            
            return screenshot
            
        except Exception as e:
            logger.error(f"クリック&キャプチャエラー: {e}")
            # エラー時もモーダルを閉じる
            try:
                pyautogui.press('escape')
            except:
                pass
            return None


# グローバルインスタンス（シングルトン的に使用）
_screenshot_helper = None


def get_screenshot_helper() -> ScreenshotHelper:
    """ScreenshotHelperのグローバルインスタンスを取得"""
    global _screenshot_helper
    if _screenshot_helper is None:
        _screenshot_helper = ScreenshotHelper()
    return _screenshot_helper


def capture_region_safe(left: int, top: int, width: int, height: int) -> Image.Image:
    """
    簡易関数：指定範囲を安全にキャプチャ
    
    Args:
        left: 左端のX座標
        top: 上端のY座標
        width: 幅
        height: 高さ
        
    Returns:
        PIL.Image オブジェクト
    """
    helper = get_screenshot_helper()
    return helper.capture_region(left, top, width, height)