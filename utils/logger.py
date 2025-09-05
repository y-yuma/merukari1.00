"""
ログ管理モジュール
システム全体のログ記録を管理
"""
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
import sys

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    ロガー設定
    Args:
        name: ロガー名
        level: ログレベル
    Returns:
        設定済みロガー
    """
    # ロガー取得
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 既にハンドラーが設定されている場合はスキップ
    if logger.handlers:
        return logger
    
    # ログディレクトリ作成
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（通常ログ）
    file_handler = RotatingFileHandler(
        log_dir / 'system.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # エラーログハンドラー
    error_handler = RotatingFileHandler(
        log_dir / 'error.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger

class LogManager:
    """
    ログマネージャークラス
    アプリケーション全体のログを統括管理
    """
    def __init__(self):
        """初期化"""
        self.logger = setup_logger(__name__)
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
    
    def log_operation_start(self, operation: str, details: dict = None):
        """
        操作開始ログ
        Args:
            operation: 操作名
            details: 詳細情報
        """
        self.logger.info(f"操作開始: {operation}")
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")
    
    def log_operation_end(self, operation: str, success: bool, details: dict = None):
        """
        操作終了ログ
        Args:
            operation: 操作名
            success: 成功フラグ
            details: 詳細情報
        """
        status = "成功" if success else "失敗"
        self.logger.info(f"操作終了: {operation} - {status}")
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")
    
    def log_performance(self, operation: str, duration: float, items_processed: int = 0):
        """
        パフォーマンスログ
        Args:
            operation: 操作名
            duration: 処理時間（秒）
            items_processed: 処理項目数
        """
        self.logger.info(f"パフォーマンス: {operation}")
        self.logger.info(f"  処理時間: {duration:.2f}秒")
        if items_processed > 0:
            self.logger.info(f"  処理項目数: {items_processed}")
            self.logger.info(f"  処理速度: {items_processed/duration:.2f}項目/秒")