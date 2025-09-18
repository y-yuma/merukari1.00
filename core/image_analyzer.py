"""
画像判定モジュール（精度改善版）
- プロ撮影特徴を優先評価
- 個人撮影背景検出の精度向上（誤検出防止）
- 木目検出の精密化
- スコアキャップからペナルティ方式への変更
"""

import cv2
import numpy as np
from pathlib import Path
import json
import shutil
from datetime import datetime
from typing import Tuple, Dict, Optional, List
import logging


class ImageAnalyzer:
    """画像分析クラス"""

    def __init__(self, config_path: str = "config/config.json"):
        self.setup_logging()
        self.load_config(config_path)
        self.setup_directories()

        # 判定閾値
        self.business_threshold = (
            self.config.get("image_analysis", {})
            .get("business_threshold", 50)
        )

        self.logger.info(f"画像分析エンジンを初期化しました (閾値: {self.business_threshold}点)")

    # -------------------------
    # 初期化周り
    # -------------------------
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def load_config(self, config_path: str):
        try:
            if Path(config_path).exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = {}
                self.logger.warning(f"設定ファイルなし: {config_path}、デフォルト設定を使用")
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")
            self.config = {}

    def setup_directories(self):
        required_dirs = [
            "data/images/mercari_ok",
            "data/images/mercari_ng",
            "data/images/temp",
            "logs"
        ]
        for d in required_dirs:
            Path(d).mkdir(parents=True, exist_ok=True)

    # -------------------------
    # 画像読み込み/正規化
    # -------------------------
    def _read_and_normalize(self, image_path: str) -> np.ndarray:
        """Unicode / EXIF / リサイズ対応"""
        try:
            img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("画像読み込み失敗")

            # EXIF回転
            try:
                from PIL import Image, ImageOps
                pil = Image.open(image_path)
                pil = ImageOps.exif_transpose(pil)
                img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
            except Exception as e:
                self.logger.debug(f"EXIF処理スキップ: {e}")

            # リサイズ
            h, w = img.shape[:2]
            max_side = max(h, w)
            max_size = (
                self.config.get("image_analysis", {})
                .get("max_image_size", 1280)
            )
            if max_side > max_size:
                scale = max_size / max_side
                img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

            return img
        except Exception as e:
            raise ValueError(f"画像正規化エラー: {str(e)}")

    # -------------------------
    # 公開API
    # -------------------------
    def analyze_single_image(self, image_path: str) -> Dict:
        result = {
            "file_path": image_path,
            "file_name": Path(image_path).name,
            "timestamp": datetime.now().isoformat(),
            "is_business": False,
            "score": 0,
            "details": {},
            "reasons": [],
            "rule_results": {},
            "error": None
        }

        try:
            image = self._read_and_normalize(image_path)
            
            # 基礎スコア
            base_score = 50
            
            # =========================================
            # 第0段階: 白背景の事前判定
            # =========================================
            is_white_bg = self._is_white_background(image)
            
            # =========================================
            # 第1段階: プロ撮影特徴を先に評価（優先）
            # =========================================
            pro_score, pro_reason = self._detect_professional_features_v2(image)
            if pro_score > 0.6:
                bonus = int(pro_score * 40)
                base_score += bonus
                result["reasons"].append(f"プロ撮影特徴 (確信度: {pro_score:.1%}): {pro_reason}")
                result["details"]["プロ撮影判定"] = {
                    "score": bonus,
                    "max_score": 40,
                    "reason": pro_reason
                }
                
                # プロ撮影が強く検出された場合、個人背景検出をスキップ
                skip_personal_bg = pro_score > 0.8
            else:
                skip_personal_bg = False
            
            # =========================================
            # 第2段階: 個人撮影背景の検出（条件付き）
            # =========================================
            if not skip_personal_bg and not is_white_bg:
                personal_bg_score, bg_reason = self._detect_personal_background_v2(image)
                if personal_bg_score > 0.8:  # 閾値を0.6→0.8に引き上げ
                    # ペナルティ方式に変更（上限キャップではなく）
                    penalty = int(personal_bg_score * 30)
                    base_score -= penalty
                    result["reasons"].append(f"個人撮影背景検出 (確信度: {personal_bg_score:.1%}): {bg_reason}")
                    result["details"]["背景判定"] = {
                        "score": -penalty,
                        "max_score": 0,
                        "reason": f"個人撮影背景ペナルティ: {bg_reason}"
                    }
            
            # =========================================
            # 第3段階: ROI抽出によるパッケージ判定
            # =========================================
            roi_result = self._extract_and_analyze_roi(image)
            if roi_result["has_roi"] and roi_result["package_face_score"] > 0.6:
                penalty = int(roi_result["package_face_score"] * 35)
                base_score -= penalty
                result["reasons"].append(
                    f"パッケージ面検出 (面積比: {roi_result['area_ratio']:.1%}, "
                    f"スコア: {roi_result['package_face_score']:.1%}): {roi_result['reason']}"
                )
                result["details"]["パッケージ面判定"] = {
                    "score": -penalty,
                    "max_score": 0,
                    "reason": roi_result['reason']
                }
            
            # =========================================
            # 第4段階: グローバルなパッケージ特徴
            # =========================================
            global_package_score, pkg_reason = self._detect_global_package_features(image)
            if global_package_score > 0.5:
                penalty = int(global_package_score * 20)
                base_score -= penalty
                result["reasons"].append(f"パッケージ特徴 (確信度: {global_package_score:.1%}): {pkg_reason}")
            
            # =========================================
            # 第5段階: ブリスターパック検出
            # =========================================
            blister_score, blister_reason = self._detect_blister_pack(image)
            if blister_score > 0.5:
                penalty = int(blister_score * 25)
                base_score -= penalty
                result["reasons"].append(f"ブリスターパック検出 (確信度: {blister_score:.1%}): {blister_reason}")
            
            # =========================================
            # 最終スコア計算
            # =========================================
            result["score"] = max(0, min(100, base_score))
            result["is_business"] = result["score"] >= self.business_threshold
            
            # 互換性のための詳細情報追加
            if "商品実物チェック" not in result["details"]:
                result["details"]["商品実物チェック"] = {
                    "score": max(0, min(30, base_score - 20)),
                    "max_score": 30,
                    "reason": "総合判定"
                }
            if "撮影品質チェック" not in result["details"]:
                result["details"]["撮影品質チェック"] = {
                    "score": max(0, min(20, base_score - 30)),
                    "max_score": 20,
                    "reason": "ROI判定優先"
                }
            if "販売努力チェック" not in result["details"]:
                result["details"]["販売努力チェック"] = {
                    "score": 0,
                    "max_score": 0,
                    "reason": "新方式のため省略"
                }

            self.logger.info(f"画像判定完了: {Path(image_path).name}")
            self.logger.info(f"  総合スコア: {result['score']}点 (閾値: {self.business_threshold})")
            self.logger.info(f"  判定結果: {'業者(OK)' if result['is_business'] else '個人(NG)'}")
            return result

        except Exception as e:
            result["error"] = f"分析エラー: {str(e)}"
            self.logger.error(f"画像分析エラー: {e}")
            return result

    def analyze_image_array(self, image: np.ndarray, filename: str = "memory_image") -> Dict:
        """RPA用：numpy配列からの分析"""
        result = {
            "file_name": filename,
            "timestamp": datetime.now().isoformat(),
            "is_business": False,
            "score": 0,
            "details": {},
            "reasons": [],
            "rule_results": {},
            "error": None,
            "source": "memory"
        }
        try:
            if image is None or image.size == 0:
                result["error"] = "無効な画像データ"
                return result

            h, w = image.shape[:2]
            max_side = max(h, w)
            max_size = self.config.get("image_analysis", {}).get("max_image_size", 1280)
            if max_side > max_size:
                scale = max_size / max_side
                image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

            base_score = 50
            is_white_bg = self._is_white_background(image)
            
            # プロ撮影特徴
            pro_score, pro_reason = self._detect_professional_features_v2(image)
            if pro_score > 0.6:
                bonus = int(pro_score * 40)
                base_score += bonus
                result["reasons"].append(f"プロ撮影: {pro_reason}")
                skip_personal_bg = pro_score > 0.8
            else:
                skip_personal_bg = False
            
            # 個人背景検出
            if not skip_personal_bg and not is_white_bg:
                personal_bg_score, bg_reason = self._detect_personal_background_v2(image)
                if personal_bg_score > 0.8:
                    penalty = int(personal_bg_score * 30)
                    base_score -= penalty
                    result["reasons"].append(f"個人撮影背景: {bg_reason}")
            
            # ROI判定
            roi_result = self._extract_and_analyze_roi(image)
            if roi_result["has_roi"] and roi_result["package_face_score"] > 0.6:
                penalty = int(roi_result["package_face_score"] * 35)
                base_score -= penalty
                result["reasons"].append(f"パッケージ面検出: {roi_result['reason']}")
            
            result["score"] = max(0, min(100, base_score))
            result["is_business"] = result["score"] >= self.business_threshold
            
            # 互換性のための詳細情報
            result["details"]["商品実物チェック"] = {"score": 0, "max_score": 30, "reason": "総合判定"}
            result["details"]["撮影品質チェック"] = {"score": 0, "max_score": 20, "reason": "ROI判定"}
            result["details"]["販売努力チェック"] = {"score": 0, "max_score": 0, "reason": "省略"}
            
            return result

        except Exception as e:
            result["error"] = f"メモリ画像分析エラー: {str(e)}"
            self.logger.error(f"メモリ画像分析エラー: {e}")
            return result

    def process_and_save_image(self, image_path: str) -> Dict:
        """分析して OK/NG フォルダへ移動/コピー"""
        result = self.analyze_single_image(image_path)
        try:
            source_path = Path(image_path)
            if not source_path.exists():
                result["error"] = "ファイルが存在しません"
                return result

            ok_folder = self.config.get("folders", {}).get("mercari_ok", "data/images/mercari_ok")
            ng_folder = self.config.get("folders", {}).get("mercari_ng", "data/images/mercari_ng")
            dest_folder = Path(ok_folder if result.get("is_business") else ng_folder)
            result["saved_to"] = "OK" if result.get("is_business") else "NG"

            dest_folder.mkdir(parents=True, exist_ok=True)
            stem, suffix = source_path.stem, source_path.suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = dest_folder / f"{stem}_{timestamp}{suffix}"
            if self.config.get("file_handling", {}).get("backup_original", True):
                shutil.copy2(source_path, dest_path)
            else:
                shutil.move(str(source_path), str(dest_path))
            result["final_path"] = str(dest_path)
            self.logger.info(f"画像処理完了: {result['saved_to']} -> {dest_path}")
        except Exception as e:
            result["error"] = f"ファイル処理エラー: {str(e)}"
            self.logger.error(f"ファイル処理エラー: {e}")
        return result

    def batch_analyze(self, image_folder: str) -> List[Dict]:
        folder_path = Path(image_folder)
        if not folder_path.exists():
            self.logger.error(f"フォルダが存在しません: {image_folder}")
            return []
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
        files = [p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() in exts]
        self.logger.info(f"一括分析開始: {len(files)}ファイル")
        results = [self.process_and_save_image(str(p)) for p in files]
        ok_count = sum(1 for r in results if r.get("is_business"))
        self.logger.info(f"一括分析完了: OK={ok_count}, NG={len(results)-ok_count}")
        return results

    # =========================================
    # 第0段階: 白背景の事前判定
    # =========================================
    def _is_white_background(self, image: np.ndarray) -> bool:
        """白背景かどうかの事前判定"""
        try:
            # 画像全体の平均明度
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            
            # 端20%領域の明度
            h, w = gray.shape
            border_size = int(min(h, w) * 0.2)
            
            border_regions = [
                gray[0:border_size, :],
                gray[h-border_size:h, :],
                gray[:, 0:border_size],
                gray[:, w-border_size:w]
            ]
            
            border_brightness = np.mean([np.mean(r) for r in border_regions])
            
            # 白背景の判定
            return mean_brightness > 180 and border_brightness > 200
            
        except Exception as e:
            self.logger.debug(f"白背景判定エラー: {e}")
            return False

    # =========================================
    # 第1段階: 改善版個人撮影背景検出
    # =========================================
    def _detect_personal_background_v2(self, image: np.ndarray) -> Tuple[float, str]:
        """改善版：個人撮影背景を検出（精度向上）"""
        scores = []
        reasons = []
        
        # 1. 木目テクスチャ検出（精密版）
        wood_score = self._detect_wood_texture_v2(image)
        if wood_score > 0.5:  # 閾値を上げる
            scores.append(wood_score)
            reasons.append(f"木目: {wood_score:.1%}")
        
        # 2. 畳・カーペット検出（白背景除外）
        if not self._is_white_background(image):
            periodic_score = self._detect_periodic_texture_v2(image)
            if periodic_score > 0.4:
                scores.append(periodic_score)
                reasons.append(f"畳/カーペット: {periodic_score:.1%}")
        
        # 3. 生活感のある雑然背景（エッジ密度ベース）
        cluttered_score = self._detect_real_clutter(image)
        if cluttered_score > 0.5:
            scores.append(cluttered_score)
            reasons.append(f"雑然背景: {cluttered_score:.1%}")
        
        # 複数の指標が同時に高い場合のみ高スコア
        if len(scores) >= 2:
            confidence = np.mean(scores)
        elif scores:
            confidence = max(scores) * 0.7  # 単一指標の場合は割引
        else:
            confidence = 0.0
        
        reason = ", ".join(reasons) if reasons else "個人撮影背景なし"
        return confidence, reason
    
    def _detect_wood_texture_v2(self, image: np.ndarray) -> float:
        """改善版：木目テクスチャの検出（色調必須）"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # 茶色系の色調チェック（必須）
            h_channel = hsv[:, :, 0]
            s_channel = hsv[:, :, 1]
            v_channel = hsv[:, :, 2]
            
            # 茶色の範囲（Hue: 10-30, Saturation: 30以上）
            brown_mask = (h_channel >= 10) & (h_channel <= 30) & (s_channel > 30) & (v_channel > 50)
            brown_ratio = np.mean(brown_mask)
            
            if brown_ratio < 0.2:  # 茶色が少ない場合は木目ではない
                return 0.0
            
            # 方向性のある線の検出
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            x_strength = np.mean(np.abs(grad_x))
            y_strength = np.mean(np.abs(grad_y))
            
            # 一方向の線が強い
            directionality = 0.0
            if x_strength > y_strength * 1.5:
                directionality = 0.4
            elif y_strength > x_strength * 1.5:
                directionality = 0.4
            
            # FFTで周期性
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude_spectrum = np.log(np.abs(f_shift) + 1)
            
            # 特定周波数帯でのピーク（木目の周期性）
            h, w = magnitude_spectrum.shape
            cy, cx = h // 2, w // 2
            
            # リング状の領域でエネルギーを計算
            y, x = np.ogrid[:h, :w]
            dist_from_center = np.sqrt((x - cx)**2 + (y - cy)**2)
            
            ring_mask = (dist_from_center > min(h, w) * 0.1) & (dist_from_center < min(h, w) * 0.3)
            ring_energy = np.mean(magnitude_spectrum[ring_mask])
            
            periodicity = min(ring_energy / 15, 0.3)
            
            score = brown_ratio + directionality + periodicity
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.debug(f"木目テクスチャ検出エラー: {e}")
            return 0.0
    
    def _detect_periodic_texture_v2(self, image: np.ndarray) -> float:
        """改善版：畳/カーペット検出（白背景除外）"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 明度チェック（白っぽい場合はスキップ）
            if np.mean(gray) > 200:
                return 0.0
            
            # ガボールフィルタで周期的パターン検出
            ksize = 31
            sigma = 4.0
            theta = 0
            lamda = 10.0
            gamma = 0.5
            
            scores = []
            for theta in [0, np.pi/4, np.pi/2, 3*np.pi/4]:
                kernel = cv2.getGaborKernel((ksize, ksize), sigma, theta, lamda, gamma, 0, ktype=cv2.CV_32F)
                filtered = cv2.filter2D(gray, cv2.CV_32F, kernel)
                response = np.mean(np.abs(filtered))
                scores.append(response)
            
            # 最大応答
            max_response = max(scores) / 255.0
            
            # 繰り返しパターンの検出
            edges = cv2.Canny(gray, 30, 100)
            
            # 水平・垂直方向の投影
            h_projection = np.mean(edges, axis=1)
            v_projection = np.mean(edges, axis=0)
            
            # FFTで周期性を確認
            h_fft = np.fft.fft(h_projection)
            v_fft = np.fft.fft(v_projection)
            
            # 周期的ピークの検出
            h_peaks = self._find_periodic_peaks(np.abs(h_fft))
            v_peaks = self._find_periodic_peaks(np.abs(v_fft))
            
            periodicity = (h_peaks + v_peaks) / 2
            
            score = max_response * 0.5 + periodicity * 0.5
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.debug(f"周期テクスチャ検出エラー: {e}")
            return 0.0
    
    def _find_periodic_peaks(self, spectrum: np.ndarray) -> float:
        """FFTスペクトラムから周期的ピークを検出"""
        try:
            # DC成分を除く
            spectrum = spectrum[1:len(spectrum)//2]
            if len(spectrum) == 0:
                return 0.0
            
            # ピーク検出
            mean_val = np.mean(spectrum)
            std_val = np.std(spectrum)
            threshold = mean_val + 2 * std_val
            
            peaks = spectrum > threshold
            peak_count = np.sum(peaks)
            
            # 周期性スコア
            if peak_count > 2 and peak_count < 10:
                return 0.8
            elif peak_count > 0:
                return 0.4
            else:
                return 0.0
                
        except:
            return 0.0
    
    def _detect_real_clutter(self, image: np.ndarray) -> float:
        """実際の雑然とした背景を検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # エッジの複雑さ
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.mean(edges > 0)
            
            # エッジが散在している（商品以外の物が多い）
            h, w = gray.shape
            grid_size = 8
            cell_h = h // grid_size
            cell_w = w // grid_size
            
            edge_distribution = []
            for i in range(grid_size):
                for j in range(grid_size):
                    cell = edges[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
                    edge_distribution.append(np.mean(cell > 0))
            
            # エッジが均等に分布している = 雑然
            distribution_std = np.std(edge_distribution)
            
            # 小物体の数
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            small_objects = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 100 < area < 2000:
                    small_objects += 1
            
            object_score = min(small_objects / 20, 0.5)
            
            # 中央と周辺のエッジ密度差が小さい = 背景にも物がある
            center_edges = edges[h//4:3*h//4, w//4:3*w//4]
            center_density = np.mean(center_edges > 0)
            
            if edge_density > 0:
                uniformity = 1.0 - abs(center_density - edge_density) / edge_density
            else:
                uniformity = 0.0
            
            score = edge_density * 2 + (1.0 - distribution_std) * 0.3 + object_score + uniformity * 0.2
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.debug(f"雑然背景検出エラー: {e}")
            return 0.0

    # =========================================
    # 第2段階: 改善版プロ撮影特徴検出
    # =========================================
    def _safe_detect(self, detect_func, image):
        """安全な特徴検出（例外をキャッチ）"""
        try:
            return detect_func(image)
        except Exception as e:
            self.logger.debug(f"{detect_func.__name__} 例外: {e}")
            return 0.0
    
    def _detect_professional_features_v2(self, image: np.ndarray) -> Tuple[float, str]:
        """改善版：プロ撮影特徴の検出（異種2項目ゲート）"""
        background_scores = {}
        composition_scores = {}
        reasons = []
        
        # === 背景系の特徴（セーフガード付き）===
        
        # 1. クリーン背景
        clean_bg = self._safe_detect(self._detect_clean_background_v2, image)
        if clean_bg > 0:
            background_scores["clean"] = clean_bg
            if clean_bg > 0.5:
                reasons.append(f"クリーン背景: {clean_bg:.1%}")
        
        # 2. 均一な照明
        uniform_lighting = self._safe_detect(self._detect_uniform_lighting, image)
        if uniform_lighting > 0:
            background_scores["lighting"] = uniform_lighting
            if uniform_lighting > 0.5:
                reasons.append(f"均一照明: {uniform_lighting:.1%}")
        
        # 3. 色調の一貫性（追加）
        color_cons = self._safe_detect(self._detect_color_consistency, image)
        if color_cons > 0:
            background_scores["color"] = color_cons
            if color_cons > 0.5:
                reasons.append(f"色調一貫: {color_cons:.1%}")
        
        # === 構図系の特徴（セーフガード付き）===
        
        # 4. エッジの鮮明さ（比率評価）
        edge_quality = self._safe_detect(self._detect_sharp_edges, image)
        if edge_quality > 0:
            composition_scores["edges"] = edge_quality
            if edge_quality > 0.4:
                reasons.append(f"鮮明エッジ: {edge_quality:.1%}")
        
        # 5. 中央配置と構図
        composition = self._safe_detect(self._detect_professional_composition, image)
        if composition > 0:
            composition_scores["center"] = composition
            if composition > 0.5:
                reasons.append(f"プロ構図: {composition:.1%}")
        
        # 6. プロ的な影
        shadow_quality = self._safe_detect(self._detect_professional_shadow, image)
        if shadow_quality > 0:
            composition_scores["shadow"] = shadow_quality
            if shadow_quality > 0.4:
                reasons.append(f"プロ影: {shadow_quality:.1%}")
        
        # 7. 商品の切り抜き感
        cutout_quality = self._safe_detect(self._detect_cutout_quality, image)
        if cutout_quality > 0:
            composition_scores["cutout"] = cutout_quality
            if cutout_quality > 0.4:
                reasons.append(f"切り抜き感: {cutout_quality:.1%}")
        
        # 8. 複数アングル合成（追加）
        multi_angle = self._safe_detect(self._detect_multi_angle_composite, image)
        if multi_angle > 0:
            composition_scores["multi"] = multi_angle
            if multi_angle > 0.4:
                reasons.append(f"多アングル: {multi_angle:.1%}")
        
        # === 異種2項目ゲートによる判定 ===
        
        # 背景系の最高スコア
        max_bg = max(background_scores.values()) if background_scores else 0.0
        # 構図系の最高スコア
        max_comp = max(composition_scores.values()) if composition_scores else 0.0
        
        # 両系統で一定以上のスコアがある場合のみプロ判定
        if max_bg > 0.5 and max_comp > 0.5:
            # 信頼度ウェイトによる加重平均
            bg_weight = min(max_bg, 1.0)
            comp_weight = min(max_comp, 1.0)
            
            # スコア計算（最大1.0になるよう正規化）
            confidence = (bg_weight * 0.5 + comp_weight * 0.5)
            
            # 追加ボーナス：両方が高い場合
            if max_bg > 0.7 and max_comp > 0.7:
                confidence = min(confidence * 1.1, 1.0)
            
        elif max_bg > 0.8 or max_comp > 0.8:
            # 片方が非常に高い場合は部分的に評価
            confidence = max(max_bg, max_comp) * 0.6
        else:
            confidence = 0.0
        
        reason = ", ".join(reasons) if reasons else "プロ撮影特徴なし"
        return confidence, reason
    
    def _detect_uniform_lighting(self, image: np.ndarray) -> float:
        """均一な照明の検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # グリッドに分割（4x4）
            grid_size = 4
            cell_h = h // grid_size
            cell_w = w // grid_size
            
            # 各セルの明度を計算
            cell_means = []
            for i in range(grid_size):
                for j in range(grid_size):
                    cell = gray[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
                    if cell.size > 0:
                        cell_means.append(np.mean(cell))
            
            if not cell_means:
                return 0.0
            
            # 明度の分散を評価
            mean_brightness = np.mean(cell_means)
            std_brightness = np.std(cell_means)
            
            # 変動係数（低いほど均一）
            if mean_brightness > 0:
                cv = std_brightness / mean_brightness
                uniformity = max(0, 1.0 - cv * 2)
            else:
                uniformity = 0.0
            
            # グラデーションチェック（上下左右の差）
            top_mean = np.mean(gray[0:h//4, :])
            bottom_mean = np.mean(gray[3*h//4:h, :])
            left_mean = np.mean(gray[:, 0:w//4])
            right_mean = np.mean(gray[:, w-w//4:w])
            
            # 各方向の差が小さいほど均一
            vertical_diff = abs(top_mean - bottom_mean)
            horizontal_diff = abs(left_mean - right_mean)
            
            gradient_penalty = 0.0
            if vertical_diff > 30 or horizontal_diff > 30:
                gradient_penalty = 0.3
            elif vertical_diff > 20 or horizontal_diff > 20:
                gradient_penalty = 0.1
            
            return max(0, uniformity - gradient_penalty)
            
        except Exception as e:
            self.logger.debug(f"均一照明検出エラー: {e}")
            return 0.0
    
    def _detect_sharp_edges(self, image: np.ndarray) -> float:
        """エッジの鮮明さを検出（中央/外周の比率で評価）"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # 中央50%領域（前景）
            cy1, cy2 = int(h * 0.25), int(h * 0.75)
            cx1, cx2 = int(w * 0.25), int(w * 0.75)
            center_region = gray[cy1:cy2, cx1:cx2]
            
            # 外周20%リング領域（背景）
            mask = np.ones_like(gray, dtype=bool)
            inner_margin = int(min(h, w) * 0.2)
            mask[inner_margin:h-inner_margin, inner_margin:w-inner_margin] = False
            ring_region = gray[mask]
            
            # ラプラシアンの分散を計算
            center_lap = cv2.Laplacian(center_region, cv2.CV_64F)
            center_var = np.var(center_lap)
            
            if ring_region.size > 0:
                # リング領域のラプラシアン分散
                ring_gray = gray.copy()
                ring_gray[~mask] = 0
                ring_lap = cv2.Laplacian(ring_gray, cv2.CV_64F)
                ring_lap = ring_lap[mask]
                ring_var = np.var(ring_lap)
                
                # 比率計算（中央/外周）
                sharp_ratio = center_var / (ring_var + 1e-6)
                
                # 比率が2.0以上なら鮮明
                if sharp_ratio > 2.0:
                    return min(sharp_ratio / 4.0, 1.0)  # 正規化
                else:
                    return sharp_ratio / 2.0
            else:
                # リング領域がない場合は中央の絶対値で評価
                return min(center_var / 500, 1.0)
            
        except Exception as e:
            self.logger.debug(f"エッジ鮮明度検出エラー: {e}")
            return 0.0
    
    def _detect_color_consistency(self, image: np.ndarray) -> float:
        """色調の一貫性を検出"""
        try:
            # HSV変換
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, w = hsv.shape[:2]
            
            # 中央と周辺の色調を比較
            center = hsv[h//3:2*h//3, w//3:2*w//3]
            
            # 背景領域（四隅）
            corner_size = min(50, h//10, w//10)
            corners = [
                hsv[0:corner_size, 0:corner_size],
                hsv[0:corner_size, w-corner_size:w],
                hsv[h-corner_size:h, 0:corner_size],
                hsv[h-corner_size:h, w-corner_size:w]
            ]
            
            # 彩度が低い領域は背景の可能性が高い
            bg_saturations = []
            for corner in corners:
                mean_saturation = np.mean(corner[:,:,1])
                bg_saturations.append(mean_saturation)
            
            # 背景の彩度が低い（単色）
            avg_bg_saturation = np.mean(bg_saturations)
            
            # 中央の物体は彩度がある
            center_saturation = np.mean(center[:,:,1])
            
            # 色調の一貫性スコア
            if avg_bg_saturation < 30:  # 背景が単色
                consistency_score = 0.8
            elif avg_bg_saturation < 50:
                consistency_score = 0.6
            else:
                consistency_score = 0.3
            
            # 中央に物体がある
            if center_saturation > avg_bg_saturation:
                consistency_score += 0.2
            
            return min(consistency_score, 1.0)
            
        except Exception as e:
            self.logger.debug(f"色調一貫性検出エラー: {e}")
            return 0.0
    
    def _detect_clean_background_v2(self, image: np.ndarray) -> float:
        """改善版：クリーン背景検出（外枠除外・色差チェック付き）"""
        try:
            h, w = image.shape[:2]
            
            # 外枠5%を除外してから角を取得
            margin = int(min(h, w) * 0.05)
            corner_size = min(50, int(min(h, w) * 0.1))
            
            # 四隅を取得（外枠除外済み）
            corners = [
                image[margin:margin+corner_size, margin:margin+corner_size],
                image[margin:margin+corner_size, w-margin-corner_size:w-margin],
                image[h-margin-corner_size:h-margin, margin:margin+corner_size],
                image[h-margin-corner_size:h-margin, w-margin-corner_size:w-margin]
            ]
            
            # 各コーナーの情報を統一管理
            corner_infos = []
            for corner in corners:
                if corner.size == 0:
                    continue
                if len(corner.shape) == 3:
                    std_val = np.mean([np.std(corner[:,:,i]) for i in range(3)])
                    mean_color = np.mean(corner, axis=(0,1)).astype(np.float32)
                    mean_val = float(np.mean(corner))
                else:
                    std_val = float(np.std(corner))
                    mean_color = np.array([np.mean(corner)], dtype=np.float32)
                    mean_val = float(np.mean(corner))
                corner_infos.append((std_val, mean_val, mean_color))
            
            if len(corner_infos) < 2:
                return 0.0
            
            # 標準偏差の小さい順にソート
            corner_infos.sort(key=lambda x: x[0])
            best = corner_infos[:2]
            
            # 2隅の色差チェック
            color_diff = float(np.linalg.norm(best[0][2] - best[1][2]))
            if color_diff > 30:
                return 0.0
            
            avg_std = np.mean([b[0] for b in best])
            avg_brightness = np.mean([b[1] for b in best])
            
            # 均一性スコア（標準偏差ベース）
            if avg_std < 20:
                uniformity = 1.0
            elif avg_std < 35:
                uniformity = 0.8
            elif avg_std < 50:
                uniformity = 0.6
            elif avg_std < 65:
                uniformity = 0.4
            else:
                uniformity = 0.0
            
            # 変動係数を考慮
            cv = avg_std / (avg_brightness + 1e-6)
            
            # 最終スコア
            clean_score = 0.7 * uniformity + 0.3 * max(0, 1.0 - cv)
            
            return min(clean_score, 1.0)
            
        except Exception as e:
            self.logger.debug(f"クリーン背景検出エラー: {e}")
            return 0.0
    
    def _detect_cutout_quality(self, image: np.ndarray) -> float:
        """商品の切り抜き感を検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # エッジの鮮明さ
            edges = cv2.Canny(gray, 50, 150)
            
            # 輪郭の滑らかさ
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return 0.0
            
            # 最大輪郭
            largest_contour = max(contours, key=cv2.contourArea)
            
            # 輪郭の滑らかさ（凸包との差）
            hull = cv2.convexHull(largest_contour)
            hull_area = cv2.contourArea(hull)
            contour_area = cv2.contourArea(largest_contour)
            
            if hull_area > 0:
                smoothness = contour_area / hull_area
            else:
                smoothness = 0.0
            
            # エッジの連続性
            perimeter = cv2.arcLength(largest_contour, True)
            if perimeter > 0:
                compactness = 4 * np.pi * contour_area / (perimeter ** 2)
            else:
                compactness = 0.0
            
            score = smoothness * 0.5 + compactness * 0.5
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.debug(f"切り抜き品質検出エラー: {e}")
            return 0.0
    
    def _detect_multi_angle_composite(self, image: np.ndarray) -> float:
        """複数アングルの合成を検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 複数の物体を検出
            edges = cv2.Canny(gray, 30, 100)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 一定サイズ以上の物体
            significant_objects = []
            total_area = gray.shape[0] * gray.shape[1]
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > total_area * 0.02:  # 画像の2%以上
                    significant_objects.append(cnt)
            
            if len(significant_objects) >= 3:
                # 物体の配置パターンを確認
                centers = []
                for cnt in significant_objects:
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        centers.append((cx, cy))
                
                if len(centers) >= 3:
                    # 配置の規則性を確認
                    x_coords = [c[0] for c in centers]
                    y_coords = [c[1] for c in centers]
                    
                    # 水平または垂直に整列しているか
                    x_std = np.std(x_coords)
                    y_std = np.std(y_coords)
                    
                    h, w = gray.shape
                    
                    if x_std < w * 0.05 or y_std < h * 0.05:
                        return 0.2  # 整列していない（自然な配置ではない）
                    else:
                        return 0.8  # 意図的な配置
            
            elif len(significant_objects) == 2:
                return 0.5
            
            return 0.0
            
        except Exception as e:
            self.logger.debug(f"複数アングル検出エラー: {e}")
            return 0.0
    
    def _detect_professional_shadow(self, image: np.ndarray) -> float:
        """プロ的な影の検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # 下部1/3領域で影を探す
            bottom_region = gray[2*h//3:h, :]
            
            # 暗い領域
            _, shadow_mask = cv2.threshold(bottom_region, 100, 255, cv2.THRESH_BINARY_INV)
            
            # 影の形状を確認
            contours, _ = cv2.findContours(shadow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 500:
                    # 楕円フィット
                    if len(cnt) >= 5:
                        ellipse = cv2.fitEllipse(cnt)
                        # 楕円の縦横比
                        aspect_ratio = min(ellipse[1]) / max(ellipse[1]) if max(ellipse[1]) > 0 else 0
                        
                        # ドロップシャドウらしい形状
                        if 0.2 < aspect_ratio < 0.8:
                            # グラデーション確認
                            x, y, w_cnt, h_cnt = cv2.boundingRect(cnt)
                            if h_cnt > 0:
                                shadow_region = bottom_region[y:y+h_cnt, x:x+w_cnt]
                                gradient = np.std(shadow_region)
                                
                                if gradient > 10 and gradient < 50:
                                    return 0.9
            
            # 全体的なグラデーション影
            vertical_gradient = np.mean(gray[h//2:h, :]) - np.mean(gray[0:h//2, :])
            if -30 < vertical_gradient < -5:  # 下が暗い
                return 0.6
            
            return 0.0
            
        except Exception as e:
            self.logger.debug(f"プロ影検出エラー: {e}")
            return 0.0
    
    def _detect_professional_composition(self, image: np.ndarray) -> float:
        """プロ的な構図の検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # 中央領域のエッジ密度
            center_region = gray[h//3:2*h//3, w//3:2*w//3]
            center_edges = cv2.Canny(center_region, 50, 150)
            center_density = np.mean(center_edges > 0)
            
            # 周辺領域のエッジ密度
            border_mask = np.ones_like(gray, dtype=bool)
            border_mask[h//3:2*h//3, w//3:2*w//3] = False
            border_edges = cv2.Canny(gray, 50, 150)
            border_edges[~border_mask] = 0
            border_density = np.mean(border_edges[border_mask] > 0)
            
            # 中央に集中している
            if center_density > border_density * 3:
                composition_score = 0.8
            elif center_density > border_density * 2:
                composition_score = 0.6
            elif center_density > border_density * 1.5:
                composition_score = 0.4
            else:
                composition_score = 0.0
            
            # 対称性チェック
            left_half = gray[:, :w//2]
            right_half = cv2.flip(gray[:, w//2:], 1)
            
            if left_half.shape == right_half.shape:
                symmetry = 1.0 - np.mean(np.abs(left_half - right_half)) / 255.0
                symmetry_bonus = symmetry * 0.2 if symmetry > 0.7 else 0.0
            else:
                symmetry_bonus = 0.0
            
            return min(composition_score + symmetry_bonus, 1.0)
            
        except Exception as e:
            self.logger.debug(f"構図検出エラー: {e}")
            return 0.0

    # =========================================
    # 既存メソッド（ROI、パッケージ、ブリスター）
    # =========================================
    def _extract_and_analyze_roi(self, image: np.ndarray) -> Dict:
        """最大矩形領域を抽出してパッケージ面を判定"""
        result = {
            "has_roi": False,
            "area_ratio": 0.0,
            "package_face_score": 0.0,
            "reason": "ROI未検出"
        }
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            image_area = h * w
            
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return result
            
            best_roi = None
            best_score = 0
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < image_area * 0.1:
                    continue
                
                epsilon = 0.02 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                
                if len(approx) == 4:
                    rect = cv2.minAreaRect(cnt)
                    rect_area = rect[1][0] * rect[1][1]
                    if rect_area > 0:
                        rectangularity = area / rect_area
                        
                        if rectangularity > 0.8:
                            area_ratio = area / image_area
                            if area_ratio > 0.25:
                                x, y, w_roi, h_roi = cv2.boundingRect(approx)
                                roi = image[y:y+h_roi, x:x+w_roi]
                                
                                face_score = self._analyze_package_face(roi)
                                
                                if face_score > best_score:
                                    best_score = face_score
                                    best_roi = {
                                        "roi": roi,
                                        "area_ratio": area_ratio,
                                        "rectangularity": rectangularity
                                    }
            
            if best_roi and best_score > 0.3:
                result["has_roi"] = True
                result["area_ratio"] = best_roi["area_ratio"]
                result["package_face_score"] = best_score
                
                reasons = []
                if best_score > 0.7:
                    reasons.append("強いパッケージ特徴")
                elif best_score > 0.5:
                    reasons.append("中程度のパッケージ特徴")
                
                result["reason"] = ", ".join(reasons) if reasons else "パッケージ面検出"
            
            return result
            
        except Exception as e:
            self.logger.debug(f"ROI抽出エラー: {e}")
            return result
    
    def _analyze_package_face(self, roi: np.ndarray) -> float:
        """ROI内のパッケージ特徴を分析"""
        scores = []
        
        text_density = self._calculate_roi_text_density(roi)
        if text_density > 0.2:
            scores.append(text_density * 2)
        
        icon_score = self._detect_icon_row(roi)
        if icon_score > 0.3:
            scores.append(icon_score)
        
        barcode_score = self._detect_barcode(roi)
        if barcode_score > 0.5:
            scores.append(barcode_score)
        
        multicolor_score = self._detect_multicolor_print(roi)
        if multicolor_score > 0.4:
            scores.append(multicolor_score)
        
        flatness = self._calculate_flatness(roi)
        if flatness > 0.6:
            scores.append(flatness)
        
        if len(scores) >= 3:
            return np.mean(scores)
        elif len(scores) >= 2 and max(scores) > 0.7:
            return np.mean(scores)
        elif scores:
            return max(scores) * 0.7
        else:
            return 0.0
    
    def _calculate_roi_text_density(self, roi: np.ndarray) -> float:
        """ROI内のテキスト密度計算"""
        try:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
            
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
            kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
            
            h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_h)
            v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_v)
            
            text_mask = cv2.bitwise_or(h_lines, v_lines)
            text_ratio = np.mean(text_mask > 0)
            
            return min(text_ratio * 2, 1.0)
            
        except Exception as e:
            self.logger.debug(f"ROIテキスト密度エラー: {e}")
            return 0.0
    
    def _detect_icon_row(self, roi: np.ndarray) -> float:
        """アイコンの横並びを検出"""
        try:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
            
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            icons = []
            for cnt in contours:
                x, y, w_cnt, h_cnt = cv2.boundingRect(cnt)
                aspect_ratio = w_cnt / h_cnt if h_cnt > 0 else 0
                
                if 0.7 < aspect_ratio < 1.3 and 20 < w_cnt < 100 and 20 < h_cnt < 100:
                    icons.append((x, y, w_cnt, h_cnt))
            
            if len(icons) >= 3:
                icons.sort(key=lambda i: i[1])
                same_row = []
                current_y = icons[0][1]
                
                for icon in icons:
                    if abs(icon[1] - current_y) < 20:
                        same_row.append(icon)
                    else:
                        if len(same_row) >= 3:
                            return 1.0
                        same_row = [icon]
                        current_y = icon[1]
                
                if len(same_row) >= 3:
                    return 1.0
            
            return 0.0
            
        except Exception as e:
            self.logger.debug(f"アイコン列検出エラー: {e}")
            return 0.0
    
    def _detect_barcode(self, roi: np.ndarray) -> float:
        """バーコードの検出"""
        try:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
            
            kernel = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
            vertical_lines = cv2.filter2D(gray, cv2.CV_32F, kernel)
            vertical_lines = np.abs(vertical_lines)
            
            h, w = vertical_lines.shape
            for y in range(0, h - 30):
                region = vertical_lines[y:y+30, :]
                profile = np.mean(region, axis=0)
                
                peaks = []
                for i in range(1, len(profile) - 1):
                    if profile[i] > profile[i-1] and profile[i] > profile[i+1]:
                        peaks.append(i)
                
                if len(peaks) > 10:
                    intervals = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
                    if intervals:
                        std_interval = np.std(intervals)
                        mean_interval = np.mean(intervals)
                        if mean_interval > 0 and std_interval / mean_interval < 0.3:
                            return 1.0
            
            return 0.0
            
        except Exception as e:
            self.logger.debug(f"バーコード検出エラー: {e}")
            return 0.0
    
    def _detect_multicolor_print(self, roi: np.ndarray) -> float:
        """多色印刷の検出"""
        try:
            if len(roi.shape) == 2:
                return 0.0
            
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            
            h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            h_hist = h_hist.flatten() / h_hist.sum()
            
            h_hist_nz = h_hist[h_hist > 0]
            h_entropy = -np.sum(h_hist_nz * np.log2(h_hist_nz))
            
            high_saturation = hsv[:, :, 1] > 150
            saturation_ratio = np.mean(high_saturation)
            
            score = (h_entropy / 7.0) * 0.6 + saturation_ratio * 0.4
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.debug(f"多色印刷検出エラー: {e}")
            return 0.0
    
    def _calculate_flatness(self, roi: np.ndarray) -> float:
        """平面性の計算"""
        try:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
            
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            low_gradient = gradient_magnitude < 20
            flat_ratio = np.mean(low_gradient)
            
            shadows = gray < 50
            shadow_ratio = 1.0 - np.mean(shadows)
            
            highlights = gray > 200
            highlight_ratio = 1.0 - np.mean(highlights)
            
            flatness = flat_ratio * 0.4 + shadow_ratio * 0.3 + highlight_ratio * 0.3
            return min(flatness, 1.0)
            
        except Exception as e:
            self.logger.debug(f"平面性計算エラー: {e}")
            return 0.0

    def _detect_global_package_features(self, image: np.ndarray) -> Tuple[float, str]:
        """画像全体でのパッケージ特徴検出"""
        scores = []
        reasons = []
        
        text_density = self._calculate_global_text_density(image)
        if text_density > 0.15:
            scores.append(text_density * 2)
            reasons.append(f"テキスト: {text_density:.1%}")
        
        rect_score = self._detect_rectangular_layout(image)
        if rect_score > 0.3:
            scores.append(rect_score)
            reasons.append(f"矩形構造: {rect_score:.1%}")
        
        if scores:
            confidence = np.mean(scores)
            reason = ", ".join(reasons)
        else:
            confidence = 0.0
            reason = "パッケージ特徴なし"
        
        return confidence, reason
    
    def _calculate_global_text_density(self, image: np.ndarray) -> float:
        """全体的なテキスト密度"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 200)
            
            kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
            kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
            
            h_lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_h)
            v_lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_v)
            
            text_areas = cv2.bitwise_or(h_lines, v_lines)
            return float(np.mean(text_areas > 0))
            
        except Exception as e:
            self.logger.debug(f"グローバルテキスト密度エラー: {e}")
            return 0.0
    
    def _detect_rectangular_layout(self, image: np.ndarray) -> float:
        """矩形レイアウトの検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=50, maxLineGap=10)
            
            if lines is None:
                return 0.0
            
            horizontal = 0
            vertical = 0
            
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                
                if angle < 10 or angle > 170:
                    horizontal += 1
                elif 80 < angle < 100:
                    vertical += 1
            
            if len(lines) > 0:
                rect_ratio = (horizontal + vertical) / len(lines)
                return min(rect_ratio, 1.0)
            
            return 0.0
            
        except Exception as e:
            self.logger.debug(f"矩形レイアウト検出エラー: {e}")
            return 0.0

    def _detect_blister_pack(self, image: np.ndarray) -> Tuple[float, str]:
        """ブリスターパック（透明包装）の検出"""
        scores = []
        reasons = []
        
        hang_hole = self._detect_hang_hole(image)
        if hang_hole > 0.5:
            scores.append(hang_hole)
            reasons.append("吊り下げ穴")
        
        plastic_reflection = self._detect_plastic_reflection(image)
        if plastic_reflection > 0.3:
            scores.append(plastic_reflection)
            reasons.append(f"プラ反射: {plastic_reflection:.1%}")
        
        two_layer = self._detect_two_layer_structure(image)
        if two_layer > 0.4:
            scores.append(two_layer)
            reasons.append("二層構造")
        
        if scores:
            confidence = max(scores)
            reason = ", ".join(reasons)
        else:
            confidence = 0.0
            reason = ""
        
        return confidence, reason
    
    def _detect_hang_hole(self, image: np.ndarray) -> float:
        """吊り下げ穴の検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            top_region = gray[0:h//4, w//3:2*w//3]
            
            circles = cv2.HoughCircles(
                top_region, 
                cv2.HOUGH_GRADIENT, 
                1, 
                20,
                param1=50, 
                param2=30, 
                minRadius=10, 
                maxRadius=50
            )
            
            if circles is not None:
                return 1.0
            
            edges = cv2.Canny(top_region, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 100 < area < 2000:
                    perimeter = cv2.arcLength(cnt, True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                        if circularity > 0.5:
                            return 0.8
            
            return 0.0
            
        except Exception as e:
            self.logger.debug(f"吊り下げ穴検出エラー: {e}")
            return 0.0
    
    def _detect_plastic_reflection(self, image: np.ndarray) -> float:
        """プラスチックの反射検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            highlights = (gray > 230).astype(np.uint8)
            
            contours, _ = cv2.findContours(highlights, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            reflection_spots = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 5 < area < 200:
                    reflection_spots += 1
            
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            high_freq = np.var(laplacian)
            
            score = min(reflection_spots / 50, 0.5) + min(high_freq / 1000, 0.5)
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.debug(f"プラ反射検出エラー: {e}")
            return 0.0
    
    def _detect_two_layer_structure(self, image: np.ndarray) -> float:
        """台紙＋商品の二層構造検出"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            edges = cv2.Canny(gray, 50, 150)
            
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if len(contours) < 2:
                return 0.0
            
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            area1 = cv2.contourArea(contours[0])
            area2 = cv2.contourArea(contours[1])
            
            total_area = gray.shape[0] * gray.shape[1]
            
            if area1 > total_area * 0.2 and area2 > total_area * 0.1:
                rect1 = cv2.boundingRect(contours[0])
                rect2 = cv2.boundingRect(contours[1])
                
                x_overlap = max(0, min(rect1[0] + rect1[2], rect2[0] + rect2[2]) - max(rect1[0], rect2[0]))
                y_overlap = max(0, min(rect1[1] + rect1[3], rect2[1] + rect2[3]) - max(rect1[1], rect2[1]))
                
                if x_overlap > 0 and y_overlap > 0:
                    overlap_area = x_overlap * y_overlap
                    if overlap_area > min(area1, area2) * 0.3:
                        return 0.8
            
            return 0.0
            
        except Exception as e:
            self.logger.debug(f"二層構造検出エラー: {e}")
            return 0.0