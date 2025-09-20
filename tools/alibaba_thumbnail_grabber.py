"""
アリババサムネイル収集ツール
PyAutoGUIでサムネイルにホバー → 左側の拡大画像を自動検出・保存
"""

import pyautogui
import numpy as np
import cv2
import time
import json
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import random
import argparse

class AlibabaThumbnailGrabber:
    """
    アリババのサムネイル画像収集クラス
    ホバーによる拡大画像を自動検出・保存
    """
    
    def __init__(self, config_path: str = "config/alibaba_config.yaml"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルパス
        """
        # 設定読み込み
        self.config = self._load_config(config_path)
        
        # ログ設定
        self._setup_logger()
        
        # PyAutoGUI設定
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        
        # キャッシュ
        self.big_rect_cache = {}
        self.cache_timestamp = {}
        
        # 画面サイズ取得
        self.screen_width, self.screen_height = pyautogui.size()
        self.logger.info(f"画面サイズ: {self.screen_width}x{self.screen_height}")
        
        # DPI/スケーリングチェック
        if self.screen_width == 1920 and self.screen_height == 1080:
            self.logger.info("フルHD解像度検出 - スケーリング100%を推奨")
        else:
            self.logger.warning("非標準解像度検出 - OSスケール100%/ブラウザズーム100%を確認してください")
        
        # データディレクトリ作成
        self.candidates_dir = Path(self.config['paths']['candidates_dir'])
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        
        # CLI引数によるオーバーライド用
        self.override_manual_roi = None
        self.override_big_rel = None
        self.override_mode = None
        self.preview_mode = False
    
    def _load_config(self, config_path: str) -> Dict:
        """設定ファイル読み込み"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _setup_logger(self):
        """ログ設定"""
        log_dir = Path(self.config['paths']['log_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_level = getattr(logging, self.config['paths']['log_level'])
        
        # ハンドラー設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # ファイルハンドラー
        file_handler = logging.FileHandler(
            log_dir / f"alibaba_grabber_{datetime.now():%Y%m%d}.log",
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        
        # ロガー設定
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # ハンドラー二重付与防止
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def set_overrides(self, manual_roi: Optional[str] = None, 
                     big_rel: Optional[str] = None, 
                     mode: Optional[str] = None,
                     gridx: Optional[int] = None,
                     gridy: Optional[int] = None,
                     no_contour: bool = False,
                     preview: bool = False):
        """
        CLI引数によるオーバーライド設定
        
        Args:
            manual_roi: 手動ROI "x,y,w,h"
            big_rel: 拡大画像相対座標 "dx,dy,w,h"
            mode: 拡大画像モード "relative" or "zone"
            gridx: X方向グリッド間隔
            gridy: Y方向グリッド間隔
            no_contour: 輪郭検出を無効化
            preview: プレビューモード
        """
        if manual_roi:
            try:
                values = [int(v.strip()) for v in manual_roi.split(',')]
                if len(values) == 4 and all(v >= 0 for v in values[2:]):
                    self.override_manual_roi = values
                    self.logger.info(f"手動ROIオーバーライド: {values}")
            except:
                self.logger.warning(f"無効な手動ROI: {manual_roi}")
        
        if big_rel:
            try:
                values = [int(v.strip()) for v in big_rel.split(',')]
                if len(values) == 4:
                    self.override_big_rel = {
                        'dx': values[0],
                        'dy': values[1],
                        'width': values[2],
                        'height': values[3]
                    }
                    self.logger.info(f"拡大画像相対座標オーバーライド: {self.override_big_rel}")
            except:
                self.logger.warning(f"無効な拡大画像相対座標: {big_rel}")
        
        if mode in ['relative', 'zone']:
            self.override_mode = mode
            self.logger.info(f"拡大画像モードオーバーライド: {mode}")
        
        if gridx is not None and gridx > 0:
            self.config['thumbnail_grabber']['grid_step_x'] = gridx
            self.logger.info(f"X方向グリッド間隔オーバーライド: {gridx}")
        
        if gridy is not None and gridy > 0:
            self.config['thumbnail_grabber']['grid_step_y'] = gridy
            self.logger.info(f"Y方向グリッド間隔オーバーライド: {gridy}")
        
        if no_contour:
            self.config['thumbnail_grabber']['use_contour_candidates'] = False
            self.logger.info("輪郭検出を無効化")
        
        self.preview_mode = preview
        if preview:
            self.logger.info("プレビューモード有効")
    
    def harvest_thumbnails(self, offer_id: str) -> Dict:
        """
        サムネイル収集メイン処理
        
        Args:
            offer_id: アリババのオファーID
            
        Returns:
            収集結果の辞書
        """
        self.logger.info(f"サムネイル収集開始: offer_id={offer_id}")
        
        # 保存先ディレクトリ作成
        save_dir = self.candidates_dir / offer_id
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # ROI決定
        roi = self._determine_roi()
        self.logger.info(f"ROI決定: {roi}")
        
        # 候補点生成
        candidate_points = self._generate_candidate_points(roi)
        self.logger.info(f"候補点数: {len(candidate_points)}")
        
        # 拡大画像モード取得
        big_image_mode = self._get_big_image_mode()
        self.logger.info(f"拡大画像モード: {big_image_mode}")
        
        # 結果格納用
        results = {
            "offer_id": offer_id,
            "timestamp": datetime.now().isoformat(),
            "left_big_rect": None,
            "big_image_mode": big_image_mode,
            "roi": list(roi),
            "candidates": []
        }
        
        # プレビューモードの場合
        if self.preview_mode:
            self.logger.info("プレビューモード: デバッグ画像のみ生成")
            # ダミーの結果を作成
            for idx, point in enumerate(candidate_points):
                results["candidates"].append({
                    "index": idx,
                    "hover_point": list(point),
                    "rect": None,
                    "path": None,
                    "ok": False,
                    "preview": True
                })
            # デバッグ画像生成
            self._save_debug_image(roi, candidate_points, results)
            self.logger.info(f"プレビュー画像を保存しました: logs/debug/")
            return results
        
        # 各候補点でホバー＆画像取得
        for idx, point in enumerate(candidate_points):
            self.logger.debug(f"処理中: {idx+1}/{len(candidate_points)} - {point}")
            
            try:
                if big_image_mode == "relative":
                    # relativeモード：マウス相対位置で拡大画像取得
                    result = self._hover_and_capture_relative(point, save_dir, idx)
                    
                    if result:
                        big_rect, img_path = result
                        results["candidates"].append({
                            "index": idx,
                            "hover_point": list(point),
                            "rect": list(big_rect),
                            "path": str(img_path),
                            "ok": True
                        })
                        
                        # 初回成功時にキャッシュ
                        if results["left_big_rect"] is None:
                            results["left_big_rect"] = list(big_rect)
                    else:
                        results["candidates"].append({
                            "index": idx,
                            "hover_point": list(point),
                            "rect": None,
                            "path": None,
                            "ok": False,
                            "reason": "video-suspected"
                        })
                else:
                    # zoneモード：差分検出で拡大画像取得
                    big_rect = self._hover_and_detect(point, offer_id)
                    
                    if big_rect:
                        # 拡大画像を切り出し保存
                        img_path = self._capture_big_image(big_rect, save_dir, idx)
                        
                        if img_path:  # 動画サムネ除外された場合はNone
                            results["candidates"].append({
                                "index": idx,
                                "hover_point": list(point),
                                "rect": list(big_rect),
                                "path": str(img_path),
                                "ok": True
                            })
                            
                            # 初回成功時にキャッシュ
                            if results["left_big_rect"] is None:
                                results["left_big_rect"] = list(big_rect)
                                self.big_rect_cache[offer_id] = big_rect
                                self.cache_timestamp[offer_id] = time.time()
                                self.logger.info(f"拡大画像矩形をキャッシュ: {big_rect}")
                    else:
                        results["candidates"].append({
                            "index": idx,
                            "hover_point": list(point),
                            "rect": None,
                            "path": None,
                            "ok": False,
                            "reason": "diff-timeout"
                        })
                    
            except Exception as e:
                self.logger.error(f"候補点{idx}でエラー: {e}")
                results["candidates"].append({
                    "index": idx,
                    "hover_point": list(point),
                    "error": str(e),
                    "ok": False
                })
            
            # 短い待機
            time.sleep(0.2)
        
        # デバッグ画像生成
        if self.config['debug']['draw_rects']:
            self._save_debug_image(roi, candidate_points, results)
        
        # 結果をJSON保存
        result_json = save_dir / "result.json"
        with open(result_json, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"収集完了: 成功={sum(1 for c in results['candidates'] if c['ok'])}/{len(results['candidates'])}")
        
        return results
    
    def _get_big_image_mode(self) -> str:
        """拡大画像モード取得（オーバーライド対応）"""
        if self.override_mode:
            return self.override_mode
        return self.config['thumbnail_grabber'].get('big_image_mode', 'zone')
    
    def _determine_roi(self) -> Tuple[int, int, int, int]:
        """
        ROI（関心領域）を決定（手動指定最優先）
        
        Returns:
            (x, y, width, height)のタプル
        """
        # CLIオーバーライドチェック
        if self.override_manual_roi:
            x, y, w, h = self.override_manual_roi
            self.logger.info(f"CLIオーバーライドROI使用: ({x}, {y}, {w}, {h})")
            return (x, y, w, h)
        
        # 手動ROI設定チェック
        manual_roi = self.config['thumbnail_grabber'].get('manual_roi_pixels')
        if manual_roi and isinstance(manual_roi, list) and len(manual_roi) == 4:
            x, y, w, h = manual_roi
            if w > 0 and h > 0:
                # 画面範囲内にクランプ
                x = max(0, min(x, self.screen_width - 1))
                y = max(0, min(y, self.screen_height - 1))
                w = min(w, self.screen_width - x)
                h = min(h, self.screen_height - y)
                self.logger.info(f"手動指定ROI使用: ({x}, {y}, {w}, {h})")
                return (x, y, w, h)
        
        # アンカー検出を試みる
        anchor_roi = self._detect_anchor_roi()
        
        if anchor_roi:
            self.logger.info("アンカーベースのROI使用")
            return anchor_roi
        else:
            # デフォルトROI使用
            self.logger.info("デフォルトROI使用")
            roi_config = self.config['thumbnail_grabber']['default_roi']
            
            x = int(self.screen_width * roi_config['x_ratio'])
            y = int(self.screen_height * roi_config['y_ratio'])
            width = int(self.screen_width * roi_config['width_ratio'])
            height = int(self.screen_height * roi_config['height_ratio'])
            
            return (x, y, width, height)
    
    def _detect_anchor_roi(self) -> Optional[Tuple[int, int, int, int]]:
        """
        アンカー画像を検出してROIを計算（修正版：左側にROI）
        
        Returns:
            成功時は(x, y, width, height)、失敗時はNone
        """
        anchors_dir = Path(self.config['paths']['anchors_dir'])
        confidence = self.config['thumbnail_grabber']['locate_confidence']
        
        for anchor_name in self.config['paths']['anchor_images']:
            anchor_path = anchors_dir / anchor_name
            
            if not anchor_path.exists():
                self.logger.warning(f"アンカー画像が見つかりません: {anchor_path}")
                continue
            
            try:
                # アンカー画像を検索
                location = pyautogui.locateOnScreen(
                    str(anchor_path),
                    confidence=confidence
                )
                
                if location:
                    anchor_x, anchor_y, anchor_w, anchor_h = location
                    expected_w = int(self.screen_width * 0.28)
                    margin = 40
                    
                    if anchor_x > self.screen_width // 2:
                        # 右側にボタン → ROIは左側（サムネ列/バリエーション帯）
                        roi_x = max(0, anchor_x - expected_w - margin)
                    else:
                        # レアケース：ボタンが左 → ROIは右
                        roi_x = min(self.screen_width - expected_w, anchor_x + anchor_w + margin)
                    
                    roi_y = max(0, anchor_y - int(self.screen_height * 0.25))
                    roi_width = min(expected_w, self.screen_width - roi_x)
                    roi_height = min(int(self.screen_height * 0.55), self.screen_height - roi_y)
                    
                    self.logger.info(f"アンカー検出成功: {anchor_name} at {location}")
                    return (roi_x, roi_y, roi_width, roi_height)
                    
            except Exception as e:
                self.logger.debug(f"アンカー検出失敗 ({anchor_name}): {e}")
        
        return None
    
    def _big_rect_from_cursor(self, point: Tuple[int, int]) -> Tuple[int, int, int, int]:
        """
        マウス位置から相対的に拡大画像矩形を計算
        
        Args:
            point: マウス位置 (x, y)
            
        Returns:
            拡大画像の矩形 (x, y, width, height)
        """
        # オーバーライドまたは設定から取得
        if self.override_big_rel:
            params = self.override_big_rel
        else:
            params = self.config['thumbnail_grabber'].get('big_from_cursor', {})
        
        dx = params.get('dx', -980)
        dy = params.get('dy', -120)
        width = params.get('width', 900)
        height = params.get('height', 700)
        
        # マウス位置からの相対座標計算
        x = point[0] + dx
        y = point[1] + dy
        
        # 画面範囲内にクランプ
        x = max(0, x)
        y = max(0, y)
        width = min(width, self.screen_width - x)
        height = min(height, self.screen_height - y)
        
        return (x, y, width, height)
    
    def _hover_and_capture_relative(self, point: Tuple[int, int], save_dir: Path, index: int) -> Optional[Tuple[Tuple[int, int, int, int], Path]]:
        """
        relativeモード：ホバー後、マウス相対位置で拡大画像を取得
        
        Args:
            point: ホバー位置
            save_dir: 保存先ディレクトリ
            index: インデックス番号
            
        Returns:
            成功時は(拡大画像矩形, ファイルパス)のタプル、動画の場合はNone
        """
        # マウス移動
        pyautogui.moveTo(point[0], point[1], duration=0.2)
        
        # ホバー待機
        wait_time = random.uniform(
            self.config['thumbnail_grabber']['hover_wait_min'],
            self.config['thumbnail_grabber']['hover_wait_max']
        )
        time.sleep(wait_time)
        
        # マウス位置から拡大画像矩形を計算
        big_rect = self._big_rect_from_cursor(point)
        
        # 拡大画像をキャプチャ
        x, y, w, h = big_rect
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
        
        # 動画サムネチェック
        raw = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        if self._looks_like_video(raw):
            self.logger.info(f"動画サムネイルを除外: index={index}")
            return None
        
        # ファイル保存
        if self.config['performance']['use_png']:
            filename = f"img_{index:04d}.png"
        else:
            filename = f"img_{index:04d}.jpg"
        
        filepath = save_dir / filename
        
        if self.config['performance']['use_png']:
            screenshot.save(filepath, "PNG")
        else:
            screenshot.save(filepath, "JPEG", quality=self.config['performance']['screenshot_quality'])
        
        self.logger.debug(f"画像保存: {filepath} (relative mode)")
        
        return big_rect, filepath
    
    def _left_zone(self) -> Tuple[int, int, int, int]:
        """
        左ゾーン（差分検出対象領域）の座標を返す
        
        Returns:
            (x, y, width, height)のタプル
        """
        # 手動指定チェック
        zone_pixels = self.config['thumbnail_grabber'].get('left_zone_pixels')
        if zone_pixels and isinstance(zone_pixels, list) and len(zone_pixels) == 4:
            x, y, w, h = zone_pixels
            if w > 0 and h > 0:
                # 画面範囲内にクランプ
                x = max(0, min(x, self.screen_width - 1))
                y = max(0, min(y, self.screen_height - 1))
                w = min(w, self.screen_width - x)
                h = min(h, self.screen_height - y)
                return (x, y, w, h)
        
        # 設定から読み込み（なければデフォルト値）
        zone_config = self.config['thumbnail_grabber'].get('left_zone', {})
        
        width_ratio = zone_config.get('width_ratio', 0.60)
        y_top_ratio = zone_config.get('y_top_ratio', 0.15)
        height_ratio = zone_config.get('height_ratio', 0.70)
        
        x = 0
        y = int(self.screen_height * y_top_ratio)
        w = int(self.screen_width * width_ratio)
        h = int(self.screen_height * height_ratio)
        
        return (x, y, w, h)
    
    def _take_screenshot_region(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """
        指定領域のスクリーンショットを取得
        
        Args:
            region: (x, y, width, height)のタプル、Noneなら全画面
            
        Returns:
            BGR形式のnumpy配列
        """
        if region is None:
            screenshot = pyautogui.screenshot()
        else:
            screenshot = pyautogui.screenshot(region=region)
        
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    def _generate_candidate_points(self, roi: Tuple[int, int, int, int]) -> List[Tuple[int, int]]:
        """
        候補点を生成（改良版：縦横別ステップ、マージン、順序制御）
        
        Args:
            roi: (x, y, width, height)のタプル
            
        Returns:
            候補点のリスト
        """
        x, y, width, height = roi
        g = self.config['thumbnail_grabber']
        
        # グリッド設定取得
        step = g['grid_step']
        step_x = g.get('grid_step_x', step)
        step_y = g.get('grid_step_y', step)
        margin = g.get('grid_margin', 0)
        
        points = []
        
        # 端を少し避けて、等間隔グリッドを作る
        for row in range(margin, max(height - margin, 1), step_y):
            for col in range(margin, max(width - margin, 1), step_x):
                # グリッド中心点を計算（step_xが大きい場合は幅の中央）
                px = x + col + min(step_x, width - col) // 2
                py = y + row + min(step_y, height - row) // 2
                
                # 画面範囲内チェック
                if 0 <= px < self.screen_width and 0 <= py < self.screen_height:
                    points.append((px, py))
        
        # スキャン順序：列優先（上→下）または行優先（左→右）
        scan_order = g.get('scan_order', 'col')
        if scan_order == 'col':
            # 列優先：X座標でグループ化してからY座標でソート
            points.sort(key=lambda p: (p[0], p[1]))
        else:
            # 行優先：Y座標でグループ化してからX座標でソート
            points.sort(key=lambda p: (p[1], p[0]))
        
        # 輪郭検出による候補点追加（オプション）
        if g.get('use_contour_candidates', True):
            contour_points = self._detect_thumbnail_contours(roi)
            if contour_points:
                self.logger.info(f"輪郭検出による候補点追加: {len(contour_points)}個")
                # 輪郭候補を先頭に追加
                points = contour_points + points
        
        return points
    
    def _detect_thumbnail_contours(self, roi: Tuple[int, int, int, int]) -> List[Tuple[int, int]]:
        """
        OpenCVで小矩形輪郭を検出（高速化）
        
        Args:
            roi: (x, y, width, height)のタプル
            
        Returns:
            検出された中心点のリスト
        """
        try:
            # ROI領域のスクリーンショット
            screenshot = pyautogui.screenshot(region=roi)
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # グレースケール変換
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # エッジ検出
            edges = cv2.Canny(gray, 50, 150)
            
            # 輪郭検出
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            points = []
            x_offset, y_offset = roi[0], roi[1]
            
            for contour in contours:
                # 面積でフィルタリング（20-120px四方）
                area = cv2.contourArea(contour)
                if 400 <= area <= 14400:
                    # 中心点計算
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"]) + x_offset
                        cy = int(M["m01"] / M["m00"]) + y_offset
                        points.append((cx, cy))
            
            return points[:50]  # 最大50個
            
        except Exception as e:
            self.logger.debug(f"輪郭検出失敗: {e}")
            return []
    
    def _iou(self, a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        """
        矩形のIoU（Intersection over Union）を計算
        
        Args:
            a, b: (x, y, width, height)のタプル
            
        Returns:
            IoU値（0.0～1.0）
        """
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        
        x1 = max(ax, bx)
        y1 = max(ay, by)
        x2 = min(ax + aw, bx + bw)
        y2 = min(ay + ah, by + bh)
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = aw * ah + bw * bh - inter + 1e-6
        
        return inter / union
    
    def _hover_and_detect(self, point: Tuple[int, int], offer_id: str) -> Optional[Tuple[int, int, int, int]]:
        """
        zoneモード：指定位置にホバーして拡大画像を差分検出（安定化機能付き）
        
        Args:
            point: ホバー位置
            offer_id: オファーID（キャッシュ用）
            
        Returns:
            成功時は(x, y, width, height)、失敗時はNone
        """
        # キャッシュチェック
        if offer_id in self.big_rect_cache:
            cache_age = time.time() - self.cache_timestamp[offer_id]
            if cache_age < self.config['performance']['cache_timeout']:
                self.logger.debug("キャッシュされた矩形を使用")
                return self.big_rect_cache[offer_id]
        
        # 左ゾーンのホバー前スクリーンショット
        left_zone = self._left_zone()
        before = self._take_screenshot_region(left_zone)
        
        # マウス移動
        pyautogui.moveTo(point[0], point[1], duration=0.2)
        
        # 安定化ループ
        stable_needed = self.config['thumbnail_grabber']['diff_stable_frames']  # 2
        timeout_sec = self.config['thumbnail_grabber']['diff_stable_timeout']  # 1.5
        tick = 0.2
        stable_count = 0
        elapsed = 0.0
        last_rect = None
        
        while elapsed < timeout_sec:
            time.sleep(tick)
            after = self._take_screenshot_region(left_zone)
            
            # 差分検出（region内の座標で返る）
            rect = self._detect_difference(before, after)
            
            if rect:
                if last_rect and self._iou(rect, last_rect) > 0.8:
                    stable_count += 1
                    if stable_count >= stable_needed:
                        # 画面全体座標に変換
                        lx, ly, lw, lh = left_zone
                        global_rect = (rect[0] + lx, rect[1] + ly, rect[2], rect[3])
                        self.logger.debug(f"安定した矩形検出: {global_rect}")
                        return global_rect
                else:
                    stable_count = 1
                    last_rect = rect
            
            elapsed += tick
        
        # タイムアウト - リトライ
        retry_offset = self.config['thumbnail_grabber']['hover_retry_offset']
        max_retries = self.config['thumbnail_grabber']['max_retries']
        
        for retry in range(max_retries):
            self.logger.debug(f"リトライ {retry+1}/{max_retries}")
            
            # 位置を微調整
            new_x = point[0] + random.randint(-retry_offset, retry_offset)
            new_y = point[1] + random.randint(-retry_offset, retry_offset)
            
            pyautogui.moveTo(new_x, new_y, duration=0.2)
            
            # 再度安定化待機（短縮版）
            time.sleep(0.8)
            after = self._take_screenshot_region(left_zone)
            rect = self._detect_difference(before, after)
            
            if rect:
                lx, ly, lw, lh = left_zone
                global_rect = (rect[0] + lx, rect[1] + ly, rect[2], rect[3])
                self.logger.debug(f"リトライで矩形検出: {global_rect}")
                return global_rect
        
        self.logger.debug("差分検出タイムアウト")
        return None
    
    def _detect_difference(self, before: np.ndarray, after: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        差分から拡大画像矩形を検出（region内座標を返す）
        
        Args:
            before: ホバー前の画像
            after: ホバー後の画像
            
        Returns:
            成功時は(x, y, width, height)、失敗時はNone
        """
        # 差分計算
        diff = cv2.absdiff(after, before)
        
        # グレースケール変換
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # 二値化
        _, binary = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
        
        # モルフォロジー処理（ノイズ除去と結合）
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        morphed = cv2.dilate(morphed, kernel, iterations=2)
        
        # 輪郭検出
        contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # 最大輪郭を探す
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        # 面積チェック
        min_area = self.config['thumbnail_grabber']['big_rect_area_min']
        max_area = self.config['thumbnail_grabber']['big_rect_area_max']
        
        if not (min_area <= area <= max_area):
            self.logger.debug(f"面積が範囲外: {area} (期待: {min_area}-{max_area})")
            return None
        
        # バウンディングボックス取得
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # アスペクト比チェック（極端な形状を除外）
        aspect_ratio = w / h if h > 0 else 0
        if aspect_ratio < 0.3 or aspect_ratio > 3.0:
            self.logger.debug(f"アスペクト比が異常: {aspect_ratio}")
            return None
        
        # パディング追加（region内でクリップ）
        padding = self.config['thumbnail_grabber']['padding']
        region_h, region_w = after.shape[:2]
        
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(region_w - x, w + padding * 2)
        h = min(region_h - y, h + padding * 2)
        
        # デバッグ用：差分画像保存
        if self.config['debug']['save_diff_images']:
            self._save_diff_debug(after, (x, y, w, h))
        
        return (x, y, w, h)
    
    def _looks_like_video(self, bgr: np.ndarray) -> bool:
        """
        動画サムネイルかどうかを判定
        
        Args:
            bgr: BGR画像
            
        Returns:
            動画サムネイルっぽければTrue
        """
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # 下部15%に均一な黒帯があるか
        bar = gray[int(h * 0.85):, :]
        if np.mean(bar < 40) > 0.60:
            self.logger.debug("動画サムネ検出: 黒帯")
            return True
        
        # 画像中央に白い三角（再生ボタン）があるか
        mid = gray[int(h * 0.35):int(h * 0.65), int(w * 0.35):int(w * 0.65)]
        _, th = cv2.threshold(mid, 220, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for c in contours:
            area = cv2.contourArea(c)
            if 200 < area < 5000:
                approx = cv2.approxPolyDP(c, 0.08 * cv2.arcLength(c, True), True)
                if len(approx) == 3:  # 三角形
                    self.logger.debug("動画サムネ検出: 再生ボタン")
                    return True
        
        return False
    
    def _capture_big_image(self, rect: Tuple[int, int, int, int], save_dir: Path, index: int) -> Optional[Path]:
        """
        拡大画像を切り出して保存（動画サムネ除外付き）
        
        Args:
            rect: (x, y, width, height)のタプル
            save_dir: 保存先ディレクトリ
            index: インデックス番号
            
        Returns:
            保存したファイルパス、動画サムネの場合はNone
        """
        x, y, w, h = rect
        
        # 領域のスクリーンショット
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
        
        # 動画サムネチェック
        raw = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        if self._looks_like_video(raw):
            self.logger.info(f"動画サムネイルを除外: index={index}")
            return None
        
        # ファイル名生成
        if self.config['performance']['use_png']:
            filename = f"img_{index:04d}.png"
        else:
            filename = f"img_{index:04d}.jpg"
        
        filepath = save_dir / filename
        
        # 保存
        if self.config['performance']['use_png']:
            screenshot.save(filepath, "PNG")
        else:
            screenshot.save(filepath, "JPEG", quality=self.config['performance']['screenshot_quality'])
        
        self.logger.debug(f"画像保存: {filepath}")
        
        return filepath
    
    def _save_diff_debug(self, img: np.ndarray, rect: Tuple[int, int, int, int]):
        """差分デバッグ画像保存"""
        debug_dir = Path(self.config['paths']['log_dir']) / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # 矩形を描画
        debug_img = img.copy()
        x, y, w, h = rect
        cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        cv2.imwrite(str(debug_dir / f"diff_{timestamp}.png"), debug_img)
    
    def _save_debug_image(self, roi: Tuple[int, int, int, int], points: List[Tuple[int, int]], results: Dict):
        """統合デバッグ画像を保存"""
        if not self.config['debug']['draw_rects']:
            return
        
        debug_dir = Path(self.config['paths']['log_dir']) / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # 全画面スクリーンショット
        screenshot = self._take_screenshot_region()
        
        # ROI描画（青）
        x, y, w, h = roi
        cv2.rectangle(screenshot, (x, y), (x+w, y+h), (255, 0, 0), 2)
        cv2.putText(screenshot, "ROI", (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # 候補点描画（緑=成功、赤=失敗）
        for candidate in results['candidates']:
            if 'hover_point' in candidate:
                px, py = candidate['hover_point']
                color = (0, 255, 0) if candidate['ok'] else (0, 0, 255)
                cv2.circle(screenshot, (px, py), 3, color, -1)
        
        # 拡大画像矩形描画（黄）
        for candidate in results['candidates']:
            if candidate['ok'] and 'rect' in candidate and candidate['rect']:
                bx, by, bw, bh = candidate['rect']
                cv2.rectangle(screenshot, (bx, by), (bx+bw, by+bh), (0, 255, 255), 1)
        
        # 最初の成功した拡大画像矩形を強調（太線）
        if results['left_big_rect']:
            bx, by, bw, bh = results['left_big_rect']
            cv2.rectangle(screenshot, (bx, by), (bx+bw, by+bh), (0, 255, 255), 3)
            cv2.putText(screenshot, "BigRect", (bx+5, by+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # 保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = debug_dir / f"debug_summary_{results['offer_id']}_{timestamp}.png"
        cv2.imwrite(str(filename), screenshot)
        self.logger.info(f"デバッグ画像保存: {filename}")


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="アリババサムネイル収集ツール")
    parser.add_argument("offer_id", help="アリババのオファーID")
    parser.add_argument("--config", default="config/alibaba_config.yaml", help="設定ファイルパス")
    parser.add_argument("--debug", action="store_true", help="デバッグモード")
    
    # オーバーライド引数
    parser.add_argument("--manual-roi", help="手動ROI指定 'x,y,w,h'")
    parser.add_argument("--bigrel", help="拡大画像相対座標 'dx,dy,w,h'")
    parser.add_argument("--mode", choices=['relative', 'zone'], help="拡大画像取得モード")
    parser.add_argument("--gridx", type=int, help="X方向グリッド間隔")
    parser.add_argument("--gridy", type=int, help="Y方向グリッド間隔")
    parser.add_argument("--no-contour", action="store_true", help="輪郭検出を無効化")
    parser.add_argument("--preview", action="store_true", help="プレビューモード（マウス動作なし）")
    
    args = parser.parse_args()
    
    # デバッグモード設定
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # 実行
    grabber = AlibabaThumbnailGrabber(args.config)
    
    # オーバーライド設定
    grabber.set_overrides(
        manual_roi=args.manual_roi,
        big_rel=args.bigrel,
        mode=args.mode,
        gridx=args.gridx,
        gridy=args.gridy,
        no_contour=args.no_contour,
        preview=args.preview
    )
    
    results = grabber.harvest_thumbnails(args.offer_id)
    
    # プレビューモードの場合
    if args.preview:
        print(f"\nプレビューモード結果:")
        print(f"  ROI: {results.get('roi', 'unknown')}")
        print(f"  候補点数: {len(results['candidates'])}")
        print(f"  デバッグ画像: logs/debug/debug_summary_{args.offer_id}_*.png")
        return 0
    
    # 結果表示
    success_count = sum(1 for c in results['candidates'] if c['ok'])
    total_count = len(results['candidates'])
    
    print(f"\n収集結果:")
    print(f"  成功: {success_count}/{total_count}")
    print(f"  保存先: data/alibaba/candidates/{args.offer_id}/")
    print(f"  モード: {results.get('big_image_mode', 'unknown')}")
    print(f"  ROI: {results.get('roi', 'unknown')}")
    
    if results['left_big_rect']:
        print(f"  拡大画像矩形: {results['left_big_rect']}")
    
    # 失敗理由の集計
    failures = [c for c in results['candidates'] if not c['ok']]
    if failures:
        print(f"\n失敗理由:")
        reasons = {}
        for f in failures:
            reason = f.get('reason', 'unknown')
            reasons[reason] = reasons.get(reason, 0) + 1
        for reason, count in reasons.items():
            print(f"  {reason}: {count}件")
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())