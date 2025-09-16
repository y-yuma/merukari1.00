"""
画像判定モジュール（完成版）
- ハードNGルール（パッケージ単体 / 袋・シュリンク）を優先
- ベンダー合成スタイルはボーナス（OK寄りだがハードOKではない）
- 従来の3指標（実物/品質/努力）を維持しつつスコア計算を安定化
- np.int0 の非推奨対策 / _estimate_corner_uniformity 追加
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
            .get("business_threshold", 70)
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

            # まずハードNGルールの判定（優先）
            hard_ng_triggered = self._apply_hard_rules(image, result)
            if hard_ng_triggered:
                # ハードNGの場合はスコアに関係なくNG確定
                result["score"] = 0
                result["is_business"] = False
                self.logger.info(f"画像判定完了: {Path(image_path).name}")
                self.logger.info(f"  総合スコア: {result['score']}点 (閾値: {self.business_threshold})")
                self.logger.info("  判定結果: 個人(NG) [ハードルール]")
                return result

            # スコアリング（3指標）
            total_score = self._execute_analysis_checks(image, result)

            # ベンダー合成っぽい→ボーナス（任意）
            bonus = self._maybe_vendor_composite_bonus(image, result)
            total_score = min(100, total_score + bonus)

            result["score"] = int(round(total_score))
            result["is_business"] = result["score"] >= self.business_threshold

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

            # リサイズ同等処理
            h, w = image.shape[:2]
            max_side = max(h, w)
            max_size = self.config.get("image_analysis", {}).get("max_image_size", 1280)
            if max_side > max_size:
                scale = max_size / max_side
                image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

            # ハードNG
            if self._apply_hard_rules(image, result):
                result["score"] = 0
                result["is_business"] = False
                return result

            total_score = self._execute_analysis_checks(image, result)
            bonus = self._maybe_vendor_composite_bonus(image, result)
            total_score = min(100, total_score + bonus)

            result["score"] = int(round(total_score))
            result["is_business"] = result["score"] >= self.business_threshold
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
            # 同名衝突回避
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

    # -------------------------
    # ハードNG & ボーナス
    # -------------------------
    def _apply_hard_rules(self, image: np.ndarray, result: Dict) -> bool:
        """設定ルールに基づくハードNG判定。Trueなら即NG確定。"""
        rules_cfg = (
            self.config.get("image_analysis", {})
            .get("rules", {})
        )
        enabled = rules_cfg.get("enabled", [])

        hard_ng = False
        result["rule_results"] = {}

        # 1) パッケージ/箱のみ
        if "package_only" in enabled and rules_cfg.get("package_only", {}).get("enabled", True):
            pkg_hit, reason = self._detect_package_only(image, rules_cfg.get("package_only", {}))
            result["rule_results"]["package_only"] = bool(pkg_hit)
            if pkg_hit and rules_cfg.get("package_only", {}).get("hard_ng", True):
                result["reasons"].append(f"ハードNG: パッケージ/箱のみが強く示唆 - {reason}")
                hard_ng = True

        # 2) 袋・シュリンク
        if not hard_ng and "bag_or_shrinkwrap" in enabled and rules_cfg.get("bag_or_shrinkwrap", {}).get("enabled", True):
            bag_hit, reason = self._detect_bag_or_shrinkwrap(image, rules_cfg.get("bag_or_shrinkwrap", {}))
            result["rule_results"]["bag_or_shrinkwrap"] = bool(bag_hit)
            if bag_hit and rules_cfg.get("bag_or_shrinkwrap", {}).get("hard_ng", True):
                result["reasons"].append(f"ハードNG: 袋/シュリンクっぽさが強い - {reason}")
                hard_ng = True

        return hard_ng

    def _maybe_vendor_composite_bonus(self, image: np.ndarray, result: Dict) -> int:
        rules_cfg = self.config.get("image_analysis", {}).get("rules", {})
        if "vendor_composite_bonus" not in rules_cfg.get("enabled", []):
            return 0
        cfg = rules_cfg.get("vendor_composite_bonus", {})
        if not cfg.get("enabled", True):
            return 0

        hit, reason = self._detect_vendor_composite_style(image, cfg)
        result["rule_results"]["vendor_composite_bonus"] = bool(hit)
        if hit:
            bonus = int(cfg.get("bonus_points", 10))
            result["reasons"].append(f"ボーナス: 業者合成スタイルを検出 (+{bonus}) - {reason}")
            return bonus
        return 0

    # -------------------------
    # 3つのスコア指標
    # -------------------------
    def _execute_analysis_checks(self, image: np.ndarray, result: Dict) -> int:
        weights = self.config.get("image_analysis", {}).get("algorithms", {})
        w_actual = int(weights.get("actual_product_weight", 40))
        w_quality = int(weights.get("photo_quality_weight", 30))
        w_effort = int(weights.get("sales_effort_weight", 30))

        total = 0

        s, reason = self._check_actual_product(image)
        total += s
        result["details"]["商品実物チェック"] = {"score": s, "max_score": 40, "reason": reason}

        s, reason = self._check_photo_quality(image)
        total += s
        result["details"]["撮影品質チェック"] = {"score": s, "max_score": 30, "reason": reason}

        s, reason = self._check_sales_effort(image)
        total += s
        result["details"]["販売努力チェック"] = {"score": s, "max_score": 30, "reason": reason}

        return total

    # --- 実物チェック ---
    def _check_actual_product(self, image: np.ndarray) -> Tuple[int, str]:
        thr = self.config.get("image_analysis", {}).get("quality_thresholds", {})
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.mean(edges > 0)

            text_density = self._estimate_text_density(gray)

            # 角の均一性（背景の整い具合）
            bg_uniformity = self._estimate_corner_uniformity(image)

            # 実物らしさ：そこそこのエッジ、テキスト少、背景が整いすぎない
            if edge_density > thr.get("edge_density_high", 0.10) and text_density < thr.get("text_density_low", 0.20):
                return 40, "商品実物の撮影（プロ仕様）"
            elif text_density > thr.get("text_density_high", 0.30):
                return 10, "パッケージ/説明要素が多く実物感が弱い"
            elif edge_density > thr.get("edge_density_medium", 0.08):
                return 25, "商品撮影（標準的）"
            else:
                return 10, "判定困難（低情報量）"
        except Exception as e:
            self.logger.error(f"実物チェックエラー: {e}")
            return 10, f"エラー: {str(e)}"

    # --- 品質チェック ---
    def _check_photo_quality(self, image: np.ndarray) -> Tuple[int, str]:
        thr = self.config.get("image_analysis", {}).get("quality_thresholds", {})
        try:
            bg_uniformity = self._estimate_corner_uniformity(image)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness_std = float(np.std(gray))

            if bg_uniformity < thr.get("background_uniformity_excellent", 30) and brightness_std < thr.get("brightness_std_excellent", 50):
                return 30, "統一された背景・プロ照明"
            elif bg_uniformity < thr.get("background_uniformity_good", 50):
                return 20, "整った背景"
            elif bg_uniformity < thr.get("background_uniformity_fair", 70):
                return 10, "やや雑然とした背景"
            else:
                return 0, "生活感のある背景（個人）"
        except Exception as e:
            self.logger.error(f"品質チェックエラー: {e}")
            return 10, f"エラー: {str(e)}"

    # --- 努力チェック ---
    def _check_sales_effort(self, image: np.ndarray) -> Tuple[int, str]:
        thr = self.config.get("image_analysis", {}).get("quality_thresholds", {})
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
            hist = hist / max(1, hist.sum())
            hist_nz = hist[hist > 0]
            entropy = float(-np.sum(hist_nz * np.log2(hist_nz))) if hist_nz.size else 0.0

            contrast = float(gray.std())
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            if entropy > thr.get("entropy_excellent", 7.0) and contrast > thr.get("contrast_excellent", 50) and sharpness > thr.get("sharpness_excellent", 100):
                return 30, "高品質・情報量多い（プロ撮影）"
            elif entropy > thr.get("entropy_good", 6.5) and contrast > thr.get("contrast_good", 40):
                return 20, "良好な撮影品質"
            elif entropy > thr.get("entropy_fair", 6.0) or contrast > thr.get("contrast_fair", 30):
                return 10, "標準的な撮影"
            else:
                return 0, "最小限の撮影（個人）"
        except Exception as e:
            self.logger.error(f"販売努力チェックエラー: {e}")
            return 10, f"エラー: {str(e)}"

    # -------------------------
    # サブルーチン（推定・検出）
    # -------------------------
    def _estimate_text_density(self, gray: np.ndarray) -> float:
        try:
            denoised = cv2.fastNlMeansDenoising(gray)
            edges = cv2.Canny(denoised, 50, 150)
            hk = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            hlines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, hk)
            vlines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vk)
            text_areas = cv2.add(hlines, vlines)
            ratio = float(np.mean(text_areas > 0))
            return float(min(ratio * 5.0, 1.0))  # 強めに正規化
        except Exception as e:
            self.logger.debug(f"テキスト密度推定エラー: {e}")
            return 0.0

    def _estimate_corner_uniformity(self, image: np.ndarray) -> float:
        """四隅の色分散の平均（低いほど均一 = スタジオ感）"""
        h, w = image.shape[:2]
        corner = min(50, h // 10, w // 10)
        if corner < 10:
            corner = min(30, h // 8, w // 8)
        blocks = [
            image[0:corner, 0:corner],
            image[0:corner, w - corner:w],
            image[h - corner:h, 0:corner],
            image[h - corner:h, w - corner:w]
        ]
        stds = []
        for b in blocks:
            if b.size == 0:
                continue
            stds.append(float(np.mean([b[:, :, 0].std(), b[:, :, 1].std(), b[:, :, 2].std()])))
        return float(np.mean(stds)) if stds else 100.0

    # ---- ハードルール用 検出 ----
    def _detect_package_only(self, image: np.ndarray, cfg: Dict) -> Tuple[bool, str]:
        """
        パッケージ/箱のみを強く示唆する簡易検出
        ヒューリスティック:
          - 画像中に大きな長方形（占有率）がある
          - 角の背景が比較的均一（合成/箱撮影っぽさ）
          - テキスト/水平垂直成分が比較的多い
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # 1) 大きな矩形占有率（最大輪郭面積 / 画像面積）
            rect_ratio, rect_reason = self._largest_rect_ratio(gray)

            # 2) 角の均一性（小さいほど合成/箱っぽい）
            bg_uni = self._estimate_corner_uniformity(image)

            # 3) テキスト密度
            text_dens = self._estimate_text_density(gray)

            cond_rect = rect_ratio >= float(cfg.get("large_rect_ratio", 0.30))
            cond_bg = bg_uni <= float(cfg.get("bg_uniformity_max", 45))
            cond_text = text_dens >= float(cfg.get("text_density_min", 0.18))

            hit = (cond_rect and cond_bg) or (cond_rect and cond_text)

            reason = f"rect_ratio={rect_ratio:.2f}, bg_uniformity={bg_uni:.1f}, text_density={text_dens:.2f}"
            return bool(hit), f"{rect_reason}; {reason}"
        except Exception as e:
            self.logger.debug(f"package_only検出エラー: {e}")
            return False, f"エラー: {str(e)}"

    def _detect_bag_or_shrinkwrap(self, image: np.ndarray, cfg: Dict) -> Tuple[bool, str]:
        """
        袋/シュリンクっぽさの簡易検出
          - 強いハイライト（明るい小領域）が多い
          - 高周波エッジがやや多い
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # 明部割合
            bright = (gray > 235).astype(np.uint8)
            bright_ratio = float(np.mean(bright > 0))

            # 小さなハイライト斑点数
            contours, _ = cv2.findContours(bright, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            spots = sum(1 for c in contours if 3 <= cv2.contourArea(c) <= 60)

            # 高周波エッジ密度
            edges = cv2.Canny(gray, 100, 200)
            hf_edge_density = float(np.mean(edges > 0))

            cond_bright = bright_ratio >= float(cfg.get("bright_pixel_ratio", 0.06))
            cond_spots = spots >= int(cfg.get("specular_spots_min", 40))
            cond_hf = hf_edge_density >= float(cfg.get("hf_edge_density_min", 0.11))

            hit = (cond_bright and cond_spots) or (cond_spots and cond_hf)

            reason = f"bright_ratio={bright_ratio:.3f}, specular_spots={spots}, hf_edge_density={hf_edge_density:.3f}"
            return bool(hit), reason
        except Exception as e:
            self.logger.debug(f"bag_or_shrinkwrap検出エラー: {e}")
            return False, f"エラー: {str(e)}"

    def _detect_vendor_composite_style(self, image: np.ndarray, cfg: Dict) -> Tuple[bool, str]:
        """
        業者合成スタイル（白/単色で均一な背景 + 中央に商品）の簡易判定
        """
        try:
            bg_uni = self._estimate_corner_uniformity(image)
            h, w = image.shape[:2]
            cx0, cy0 = int(w * 0.35), int(h * 0.35)
            cx1, cy1 = int(w * 0.65), int(h * 0.65)
            center = image[cy0:cy1, cx0:cx1]
            if center.size == 0:
                return False, "center area empty"

            # 中央のエッジ占有率（商品が中央に十分あるか）
            gray_c = cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)
            edges_c = cv2.Canny(gray_c, 50, 150)
            center_occ = float(np.mean(edges_c > 0))

            cond_uni = bg_uni <= float(cfg.get("solid_bg_uniformity_max", 28))
            cond_center = center_occ >= float(cfg.get("center_occupancy_min", 0.18))

            hit = cond_uni and cond_center
            reason = f"bg_uniformity={bg_uni:.1f}, center_occupancy={center_occ:.3f}"
            return bool(hit), reason
        except Exception as e:
            self.logger.debug(f"vendor_composite検出エラー: {e}")
            return False, f"エラー: {str(e)}"

    # ---- 補助: 最大矩形占有率 ----
    def _largest_rect_ratio(self, gray: np.ndarray) -> Tuple[float, str]:
        """
        ざっくり「大きな箱っぽい輪郭」が占める割合を返す
        """
        try:
            # 二値化→輪郭
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            thr_val, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 文字/模様の白地潰れを減らすため反転の方が良いケースがあるため比較
            th_inv = cv2.bitwise_not(th)

            def ratio_from_mask(mask: np.ndarray) -> float:
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                h, w = mask.shape[:2]
                img_area = float(h * w)
                if not contours:
                    return 0.0
                c = max(contours, key=cv2.contourArea)
                area = float(cv2.contourArea(c))
                if img_area <= 0:
                    return 0.0
                return area / img_area

            r1 = ratio_from_mask(th)
            r2 = ratio_from_mask(th_inv)
            r = max(r1, r2)
            return float(r), f"largest_rect_ratio={r:.2f} (bin={r1:.2f}/inv={r2:.2f})"
        except Exception as e:
            return 0.0, f"largest_rect_ratio計算エラー: {e}"