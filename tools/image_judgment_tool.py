"""
画像判定ツール - ユーザーインターフェース

使用方法:
1. python tools/image_judgment_tool.py single <画像パス>     # 単一画像判定
2. python tools/image_judgment_tool.py batch <フォルダパス>  # フォルダ一括判定
3. python tools/image_judgment_tool.py interactive         # 対話モード

段階的開発:
- Phase 1: 基本CLI ツール（現在）
- Phase 2: 精度向上とGUIインターフェース
- Phase 3: RPA統合モジュール
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime
import argparse
from typing import List, Dict

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.image_analyzer import ImageAnalyzer


class ImageJudgmentTool:
    """画像判定ツールのメインクラス"""
    
    def __init__(self):
        """初期化"""
        self.analyzer = ImageAnalyzer()
        self.setup_directories()
    
    def setup_directories(self):
        """必要ディレクトリの作成"""
        required_dirs = [
            "data/images/upload",      # アップロード用
            "data/images/mercari_ok",  # OK判定
            "data/images/mercari_ng",  # NG判定
            "data/results",            # 結果保存
            "logs"
        ]
        
        for dir_path in required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def analyze_single_image(self, image_path: str, save_result: bool = True) -> Dict:
        """
        単一画像の判定
        
        Args:
            image_path: 画像ファイルパス
            save_result: 結果保存するか
            
        Returns:
            判定結果
        """
        print(f"\n🔍 画像分析開始: {Path(image_path).name}")
        print("=" * 60)
        
        # 画像存在確認
        if not Path(image_path).exists():
            print(f"❌ エラー: ファイルが存在しません - {image_path}")
            return {'error': 'ファイルが存在しません'}
        
        # 分析実行
        result = self.analyzer.process_and_save_image(image_path)
        
        # 結果表示
        self._display_result(result)
        
        # 結果保存
        if save_result:
            self._save_result_json(result)
        
        return result
    
    def analyze_batch(self, folder_path: str) -> List[Dict]:
        """
        フォルダ内画像の一括判定
        
        Args:
            folder_path: フォルダパス
            
        Returns:
            判定結果のリスト
        """
        print(f"\n📁 フォルダ一括分析: {folder_path}")
        print("=" * 60)
        
        if not Path(folder_path).exists():
            print(f"❌ エラー: フォルダが存在しません - {folder_path}")
            return []
        
        # 一括分析実行
        results = self.analyzer.batch_analyze(folder_path)
        
        # 統計表示
        self._display_batch_summary(results)
        
        # 結果保存
        self._save_batch_results(results, folder_path)
        
        return results
    
    def interactive_mode(self):
        """対話モード"""
        print("\n🎯 メルカリ画像判定ツール - 対話モード")
        print("=" * 60)
        print("使用方法:")
        print("1. 画像ファイルのパスを入力")
        print("2. フォルダパスを入力（一括処理）")
        print("3. 'quit' で終了")
        print("=" * 60)
        
        while True:
            user_input = input("\n📸 画像パス/フォルダパス (quit で終了): ").strip()
            
            if user_input.lower() in ['quit', 'q', 'exit']:
                print("👋 終了します")
                break
            
            if not user_input:
                continue
            
            path = Path(user_input)
            
            if path.is_file():
                # 単一ファイル処理
                self.analyze_single_image(str(path))
            elif path.is_dir():
                # フォルダ処理
                self.analyze_batch(str(path))
            else:
                print(f"❌ パスが無効です: {user_input}")
    
    def _display_result(self, result: Dict):
        """判定結果の表示"""
        if result.get('error'):
            print(f"❌ エラー: {result['error']}")
            return
        
        # 基本情報
        print(f"📄 ファイル名: {result['file_name']}")
        print(f"📊 総合スコア: {result['score']}/100点")
        print(f"🎯 判定結果: {'✅ 業者(OK)' if result['is_business'] else '❌ 個人(NG)'}")
        print(f"💾 保存先: {result.get('saved_to', '未保存')}")
        
        # 詳細スコア
        print("\n📋 詳細スコア:")
        for check_name, detail in result.get('details', {}).items():
            score = detail['score']
            max_score = detail['max_score']
            reason = detail['reason']
            print(f"  • {check_name}: {score}/{max_score}点 - {reason}")
        
        # 最終パス
        if result.get('final_path'):
            print(f"\n📁 最終保存先: {result['final_path']}")
    
    def _display_batch_summary(self, results: List[Dict]):
        """一括処理結果の統計表示"""
        total = len(results)
        if total == 0:
            print("❌ 処理対象の画像がありませんでした")
            return
        
        ok_count = sum(1 for r in results if r.get('is_business', False))
        ng_count = total - ok_count
        error_count = sum(1 for r in results if r.get('error'))
        
        print(f"\n📊 処理結果統計:")
        print(f"  📁 総画像数: {total}")
        print(f"  ✅ OK判定: {ok_count} ({ok_count/total*100:.1f}%)")
        print(f"  ❌ NG判定: {ng_count} ({ng_count/total*100:.1f}%)")
        if error_count > 0:
            print(f"  ⚠️  エラー: {error_count}")
        
        # 平均スコア
        valid_results = [r for r in results if not r.get('error')]
        if valid_results:
            avg_score = sum(r['score'] for r in valid_results) / len(valid_results)
            print(f"  📈 平均スコア: {avg_score:.1f}点")
    
    def _save_result_json(self, result: Dict):
        """単一結果をJSONで保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"result_{timestamp}.json"
        filepath = Path("data/results") / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"💾 結果保存: {filepath}")
        except Exception as e:
            print(f"❌ 結果保存エラー: {e}")
    
    def _save_batch_results(self, results: List[Dict], folder_path: str):
        """一括結果をJSONで保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_name = Path(folder_path).name
        filename = f"batch_{folder_name}_{timestamp}.json"
        filepath = Path("data/results") / filename
        
        summary = {
            'source_folder': folder_path,
            'timestamp': timestamp,
            'total_images': len(results),
            'ok_count': sum(1 for r in results if r.get('is_business', False)),
            'ng_count': sum(1 for r in results if not r.get('is_business', False) and not r.get('error')),
            'error_count': sum(1 for r in results if r.get('error')),
            'results': results
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"💾 一括結果保存: {filepath}")
        except Exception as e:
            print(f"❌ 結果保存エラー: {e}")
    
    def test_mode(self):
        """テストモード - サンプル画像で動作確認"""
        print("\n🧪 テストモード")
        print("=" * 60)
        
        # テスト用ディレクトリ作成
        test_dir = Path("data/images/test_samples")
        test_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 テスト画像を {test_dir} に配置してください")
        print("準備ができたら Enter を押してください...")
        input()
        
        # テスト実行
        if any(test_dir.iterdir()):
            self.analyze_batch(str(test_dir))
        else:
            print("❌ テスト画像が見つかりません")


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description='メルカリ画像判定ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python tools/image_judgment_tool.py single data/images/sample.jpg
  python tools/image_judgment_tool.py batch data/images/upload/
  python tools/image_judgment_tool.py interactive
  python tools/image_judgment_tool.py test
        """
    )
    
    parser.add_argument(
        'mode',
        choices=['single', 'batch', 'interactive', 'test'],
        help='実行モード'
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        help='画像ファイル/フォルダパス (single/batch モード用)'
    )
    
    args = parser.parse_args()
    
    # ツール初期化
    tool = ImageJudgmentTool()
    
    try:
        if args.mode == 'single':
            if not args.path:
                print("❌ エラー: 画像パスを指定してください")
                parser.print_help()
                sys.exit(1)
            tool.analyze_single_image(args.path)
            
        elif args.mode == 'batch':
            if not args.path:
                print("❌ エラー: フォルダパスを指定してください")
                parser.print_help()
                sys.exit(1)
            tool.analyze_batch(args.path)
            
        elif args.mode == 'interactive':
            tool.interactive_mode()
            
        elif args.mode == 'test':
            tool.test_mode()
            
    except KeyboardInterrupt:
        print("\n\n👋 処理を中断しました")
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()