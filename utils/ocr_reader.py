"""
OCR処理モジュール
pytesseractを使用したテキスト抽出
"""
import pytesseract
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, List
from utils.logger import setup_logger

class OCRReader:
    """
    OCRリーダークラス
    画像からテキストを抽出
    """
    def __init__(self):
        """初期化"""
        self.logger = setup_logger(__name__)
        
        # Tesseractのパス設定（OS別）
        try:
            import platform
            system = platform.system()
            
            if system == "Windows":
                # Windowsの標準インストールパス
                tesseract_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
                ]
                for path in tesseract_paths:
                    if Path(path).exists():
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
            elif system == "Darwin":  # macOS
                # Homebrewでインストールした場合のパス
                tesseract_paths = [
                    '/usr/local/bin/tesseract',
                    '/opt/homebrew/bin/tesseract'  # Apple Silicon Mac
                ]
                for path in tesseract_paths:
                    if Path(path).exists():
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
            # Linuxは通常PATHに含まれているので設定不要
                        
        except Exception as e:
            self.logger.warning(f"Tesseractパス設定警告: {e}")
    
    def extract_text(self, image_path: str, lang: str = 'jpn+eng') -> str:
        """
        画像からテキストを抽出
        Args:
            image_path: 画像ファイルパス
            lang: 認識言語（jpn+eng = 日本語+英語）
        Returns:
            抽出されたテキスト
        """
        try:
            # 画像読み込み
            image = cv2.imread(image_path)
            if image is None:
                self.logger.error(f"画像読み込み失敗: {image_path}")
                return ""
            
            # 前処理
            processed_image = self.preprocess_image(image)
            
            # OCR実行
            text = pytesseract.image_to_string(
                processed_image, 
                lang=lang,
                config='--psm 6'
            )
            
            # テキストクリーンアップ
            cleaned_text = self.clean_text(text)
            
            self.logger.debug(f"OCR抽出テキスト: {cleaned_text[:50]}...")
            return cleaned_text
            
        except Exception as e:
            self.logger.error(f"OCRエラー: {e}")
            return ""
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        画像前処理
        Args:
            image: 入力画像
        Returns:
            前処理済み画像
        """
        # グレースケール変換
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # ノイズ除去
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # コントラスト強化
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # 二値化（適応的閾値処理）
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        return binary
    
    def clean_text(self, text: str) -> str:
        """
        テキストクリーンアップ
        Args:
            text: 生テキスト
        Returns:
            クリーンアップされたテキスト
        """
        # 改行の正規化
        cleaned = text.replace('\n\n', '\n').strip()
        
        # 不要な空白除去
        lines = []
        for line in cleaned.split('\n'):
            line = line.strip()
            if line:
                lines.append(line)
        
        return '\n'.join(lines)
    
    def extract_numbers(self, image_path: str) -> List[str]:
        """
        数値のみを抽出
        Args:
            image_path: 画像ファイルパス
        Returns:
            抽出された数値のリスト
        """
        import re
        text = self.extract_text(image_path)
        # 数値パターンの抽出
        numbers = re.findall(r'\d+', text)
        return numbers
    
    def extract_price(self, image_path: str) -> Optional[int]:
        """
        価格を抽出（日本円）
        Args:
            image_path: 画像ファイルパス
        Returns:
            抽出された価格
        """
        import re
        text = self.extract_text(image_path)
        
        # 価格パターン（円、¥、コンマ区切りなど）
        price_patterns = [
            r'[¥￥]\s*([0-9,]+)',
            r'([0-9,]+)\s*円',
            r'([0-9,]+)\s*[¥￥]',
            r'(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    # コンマを除去して数値化
                    price = int(match.replace(',', ''))
                    if 100 <= price <= 1000000:  # 妥当な価格範囲
                        return price
                except ValueError:
                    continue
        
        return None