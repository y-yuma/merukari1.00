"""
画像判定デバッグ・精度測定ツール

使い方:
1) 混同行列:
   python tools/debug_analyzer.py confusion test_data/
   ├─ test_data/business ... 業者=OKの正解
   └─ test_data/personal ... 個人=NGの正解

2) 閾値最適化:
   python tools/debug_analyzer.py threshold test_data/

3) デバッグ画像（中間可視化）:
   python tools/debug_analyzer.py debug_images <画像パス>
"""

import sys
from pathlib import Path
import json
import numpy as np
import cv2
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict
import argparse

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.image_analyzer import ImageAnalyzer


class DebugAnalyzer:
    def __init__(self):
        self.analyzer = ImageAnalyzer()
        self.results_dir = Path("data/debug_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # 混同行列
    # -------------------------
    def create_confusion_matrix(self, test_folder: str) -> Dict:
        tp = tn = fp = fn = 0
        business_scores, personal_scores = [], []
        details = []

        base = Path(test_folder)
        biz = base / "business"
        per = base / "personal"
        if not biz.exists() or not per.exists():
            print("❌ エラー: business/ と personal/ フォルダが必要です")
            return {}

        def files_in(d: Path):
            return [p for p in d.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}]

        biz_files = files_in(biz)
        per_files = files_in(per)

        print(f"📊 業者(OK)画像: {len(biz_files)}")
        for p in biz_files:
            r = self.analyzer.analyze_single_image(str(p))
            s = r.get("score", 0)
            yhat = r.get("is_business", False)
            business_scores.append(float(s))
            details.append({
                "file": p.name, "true": "business", "pred": "business" if yhat else "personal",
                "score": s, "correct": bool(yhat)
            })
            if yhat: tp += 1
            else: fn += 1

        print(f"📊 個人(NG)画像: {len(per_files)}")
        for p in per_files:
            r = self.analyzer.analyze_single_image(str(p))
            s = r.get("score", 0)
            yhat = r.get("is_business", False)
            personal_scores.append(float(s))
            details.append({
                "file": p.name, "true": "personal", "pred": "business" if yhat else "personal",
                "score": s, "correct": not bool(yhat)
            })
            if yhat: fp += 1
            else: tn += 1

        total = tp + tn + fp + fn
        acc = (tp + tn) / total if total else 0.0
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

        print("\n📊 混同行列")
        print("            予測")
        print("        業者  個人")
        print(f"実際 業者  {tp:3d}   {fn:3d}")
        print(f"     個人  {fp:3d}   {tn:3d}")
        print(f"\n📈 Accuracy={acc:.3f}  Precision={prec:.3f}  Recall={rec:.3f}  F1={f1:.3f}")

        result = {
            "true_positive": tp, "true_negative": tn, "false_positive": fp, "false_negative": fn,
            "accuracy": acc, "precision": prec, "recall": rec, "f1_score": f1,
            "business_scores": business_scores,
            "personal_scores": personal_scores,
            "details": details
        }

        self._save_json("confusion_matrix", result)
        return result

    # -------------------------
    # 閾値最適化
    # -------------------------
    def optimize_threshold(self, test_folder: str) -> Dict:
        cm = self.create_confusion_matrix(test_folder)
        biz = cm.get("business_scores", [])
        per = cm.get("personal_scores", [])
        if not biz or not per:
            print("❌ スコアデータが不足しています")
            return {}

        all_scores = biz + per
        lo, hi = min(all_scores), max(all_scores)
        thresholds = np.linspace(lo, hi, 100)

        best_f1, best_t = -1.0, self.analyzer.business_threshold
        rows = []
        for t in thresholds:
            tp = sum(1 for s in biz if s >= t)
            fn = sum(1 for s in biz if s < t)
            tn = sum(1 for s in per if s < t)
            fp = sum(1 for s in per if s >= t)
            total = tp + tn + fp + fn
            if total == 0: 
                continue
            acc = (tp + tn) / total
            prec = tp / (tp + fp) if (tp + fp) else 0
            rec = tp / (tp + fn) if (tp + fn) else 0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
            rows.append({"threshold": float(t), "accuracy": acc, "precision": prec, "recall": rec, "f1_score": f1})
            if f1 > best_f1:
                best_f1, best_t = f1, float(t)

        self._plot_thresholds(rows, best_t)
        out = {"current_threshold": self.analyzer.business_threshold, "optimal_threshold": best_t, "best_f1_score": best_f1, "threshold_results": rows}
        self._save_json("threshold_optimization", out)
        print(f"\n📈 最適閾値: {best_t:.1f} (F1={best_f1:.3f})")
        print(f"   現在閾値: {self.analyzer.business_threshold:.1f}")
        if abs(best_t - self.analyzer.business_threshold) >= 1e-6:
            print(f"💡 推奨: config.json の business_threshold を {best_t:.1f} に調整")
        return out

    # -------------------------
    # デバッグ画像
    # -------------------------
    def create_debug_images(self, image_path: str):
        print(f"🔬 デバッグ画像作成: {Path(image_path).name}")
        try:
            img = self.analyzer._read_and_normalize(image_path)
            out_dir = self.results_dir / "debug_images" / Path(image_path).stem
            out_dir.mkdir(parents=True, exist_ok=True)

            cv2.imwrite(str(out_dir / "01_original.jpg"), img)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(str(out_dir / "02_gray.jpg"), gray)
            edges = cv2.Canny(gray, 50, 150)
            cv2.imwrite(str(out_dir / "03_edges.jpg"), edges)

            # テキスト推定可視化
            hk = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            hlines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, hk)
            vlines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vk)
            text = cv2.add(hlines, vlines)
            vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            vis[:, :, 2] = np.maximum(vis[:, :, 2], text)
            cv2.imwrite(str(out_dir / "04_text_like.jpg"), vis)

            # 背景四隅
            vis2 = img.copy()
            h, w = img.shape[:2]
            corner = min(50, h // 10, w // 10)
            for (x, y), color in [((0, 0), (255, 0, 0)), ((w - corner, 0), (0, 255, 0)),
                                  ((0, h - corner), (0, 0, 255)), ((w - corner, h - corner), (255, 255, 0))]:
                cv2.rectangle(vis2, (x, y), (x + corner, y + corner), color, 2)
            cv2.imwrite(str(out_dir / "05_background_corners.jpg"), vis2)

            print(f"✅ デバッグ画像保存: {out_dir}")
        except Exception as e:
            print(f"❌ デバッグ画像作成エラー: {e}")

    # -------------------------
    # ヘルパ
    # -------------------------
    def _save_json(self, name: str, payload: Dict):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.results_dir / f"{name}_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"💾 結果保存: {path}")

    def _plot_thresholds(self, rows: List[Dict], best_t: float):
        try:
            th = [r["threshold"] for r in rows]
            acc = [r["accuracy"] for r in rows]
            pre = [r["precision"] for r in rows]
            rec = [r["recall"] for r in rows]
            f1 = [r["f1_score"] for r in rows]
            plt.figure(figsize=(12, 8))
            plt.plot(th, acc, label="Accuracy", linewidth=2)
            plt.plot(th, pre, label="Precision", linewidth=2)
            plt.plot(th, rec, label="Recall", linewidth=2)
            plt.plot(th, f1, label="F1", linewidth=2)
            plt.axvline(best_t, linestyle="--", color="red", label=f"Optimal ({best_t:.1f})")
            plt.xlabel("Threshold"); plt.ylabel("Score"); plt.title("Threshold Optimization")
            plt.grid(True, alpha=0.3); plt.legend()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = self.results_dir / f"threshold_plot_{ts}.png"
            plt.savefig(out, dpi=300, bbox_inches="tight")
            print(f"📈 グラフ保存: {out}")
        except Exception as e:
            print(f"⚠️ グラフ作成エラー: {e}")


def main():
    p = argparse.ArgumentParser(description="画像判定デバッグツール")
    p.add_argument("mode", choices=["confusion", "threshold", "debug_images"])
    p.add_argument("path", help="対象フォルダ or 画像パス")
    args = p.parse_args()

    tool = DebugAnalyzer()
    try:
        if args.mode == "confusion":
            tool.create_confusion_matrix(args.path)
        elif args.mode == "threshold":
            tool.optimize_threshold(args.path)
        elif args.mode == "debug_images":
            tool.create_debug_images(args.path)
    except KeyboardInterrupt:
        print("\n👋 中断しました")
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == "__main__":
    main()