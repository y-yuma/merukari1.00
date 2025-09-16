"""
人間的動作シミュレーション
マウスとキーボードの自然な動作を実装
"""
import pyautogui
import time
import random
import math
from typing import Tuple, Optional
import numpy as np
import platform
import pyperclip
from utils.logger import setup_logger

class HumanBehavior:
    """
    人間的動作クラス
    自然なマウス移動とタイピングを実現
    """
    def __init__(self):
        """初期化"""
        self.logger = setup_logger(__name__)
        
        # OS判定
        self.is_mac = platform.system() == "Darwin"
        
        # 動作設定
        self.typing_speed_range = (0.05, 0.15)  # タイピング速度（秒/文字）
        self.mouse_speed_range = (0.3, 0.8)  # マウス移動速度
        self.thinking_time_range = (0.5, 2.0)  # 考える時間
        self.reading_speed = 200  # 読み速度（文字/分）
        
        # タイプミス設定
        self.typo_probability = 0.02  # タイプミス確率
        self.typo_corrections = True  # タイプミス修正
        
        # PyAutoGUI設定
        pyautogui.MINIMUM_DURATION = 0.1
        pyautogui.MINIMUM_SLEEP = 0.05
        pyautogui.PAUSE = 0.1
    
    def get_cmd_key(self):
        """OSに応じたコマンドキーを取得（PyAutoGUI用）"""
        return 'command' if self.is_mac else 'ctrl'
    
    def move_mouse_naturally(self, x: int, y: int, duration: Optional[float] = None):
        """
        自然なマウス移動
        ベジエ曲線を使用した曲線的な動き
        Args:
            x: 目標X座標
            y: 目標Y座標
            duration: 移動時間
        """
        if duration is None:
            # 距離に応じた移動時間計算
            current_x, current_y = pyautogui.position()
            distance = math.sqrt((x - current_x)**2 + (y - current_y)**2)
            duration = self.calculate_mouse_duration(distance)
        
        # ベジエ曲線による移動
        self.bezier_mouse_move(x, y, duration)
    
    def bezier_mouse_move(self, x: int, y: int, duration: float):
        """
        ベジエ曲線によるマウス移動
        Args:
            x: 目標X座標
            y: 目標Y座標
            duration: 移動時間
        """
        start_x, start_y = pyautogui.position()
        
        # コントロールポイント生成（ランダムな曲線）
        control_x1 = start_x + random.randint(-100, 100)
        control_y1 = start_y + random.randint(-100, 100)
        control_x2 = x + random.randint(-100, 100)
        control_y2 = y + random.randint(-100, 100)
        
        # ベジエ曲線の計算
        steps = max(int(duration * 100), 20)
        for i in range(steps + 1):
            t = i / steps
            # ベジエ曲線の式
            pos_x = (1-t)**3 * start_x + \
                    3*(1-t)**2*t * control_x1 + \
                    3*(1-t)*t**2 * control_x2 + \
                    t**3 * x
            pos_y = (1-t)**3 * start_y + \
                    3*(1-t)**2*t * control_y1 + \
                    3*(1-t)*t**2 * control_y2 + \
                    t**3 * y
            
            pyautogui.moveTo(int(pos_x), int(pos_y))
            time.sleep(duration / steps)
        
        # 最終位置の微調整
        pyautogui.moveTo(x, y)
    
    def calculate_mouse_duration(self, distance: float) -> float:
        """
        マウス移動時間計算
        Args:
            distance: 移動距離
        Returns:
            移動時間
        """
        # 距離に応じた基本時間
        base_time = distance / 1000
        # ランダム要素追加
        variation = random.uniform(*self.mouse_speed_range)
        return max(base_time * variation, 0.2)
    
    def move_and_click(self, coords: Tuple[int, int], button: str = 'left'):
        """
        移動してクリック
        Args:
            coords: クリック座標
            button: マウスボタン
        """
        # 座標の微小なランダム化
        x = coords[0] + random.randint(-2, 2)
        y = coords[1] + random.randint(-2, 2)
        
        # 自然な移動
        self.move_mouse_naturally(x, y)
        
        # クリック前の微小な待機
        time.sleep(random.uniform(0.05, 0.15))
        
        # クリック
        pyautogui.click(x, y, button=button)
        
        # クリック後の微小な待機
        time.sleep(random.uniform(0.1, 0.2))
    
    def command_click(self, coords: Tuple[int, int]):
        """
        中クリック（新タブで開く）- デバッグ情報付き
        Args:
            coords: クリック座標
        """
        # 座標の微小なランダム化
        x = coords[0] + random.randint(-2, 2)
        y = coords[1] + random.randint(-2, 2)
        
        # デバッグ: クリック前の状態確認
        self.logger.info(f"=== 中クリック開始 ===")
        self.logger.info(f"元座標: {coords}, 実際座標: ({x}, {y})")
        
        # 現在のマウス位置を記録
        current_x, current_y = pyautogui.position()
        self.logger.info(f"クリック前マウス位置: ({current_x}, {current_y})")
        
        # 自然な移動
        self.move_mouse_naturally(x, y)
        
        # 移動後の位置確認
        after_x, after_y = pyautogui.position()
        self.logger.info(f"移動後マウス位置: ({after_x}, {after_y})")
        
        # クリック前の微小な待機
        time.sleep(random.uniform(0.05, 0.15))
        
        # 中クリック実行
        self.logger.info(f"中クリック実行: button='middle'")
        pyautogui.click(x, y, button='middle')
        self.logger.info(f"中クリック送信完了")
        
        # 新タブ作成確認のための待機
        time.sleep(3.0)
        
        # 新しいタブにフォーカス移動
        self.focus_new_tab()
        
        self.logger.info(f"=== 中クリック完了 ===")
    
    def focus_new_tab(self):
        """新しく開いたタブにフォーカスを移動 - 物理キー対応"""
        self.logger.info("タブ移動開始")
        
        # Mac/Windows共通：物理的なControl+Tab
        try:
            # 方法1: Control+Tab (物理的なcontrolキー)
            pyautogui.keyDown('ctrl')  # 物理controlキー
            time.sleep(0.1)
            pyautogui.keyDown('tab')   # tabキー
            time.sleep(0.1)
            pyautogui.keyUp('tab')
            pyautogui.keyUp('ctrl')
            self.logger.info("Control+Tab (物理キー) 実行")
            
            time.sleep(1)
            
            # 成功確認
            if self._verify_new_tab():
                self.logger.info("タブ移動成功")
                return
            
            # 方法2: 失敗した場合はControl+Page Down
            pyautogui.keyDown('ctrl')
            time.sleep(0.1)
            pyautogui.press('pagedown')  # 次のタブ
            time.sleep(0.1)
            pyautogui.keyUp('ctrl')
            self.logger.info("Control+PageDown 実行")
            
            time.sleep(1)
            
        except Exception as e:
            self.logger.error(f"タブ移動エラー: {e}")
        
        self.logger.info("タブ移動処理完了")
    
    def _verify_new_tab(self) -> bool:
        """新しいタブに移動できたか確認"""
        try:
            cmd_key = self.get_cmd_key()
            pyautogui.hotkey(cmd_key, 'l')
            time.sleep(0.3)
            pyautogui.hotkey(cmd_key, 'c')
            time.sleep(0.3)
            current_url = pyperclip.paste()
            
            # メルカリ商品ページのURLパターンをチェック
            is_product_page = '/item/' in current_url or 'mercari.com' in current_url
            self.logger.debug(f"URL確認: {current_url[:50]}... 商品ページ: {is_product_page}")
            return is_product_page
        except Exception as e:
            self.logger.error(f"タブ確認エラー: {e}")
            return False
    
    def close_current_tab(self):
        """
        現在のタブを閉じる（OS別対応）
        """
        cmd_key = self.get_cmd_key()
        pyautogui.hotkey(cmd_key, 'w')  # Mac: command+w, Windows: ctrl+w
        time.sleep(1)  # タブが閉じるまで待機
        self.logger.debug(f"タブを閉じました（{cmd_key}+w）")
    
    def double_click(self, coords: Tuple[int, int]):
        """ダブルクリック"""
        x = coords[0] + random.randint(-2, 2)
        y = coords[1] + random.randint(-2, 2)
        
        self.move_mouse_naturally(x, y)
        time.sleep(random.uniform(0.05, 0.1))
        
        # ダブルクリック間隔をランダム化
        interval = random.uniform(0.05, 0.15)
        pyautogui.click(x, y)
        time.sleep(interval)
        pyautogui.click(x, y)
    
    def type_like_human(self, text: str, typos: bool = True):
        """
        人間らしいタイピング
        Args:
            text: 入力テキスト
            typos: タイプミスを含めるか
        """
        for char in text:
            # タイプミス判定
            if typos and self.typo_corrections and random.random() < self.typo_probability:
                # タイプミス発生
                wrong_char = self.generate_typo(char)
                pyautogui.write(wrong_char)
                time.sleep(random.uniform(*self.typing_speed_range))
                
                # 気づくまでの遅延
                time.sleep(random.uniform(0.2, 0.5))
                
                # バックスペースで修正
                pyautogui.press('backspace')
                time.sleep(random.uniform(0.05, 0.1))
            
            # 正しい文字を入力
            pyautogui.write(char)
            
            # タイピング間隔
            if char == ' ':
                # スペースは速い
                time.sleep(random.uniform(0.03, 0.08))
            elif char in '.,!?':
                # 句読点の後は少し間を置く
                time.sleep(random.uniform(0.15, 0.3))
            else:
                # 通常の文字
                time.sleep(random.uniform(*self.typing_speed_range))
    
    def generate_typo(self, char: str) -> str:
        """
        タイプミス生成
        Args:
            char: 正しい文字
        Returns:
            間違った文字
        """
        # キーボード上の隣接キー
        keyboard_layout = {
            'q': 'wa', 'w': 'qeas', 'e': 'wrd', 'r': 'eft', 't': 'rgy',
            'y': 'thu', 'u': 'yij', 'i': 'uok', 'o': 'ipl', 'p': 'ol',
            'a': 'qwsz', 's': 'awedx', 'd': 'serfx', 'f': 'drtgc', 'g': 'ftyv',
            'h': 'gybn', 'j': 'hukmn', 'k': 'jilm', 'l': 'kop',
            'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn',
            'n': 'bhjm', 'm': 'njk'
        }
        
        char_lower = char.lower()
        if char_lower in keyboard_layout:
            adjacent = keyboard_layout[char_lower]
            typo = random.choice(adjacent)
            return typo.upper() if char.isupper() else typo
        return char
    
    def random_pause(self, min_seconds: float = 0.5, max_seconds: float = 2.0):
        """
        ランダムな待機時間
        Args:
            min_seconds: 最小待機時間
            max_seconds: 最大待機時間
        """
        pause_time = random.uniform(min_seconds, max_seconds)
        self.logger.debug(f"待機: {pause_time:.2f}秒")
        time.sleep(pause_time)
    
    def simulate_thinking(self):
        """考える動作のシミュレーション"""
        thinking_time = random.uniform(*self.thinking_time_range)
        self.logger.debug(f"思考時間: {thinking_time:.2f}秒")
        
        # 考えている間、時々マウスを微動
        elapsed = 0
        while elapsed < thinking_time:
            if random.random() < 0.2:  # 20%の確率でマウス微動
                current_x, current_y = pyautogui.position()
                new_x = current_x + random.randint(-5, 5)
                new_y = current_y + random.randint(-5, 5)
                pyautogui.moveTo(new_x, new_y, duration=0.2)
            
            pause = random.uniform(0.3, 0.7)
            time.sleep(pause)
            elapsed += pause