"""
アリババ画像一致判定ツール
メルカリ画像とアリババ拡大画像をOpenCVで照合（pHash/ORB/NCC の 2/3 合格）
"""

import cv2
import numpy as np
import json
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import hashlib

class AlibabaImageMatcher:
    """
    画像一致判定クラス
    複数のアルゴリズムで照合し、投票方式で判定
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
        
        # ORB検出器初期化
        self.orb = cv2.ORB_create(
            nfeatures=self.config['image_matcher']['orb']['n_features']
        )
        
        # BFMatcher初期化
        self.bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        
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
            log_dir / f"alibaba_matcher_{datetime.now():%Y%m%d}.log",
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
    
    def is_match(self, mercari_img: str, candidate_img: str) -> Tuple[bool, Dict]:
        """
        画像の一致判定（単一ペア）
        
        Args:
            mercari_img: メルカリ画像パス
            candidate_img: アリババ候補画像パス
            
        Returns:
            (matched: bool, scores: dict)のタプル
        """
        self.logger.info(f"一致判定開始: {Path(mercari_img).name} vs {Path(candidate_img).name}")
        
        # 画像読み込み
        img1 = self._load_and_preprocess(mercari_img)
        img2 = self._load_and_preprocess(candidate_img)
        
        if img1 is None or img2 is None:
            self.logger.error("画像読み込み失敗")
            return False, {"error": "画像読み込み失敗"}
        
        # 色ゲートチェック（最初に実行）
        ok_color, color_info = self._check_color_gate(img1, img2)
        if not ok_color:
            self.logger.info(f"色ゲートNG: HSV相関={color_info['color']['corr']:.3f}, ΔE={color_info['color']['deltaE50']:.1f}")
            return False, {"votes": 0, "matched": False, **color_info, "reason": "color-mismatch"}
        
        # 各アルゴリズムで判定
        scores = {"color": color_info["color"]}
        votes = 0
        
        # pHash判定
        if self.config['image_matcher']['phash']['enabled']:
            phash_result = self._check_phash(img1, img2)
            scores['phash'] = phash_result
            if phash_result['matched']:
                votes += 1
                self.logger.debug(f"pHash: 合格 (距離={phash_result['distance']})")
        
        # ORB判定
        if self.config['image_matcher']['orb']['enabled']:
            orb_result = self._check_orb(img1, img2)
            scores['orb'] = orb_result
            if orb_result['matched']:
                votes += 1
                self.logger.debug(f"ORB: 合格 (matches={orb_result['good_matches']}, inliers={orb_result.get('inlier_ratio', 0):.2f})")
        
        # NCC判定
        if self.config['image_matcher']['ncc']['enabled']:
            ncc_result = self._check_ncc(img1, img2)
            scores['ncc'] = ncc_result
            if ncc_result['matched']:
                votes += 1
                self.logger.debug(f"NCC: 合格 (score={ncc_result['score']:.3f})")
        
        # 投票結果
        required_votes = self.config['image_matcher']['voting']['required_votes']
        matched = votes >= required_votes
        
        scores['votes'] = votes
        scores['matched'] = matched
        
        self.logger.info(f"判定結果: {'一致' if matched else '不一致'} (票数: {votes}/{required_votes})")
        
        return matched, scores
    
    def match_folder(self, mercari_img: str, folder: str) -> Dict:
        """
        フォルダ内の全画像と照合
        
        Args:
            mercari_img: メルカリ画像パス
            folder: アリババ画像フォルダパス
            
        Returns:
            照合結果の辞書
        """
        self.logger.info(f"フォルダ照合開始: {folder}")
        
        folder_path = Path(folder)
        if not folder_path.exists():
            self.logger.error(f"フォルダが存在しません: {folder}")
            return {"error": "フォルダが存在しません"}
        
        # 画像ファイルを取得
        image_files = list(folder_path.glob("*.png")) + list(folder_path.glob("*.jpg"))
        self.logger.info(f"候補画像数: {len(image_files)}")
        
        if not image_files:
            return {"error": "画像ファイルが見つかりません"}
        
        # 各画像と照合
        results = []
        best_match = None
        best_votes = 0
        
        for img_file in image_files:
            matched, scores = self.is_match(mercari_img, str(img_file))
            
            result = {
                "path": str(img_file),
                "filename": img_file.name,
                "matched": matched,
                "scores": scores
            }
            results.append(result)
            
            # ベストマッチ更新
            if scores['votes'] > best_votes:
                best_votes = scores['votes']
                best_match = result
        
        return {
            "mercari_image": mercari_img,
            "folder": folder,
            "total_candidates": len(image_files),
            "best": best_match,
            "all": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _load_and_preprocess(self, image_path: str) -> Optional[np.ndarray]:
        """
        画像を読み込んで前処理
        
        Args:
            image_path: 画像パス
            
        Returns:
            前処理済み画像（BGR形式）
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # 前処理設定
            preproc = self.config['image_matcher']['preprocessing']
            
            # ノイズ除去
            if preproc['denoise']:
                img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
            
            # コントラスト強調
            if preproc['enhance_contrast']:
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l = clahe.apply(l)
                img = cv2.merge([l, a, b])
                img = cv2.cvtColor(img, cv2.COLOR_LAB2BGR)
            
            # 周辺5%クロップ（枠除去）
            h, w = img.shape[:2]
            y1, y2 = int(h * 0.05), int(h * 0.95)
            x1, x2 = int(w * 0.05), int(w * 0.95)
            img = img[y1:y2, x1:x2]
            
            return img
            
        except Exception as e:
            self.logger.error(f"画像読み込みエラー ({image_path}): {e}")
            return None
    
    def _check_color_gate(self, img1: np.ndarray, img2: np.ndarray) -> Tuple[bool, Dict]:
        """
        色ゲートチェック（カラー違いを弾く）
        
        Args:
            img1, img2: BGR画像
            
        Returns:
            (合格フラグ, 詳細情報)のタプル
        """
        try:
            # 中央60%を切り出し
            def crop_center(img):
                h, w = img.shape[:2]
                y1, y2 = int(h * 0.2), int(h * 0.8)
                x1, x2 = int(w * 0.2), int(w * 0.8)
                return img[y1:y2, x1:x2]
            
            center1 = crop_center(img1)
            center2 = crop_center(img2)
            
            # HSV変換
            hsv1 = cv2.cvtColor(center1, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(center2, cv2.COLOR_BGR2HSV)
            
            # 低彩度マスク（彩度40以上のピクセル）
            sat_mask1 = hsv1[:, :, 1] >= 40
            sat_mask2 = hsv2[:, :, 1] >= 40
            
            # HSヒストグラム相関（H:36ビン, S:16ビン）
            def hs_hist(hsv):
                h = cv2.calcHist([hsv], [0], None, [36], [0, 180])
                s = cv2.calcHist([hsv], [1], None, [16], [0, 256])
                h = cv2.normalize(h, h).flatten()
                s = cv2.normalize(s, s).flatten()
                return np.concatenate([h, s])
            
            hist1 = hs_hist(hsv1)
            hist2 = hs_hist(hsv2)
            corr = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            
            # Lab色空間でΔE計算（中央値）
            lab1 = cv2.cvtColor(center1, cv2.COLOR_BGR2Lab).astype(np.float32)
            lab2 = cv2.cvtColor(center2, cv2.COLOR_BGR2Lab).astype(np.float32)
            
            # 有彩色部分のみでΔE計算
            mask = sat_mask1 & sat_mask2
            if not np.any(mask):
                # 有彩色がない場合はNGとする
                return False, {"color": {"corr": float(corr), "deltaE50": 999.0}}
            
            # ΔE計算（ユークリッド距離）
            diff = lab1 - lab2
            deltaE = np.sqrt(np.sum(diff ** 2, axis=2))
            deltaE_masked = deltaE[mask]
            medE = float(np.median(deltaE_masked))
            
            # 閾値判定
            color_config = self.config['image_matcher'].get('color_gate', {})
            corr_min = color_config.get('hsv_corr_min', 0.92)
            deltaE_max = color_config.get('deltaE50_median_max', 6.0)
            
            ok = (corr >= corr_min) and (medE <= deltaE_max)
            
            return ok, {"color": {
                "corr": float(corr),
                "deltaE50": medE,
                "passed": ok
            }}
            
        except Exception as e:
            self.logger.error(f"色ゲートエラー: {e}")
            return False, {"color": {"error": str(e)}}
    
    def _check_phash(self, img1: np.ndarray, img2: np.ndarray) -> Dict:
        """
        pHash（Perceptual Hash）による判定
        
        Args:
            img1: 画像1（BGR）
            img2: 画像2（BGR）
            
        Returns:
            判定結果の辞書
        """
        try:
            # グレースケール変換
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            # リサイズ
            hash_size = self.config['image_matcher']['phash']['hash_size']
            resize_size = (hash_size * 4, hash_size * 4)
            
            resized1 = cv2.resize(gray1, resize_size, interpolation=cv2.INTER_AREA)
            resized2 = cv2.resize(gray2, resize_size, interpolation=cv2.INTER_AREA)
            
            # DCT（離散コサイン変換）
            dct1 = cv2.dct(np.float32(resized1))
            dct2 = cv2.dct(np.float32(resized2))
            
            # 低周波成分を抽出
            dct1_low = dct1[:hash_size, :hash_size]
            dct2_low = dct2[:hash_size, :hash_size]
            
            # 平均値計算（DC成分を除く）
            avg1 = np.mean(dct1_low) 
            avg2 = np.mean(dct2_low)
            
            # ハッシュ生成
            hash1 = (dct1_low > avg1).astype(np.uint8)
            hash2 = (dct2_low > avg2).astype(np.uint8)
            
            # ハミング距離計算
            hamming_distance = np.sum(hash1 != hash2)
            
            # 判定
            threshold = self.config['image_matcher']['phash']['hamming_threshold']
            matched = hamming_distance <= threshold
            
            return {
                "matched": matched,
                "distance": int(hamming_distance),
                "threshold": threshold,
                "hash1": hashlib.md5(hash1.tobytes()).hexdigest()[:8],
                "hash2": hashlib.md5(hash2.tobytes()).hexdigest()[:8]
            }
            
        except Exception as e:
            self.logger.error(f"pHashエラー: {e}")
            return {"matched": False, "error": str(e)}
    
    def _check_orb(self, img1: np.ndarray, img2: np.ndarray) -> Dict:
        """
        ORB（Oriented FAST and Rotated BRIEF）による判定（救済条件付き）
        
        Args:
            img1: 画像1（BGR）
            img2: 画像2（BGR）
            
        Returns:
            判定結果の辞書
        """
        try:
            # グレースケール変換
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            # 特徴点検出
            kp1, des1 = self.orb.detectAndCompute(gray1, None)
            kp2, des2 = self.orb.detectAndCompute(gray2, None)
            
            if des1 is None or des2 is None:
                return {
                    "matched": False,
                    "error": "特徴点が検出されませんでした",
                    "reason": "no-features"
                }
            
            # マッチング
            matches = self.bf_matcher.knnMatch(des1, des2, k=2)
            
            # Lowe's ratio test
            good_matches = []
            lowe_ratio = self.config['image_matcher']['orb']['lowe_ratio']
            
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < lowe_ratio * n.distance:
                        good_matches.append(m)
            
            # RANSAC によるホモグラフィ推定
            inlier_ratio = 0
            inliers = 0
            
            if len(good_matches) >= 4:
                src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                
                # ホモグラフィ行列とマスク取得
                _, mask = cv2.findHomography(
                    src_pts, dst_pts, 
                    cv2.RANSAC, 
                    self.config['image_matcher']['orb']['ransac_reproj_threshold']
                )
                
                if mask is not None:
                    inliers = int(np.sum(mask))
                    inlier_ratio = inliers / len(mask)
            
            # 判定（救済条件付き）
            good_threshold = self.config['image_matcher']['orb']['good_match_threshold']
            inlier_threshold = self.config['image_matcher']['orb']['inlier_ratio_threshold']
            
            # 厳密条件
            strict_ok = (len(good_matches) >= good_threshold and 
                        inlier_ratio >= inlier_threshold)
            
            # 救済条件
            rescue_ok = (inliers >= 18) or \
                       (len(good_matches) >= 30 and inlier_ratio >= 0.25)
            
            matched = strict_ok or rescue_ok
            
            reason = None
            if not matched:
                if len(good_matches) < 30:
                    reason = "orb-low-matches"
                elif inlier_ratio < 0.25:
                    reason = "orb-low-inliers"
            
            result = {
                "matched": matched,
                "total_matches": len(matches),
                "good_matches": len(good_matches),
                "inliers": inliers,
                "inlier_ratio": float(inlier_ratio),
                "good_threshold": good_threshold,
                "inlier_threshold": inlier_threshold
            }
            
            if reason:
                result["reason"] = reason
            
            return result
            
        except Exception as e:
            self.logger.error(f"ORBエラー: {e}")
            return {"matched": False, "error": str(e)}
    
    def _check_ncc(self, img1: np.ndarray, img2: np.ndarray) -> Dict:
        """
        NCC（Normalized Cross-Correlation）による判定
        
        Args:
            img1: 画像1（BGR）
            img2: 画像2（BGR）
            
        Returns:
            判定結果の辞書
        """
        try:
            # グレースケール変換
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            # リサイズ（計算高速化）
            resize_width = self.config['image_matcher']['ncc']['resize_width']
            
            h1, w1 = gray1.shape
            h2, w2 = gray2.shape
            
            # アスペクト比を保持してリサイズ
            scale1 = resize_width / w1
            scale2 = resize_width / w2
            
            new_h1 = int(h1 * scale1)
            new_h2 = int(h2 * scale2)
            
            resized1 = cv2.resize(gray1, (resize_width, new_h1))
            resized2 = cv2.resize(gray2, (resize_width, new_h2))
            
            # サイズを合わせる（小さい方に合わせる）
            min_h = min(new_h1, new_h2)
            resized1 = resized1[:min_h, :]
            resized2 = resized2[:min_h, :]
            
            # 正規化
            resized1 = resized1.astype(np.float32)
            resized2 = resized2.astype(np.float32)
            
            resized1 = (resized1 - np.mean(resized1)) / (np.std(resized1) + 1e-10)
            resized2 = (resized2 - np.mean(resized2)) / (np.std(resized2) + 1e-10)
            
            # 相関計算
            result = cv2.matchTemplate(resized1, resized2, cv2.TM_CCOEFF_NORMED)
            
            # 最大相関値
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            # スコアが負の場合は0にクリップ
            score = max(0, float(max_val))
            
            # 判定
            threshold = self.config['image_matcher']['ncc']['score_threshold']
            matched = score >= threshold
            
            return {
                "matched": matched,
                "score": score,
                "threshold": threshold,
                "size1": (w1, h1),
                "size2": (w2, h2),
                "resized_size": (resize_width, min_h)
            }
            
        except Exception as e:
            self.logger.error(f"NCCエラー: {e}")
            return {"matched": False, "error": str(e)}
    
    def generate_comparison_report(self, mercari_img: str, alibaba_folder: str, output_path: str = None):
        """
        詳細な比較レポートを生成
        
        Args:
            mercari_img: メルカリ画像パス
            alibaba_folder: アリババ画像フォルダ
            output_path: レポート出力パス（省略時は自動生成）
        """
        self.logger.info("比較レポート生成開始")
        
        # 照合実行
        results = self.match_folder(mercari_img, alibaba_folder)
        
        # レポート作成
        report = {
            "title": "画像一致判定レポート",
            "timestamp": datetime.now().isoformat(),
            "mercari_image": mercari_img,
            "alibaba_folder": alibaba_folder,
            "summary": {
                "total_candidates": results.get("total_candidates", 0),
                "matched_count": sum(1 for r in results.get("all", []) if r["matched"]),
                "best_match": None,
                "color_mismatches": 0
            }
        }
        
        # 色ミスマッチのカウント
        color_mismatches = sum(1 for r in results.get("all", []) 
                              if r.get("scores", {}).get("reason") == "color-mismatch")
        report["summary"]["color_mismatches"] = color_mismatches
        
        # ベストマッチ詳細
        if results.get("best"):
            best = results["best"]
            report["summary"]["best_match"] = {
                "filename": best["filename"],
                "votes": best["scores"]["votes"],
                "matched": best["matched"]
            }
        
        # 詳細結果
        report["details"] = []
        for result in results.get("all", []):
            detail = {
                "filename": result["filename"],
                "matched": result["matched"],
                "votes": result["scores"]["votes"],
                "algorithms": {}
            }
            
            # 失敗理由
            if "reason" in result["scores"]:
                detail["reason"] = result["scores"]["reason"]
            
            # 色ゲート結果
            if "color" in result["scores"]:
                detail["algorithms"]["color"] = result["scores"]["color"]
            
            # 各アルゴリズムの詳細
            if "phash" in result["scores"]:
                detail["algorithms"]["phash"] = {
                    "matched": result["scores"]["phash"].get("matched", False),
                    "distance": result["scores"]["phash"].get("distance", -1)
                }
            
            if "orb" in result["scores"]:
                detail["algorithms"]["orb"] = {
                    "matched": result["scores"]["orb"].get("matched", False),
                    "good_matches": result["scores"]["orb"].get("good_matches", 0),
                    "inliers": result["scores"]["orb"].get("inliers", 0),
                    "inlier_ratio": result["scores"]["orb"].get("inlier_ratio", 0)
                }
            
            if "ncc" in result["scores"]:
                detail["algorithms"]["ncc"] = {
                    "matched": result["scores"]["ncc"].get("matched", False),
                    "score": result["scores"]["ncc"].get("score", 0)
                }
            
            report["details"].append(detail)
        
        # 失敗理由の集計
        failure_reasons = {}
        for detail in report["details"]:
            if not detail["matched"] and "reason" in detail:
                reason = detail["reason"]
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        report["summary"]["failure_reasons"] = failure_reasons
        
        # ファイル出力
        if output_path is None:
            output_dir = Path(self.config['paths']['alibaba_data']) / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"report_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"レポート生成完了: {output_path}")
        
        return report


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="アリババ画像一致判定ツール")
    parser.add_argument("mercari_image", help="メルカリ画像パス")
    parser.add_argument("target", help="アリババ画像パス or フォルダパス")
    parser.add_argument("--config", default="config/alibaba_config.yaml", help="設定ファイルパス")
    parser.add_argument("--report", action="store_true", help="詳細レポートを生成")
    parser.add_argument("--output", help="レポート出力パス")
    parser.add_argument("--debug", action="store_true", help="デバッグモード")
    
    args = parser.parse_args()
    
    # デバッグモード設定
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # マッチャー初期化
    matcher = AlibabaImageMatcher(args.config)
    
    # ターゲット判定
    target_path = Path(args.target)
    
    # 終了コード判定用
    exit_ok = False
    
    if target_path.is_dir():
        # フォルダ照合
        if args.report:
            # 詳細レポート生成
            report = matcher.generate_comparison_report(
                args.mercari_image,
                args.target,
                args.output
            )
            
            # サマリー表示
            print(f"\n===== 照合結果サマリー =====")
            print(f"候補数: {report['summary']['total_candidates']}")
            print(f"一致数: {report['summary']['matched_count']}")
            print(f"色ミスマッチ: {report['summary']['color_mismatches']}")
            
            if report['summary']['failure_reasons']:
                print(f"\n失敗理由:")
                for reason, count in report['summary']['failure_reasons'].items():
                    print(f"  {reason}: {count}件")
            
            if report['summary']['best_match']:
                best = report['summary']['best_match']
                print(f"\nベストマッチ:")
                print(f"  ファイル: {best['filename']}")
                print(f"  票数: {best['votes']}/3")
                print(f"  判定: {'一致' if best['matched'] else '不一致'}")
                exit_ok = bool(best and best.get("matched"))
            
        else:
            # 通常のフォルダ照合
            results = matcher.match_folder(args.mercari_image, args.target)
            
            # 結果出力
            print(f"\n===== 照合結果 =====")
            print(f"候補数: {results['total_candidates']}")
            
            if results.get('best'):
                best = results['best']
                print(f"\nベストマッチ:")
                print(f"  ファイル: {best['filename']}")
                print(f"  判定: {'一致' if best['matched'] else '不一致'}")
                print(f"  票数: {best['scores']['votes']}/3")
                
                # 色情報
                if 'color' in best['scores']:
                    color = best['scores']['color']
                    print(f"\n色情報:")
                    print(f"  HSV相関: {color['corr']:.3f}")
                    print(f"  ΔE50: {color['deltaE50']:.1f}")
                
                # 各アルゴリズムの結果
                if 'phash' in best['scores']:
                    print(f"\npHash:")
                    print(f"  距離: {best['scores']['phash']['distance']}")
                if 'orb' in best['scores']:
                    print(f"\nORB:")
                    print(f"  マッチ数: {best['scores']['orb']['good_matches']}")
                    print(f"  インライア: {best['scores']['orb']['inliers']}")
                if 'ncc' in best['scores']:
                    print(f"\nNCC:")
                    print(f"  スコア: {best['scores']['ncc']['score']:.3f}")
                
                exit_ok = bool(best.get("matched"))
            else:
                print("一致する画像が見つかりませんでした")
                
    else:
        # 単一画像照合
        matched, scores = matcher.is_match(args.mercari_image, args.target)
        
        # 結果出力
        print(f"\n===== 照合結果 =====")
        print(f"判定: {'一致' if matched else '不一致'}")
        print(f"票数: {scores['votes']}/3")
        
        # 失敗理由
        if 'reason' in scores:
            print(f"理由: {scores['reason']}")
        
        # 色ゲート情報
        if 'color' in scores:
            print(f"\n色ゲート:")
            print(f"  HSV相関: {scores['color']['corr']:.3f}")
            print(f"  ΔE50: {scores['color']['deltaE50']:.1f}")
            print(f"  判定: {'合格' if scores['color'].get('passed', False) else '不合格'}")
        
        # 各アルゴリズムの詳細
        print("\n--- 詳細スコア ---")
        if 'phash' in scores:
            print(f"pHash:")
            print(f"  判定: {'合格' if scores['phash']['matched'] else '不合格'}")
            print(f"  ハミング距離: {scores['phash']['distance']}/{scores['phash']['threshold']}")
        
        if 'orb' in scores:
            print(f"ORB:")
            print(f"  判定: {'合格' if scores['orb']['matched'] else '不合格'}")
            print(f"  良好マッチ数: {scores['orb']['good_matches']}/{scores['orb']['good_threshold']}")
            print(f"  インライア数: {scores['orb']['inliers']}")
            print(f"  インライア率: {scores['orb']['inlier_ratio']:.2%}")
        
        if 'ncc' in scores:
            print(f"NCC:")
            print(f"  判定: {'合格' if scores['ncc']['matched'] else '不合格'}")
            print(f"  相関スコア: {scores['ncc']['score']:.3f}/{scores['ncc']['threshold']}")
        
        exit_ok = bool(matched)
    
    return 0 if exit_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())