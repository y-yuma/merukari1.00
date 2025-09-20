"""
メルカリ統合フローシステム
RPAと画像判別を統合した一連の自動処理
"""
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pyautogui
import numpy as np

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from modules.research import MercariResearcher
from core.image_analyzer import ImageAnalyzer
from utils.logger import setup_logger
from utils.screenshot_helper import get_screenshot_helper

class MercariIntegratedFlow:
    """メルカリ統合フロークラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = setup_logger(__name__)
        
        # モジュール初期化
        self.researcher = MercariResearcher()
        self.analyzer = ImageAnalyzer()
        
        # 結果保存用
        self.results = []
        self.stats = {
            'total_processed': 0,
            'ok_count': 0,
            'ng_count': 0,
            'error_count': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 座標設定読み込み
        self.load_coordinates()
        
        self.logger.info("メルカリ統合フローシステムを初期化しました")
    
    def load_coordinates(self):
        """座標設定を読み込み"""
        coord_file = Path('config/coordinate_sets/mercari.json')
        if coord_file.exists():
            with open(coord_file, 'r', encoding='utf-8') as f:
                self.coords = json.load(f)
                self.logger.info(f"座標設定を読み込みました: {len(self.coords)-1}項目")
        else:
            raise FileNotFoundError("座標設定ファイルが見つかりません")
    
    def run_integrated_search(self, 
                            category_path: List[str], 
                            max_items: int = 20,
                            save_results: bool = True) -> List[Dict]:
        """
        統合検索実行
        
        Args:
            category_path: カテゴリーパス（例: ['家電・スマホ・カメラ', 'PC/タブレット']）
            max_items: 処理する商品数
            save_results: 結果を保存するか
            
        Returns:
            判別結果を含む商品情報リスト
        """
        self.logger.info("=" * 60)
        self.logger.info("統合検索を開始します")
        self.logger.info(f"カテゴリー: {' > '.join(category_path)}")
        self.logger.info(f"最大処理数: {max_items}件")
        self.logger.info("=" * 60)
        
        self.stats['start_time'] = datetime.now()
        
        try:
            # メルカリトップページへ移動
            self.researcher.navigate_to_mercari()
            
            # カテゴリー選択
            self.researcher.select_category_hierarchy(category_path)
            
            # フィルター適用
            self.researcher.apply_search_filters()
            
            # 検索実行
            self.researcher.execute_search()
            
            # 商品処理ループ
            processed_items = 0
            page = 1
            
            while processed_items < max_items:
                self.logger.info(f"\n--- ページ{page}の処理開始 ---")
                
                # 現在ページの商品を処理
                page_results = self.process_page_with_judgment(
                    max_items - processed_items
                )
                
                if not page_results:
                    self.logger.info("これ以上商品がありません")
                    break
                
                self.results.extend(page_results)
                processed_items += len(page_results)
                
                # 統計更新
                self.update_statistics(page_results)
                
                # 進捗表示
                self.show_progress(processed_items, max_items)
                
                # 次ページへ
                if processed_items < max_items:
                    if not self.researcher.go_to_next_page():
                        self.logger.info("次ページが見つかりません")
                        break
                    page += 1
                    
                    # レート制限対策
                    if page % 3 == 0:
                        self.logger.info("レート制限対策: 30秒待機")
                        time.sleep(30)
            
            # 処理完了
            self.stats['end_time'] = datetime.now()
            self.stats['total_processed'] = processed_items
            
            # 結果保存
            if save_results:
                self.save_results()
            
            # 最終レポート表示
            self.show_final_report()
            
            return self.results
            
        except Exception as e:
            self.logger.error(f"統合検索エラー: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return self.results
    
    def process_page_with_judgment(self, max_items: int) -> List[Dict]:
        """
        ページ内の商品を画像判別付きで処理
        
        Args:
            max_items: このページで処理する最大商品数
            
        Returns:
            画像判別結果を含む商品リスト
        """
        products = []
        items_processed = 0
        
        # グリッド位置の商品を順番に処理
        for i in range(1, 21):  # 最大20商品/ページ
            if items_processed >= max_items:
                break
            
            grid_key = f'product_grid_{i}'
            if grid_key not in self.coords:
                continue
            
            try:
                self.logger.info(f"\n=== 商品{i}処理開始 ===")
                
                # 商品をCommand+クリックで新タブで開く
                coords = self.coords[grid_key]
                self.researcher.human.command_click(coords)
                time.sleep(2)  # ページ読み込み待機
                
                # 商品情報抽出
                product = self.researcher.extract_product_details()
                
                if product:
                    # 画像判別を実行
                    product = self.process_product_image(product)
                    
                    # 3日間売上カウント
                    sales_3days = self.researcher.count_3days_sales()
                    product['sales_3days'] = sales_3days if sales_3days is not None else 0
                    product['monthly_estimate'] = product['sales_3days'] * 10
                    
                    # 結果を追加
                    products.append(product)
                    
                    # ログ出力
                    self.logger.info(
                        f"商品{i}: {product.get('title', 'タイトル不明')[:30]}..."
                    )
                    self.logger.info(
                        f"  判別結果: {'OK (業者)' if product.get('is_business') else 'NG (個人)'}"
                    )
                    self.logger.info(
                        f"  スコア: {product.get('judgment_score', 0)}点"
                    )
                    self.logger.info(
                        f"  3日売上: {product['sales_3days']}個"
                    )
                
                # タブを閉じて一覧に戻る
                self.researcher.human.close_current_tab()
                items_processed += 1
                
                # 人間らしい休憩
                if items_processed % 5 == 0:
                    time.sleep(2)
                
                # 10個処理後、スクロール
                if items_processed == 10:
                    self.perform_scroll_with_adjustment()
                
            except Exception as e:
                self.logger.error(f"商品{i}の処理エラー: {e}")
                self.stats['error_count'] += 1
                # エラー時もタブを閉じる
                try:
                    self.researcher.human.close_current_tab()
                except:
                    pass
                continue
        
        return products
    
    def process_product_image(self, product: Dict) -> Dict:
        """
        商品画像を判別処理
        
        Args:
            product: 商品情報
            
        Returns:
            判別結果を追加した商品情報
        """
        try:
            # 拡大画像を取得
            if not product.get('image_path'):
                # 画像をキャプチャ（拡大表示）
                image_path = self.capture_expanded_product_image()
                product['image_path'] = image_path
            
            # 画像判別実行
            if product.get('image_path') and Path(product['image_path']).exists():
                result = self.analyzer.analyze_single_image(product['image_path'])
                
                # 結果を商品情報に追加
                product['is_business'] = result.get('is_business', False)
                product['judgment_score'] = result.get('score', 0)
                product['judgment_reasons'] = result.get('reasons', [])
                product['judgment_details'] = result.get('details', {})
                
                self.logger.debug(f"画像判別完了: スコア{product['judgment_score']}点")
            else:
                # 画像取得失敗時
                product['is_business'] = False
                product['judgment_score'] = 0
                product['judgment_reasons'] = ['画像取得失敗']
                self.logger.warning("画像取得失敗のためNG判定")
                
        except Exception as e:
            self.logger.error(f"画像判別エラー: {e}")
            product['is_business'] = False
            product['judgment_score'] = 0
            product['judgment_reasons'] = [f'判別エラー: {str(e)}']
        
        return product
    
    def capture_expanded_product_image(self) -> str:
        """
        商品画像をクリックして拡大表示し、指定範囲をキャプチャ
        マルチディスプレイ・Retina対応版
        
        Returns:
            保存した画像のパス
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = Path(f'data/images/mercari/{timestamp}_product.png')
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # スクリーンショットヘルパーを取得
        screenshot_helper = get_screenshot_helper()
        
        try:
            # メイン画像をクリックして拡大表示
            if 'product_image_main' in self.coords:
                self.logger.debug("商品画像をクリックして拡大表示")
                coords = self.coords['product_image_main']
                pyautogui.click(coords[0], coords[1])
                time.sleep(2)  # モーダル表示待機
                
                # 座標設定から拡大画像エリアを取得
                if 'expanded_image_area' in self.coords:
                    # 設定済みの範囲を使用
                    area = self.coords['expanded_image_area']
                    left = area['top_left'][0]
                    top = area['top_left'][1]
                    capture_width = area['width']
                    capture_height = area['height']
                    
                    self.logger.debug(f"設定済み範囲を使用: ({left}, {top}, {capture_width}, {capture_height})")
                else:
                    # フォールバック：画面中央の600x600ピクセル
                    screen_width, screen_height = pyautogui.size()
                    capture_width = 600
                    capture_height = 600
                    left = (screen_width - capture_width) // 2
                    top = (screen_height - capture_height) // 2
                    
                    self.logger.warning("拡大画像エリアが未設定のため、デフォルト範囲を使用")
                    self.logger.debug(f"デフォルト範囲: ({left}, {top}, {capture_width}, {capture_height})")
                
                # マルチディスプレイ対応スクリーンショット撮影
                screenshot = screenshot_helper.capture_region(left, top, capture_width, capture_height)
                screenshot.save(filepath)
                
                # モーダルを閉じる（ESCキー）
                pyautogui.press('escape')
                time.sleep(1)
                
                self.logger.info(f"画像保存: {filepath}")
                return str(filepath)
                
            else:
                self.logger.error("product_image_main座標が設定されていません")
                return ""
                
        except Exception as e:
            self.logger.error(f"画像キャプチャエラー: {e}")
            # エラー時もモーダルを閉じる
            try:
                pyautogui.press('escape')
            except:
                pass
            return ""
    
    def perform_scroll_with_adjustment(self):
        """改善されたスクロール処理"""
        try:
            # スクロール基準位置に移動
            if 'scroll_position' in self.coords:
                scroll_pos = self.coords['scroll_position']
                pyautogui.moveTo(scroll_pos[0], scroll_pos[1])
                time.sleep(0.3)
            
            # 段階的スクロール（より自然に）
            scroll_amounts = [-300, -300, -200]  # 徐々に減速
            for amount in scroll_amounts:
                pyautogui.scroll(amount)
                time.sleep(0.5)
            
            # スクロール後の安定化待機
            time.sleep(2)
            
            self.logger.debug("スクロール完了")
            
        except Exception as e:
            self.logger.error(f"スクロールエラー: {e}")
    
    def update_statistics(self, page_results: List[Dict]):
        """統計情報を更新"""
        for product in page_results:
            if product.get('is_business'):
                self.stats['ok_count'] += 1
            else:
                self.stats['ng_count'] += 1
    
    def show_progress(self, current: int, total: int):
        """進捗表示"""
        percentage = (current / total * 100) if total > 0 else 0
        self.logger.info(f"\n進捗: {current}/{total} ({percentage:.1f}%)")
        self.logger.info(f"OK: {self.stats['ok_count']}件, NG: {self.stats['ng_count']}件")
    
    def save_results(self):
        """結果をJSONファイルに保存"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = Path(f'data/results/mercari_results_{timestamp}.json')
            result_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存データ作成
            save_data = {
                'timestamp': timestamp,
                'statistics': self.stats,
                'products': self.results
            }
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"結果を保存しました: {result_file}")
            
        except Exception as e:
            self.logger.error(f"結果保存エラー: {e}")
    
    def show_final_report(self):
        """最終レポート表示"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("処理完了レポート")
        self.logger.info("=" * 60)
        
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            self.logger.info(f"処理時間: {duration}")
        
        self.logger.info(f"総処理数: {self.stats['total_processed']}件")
        self.logger.info(f"OK (業者): {self.stats['ok_count']}件")
        self.logger.info(f"NG (個人): {self.stats['ng_count']}件")
        self.logger.info(f"エラー: {self.stats['error_count']}件")
        
        if self.stats['total_processed'] > 0:
            ok_rate = (self.stats['ok_count'] / self.stats['total_processed'] * 100)
            self.logger.info(f"業者率: {ok_rate:.1f}%")
        
        # OK商品のリスト表示
        ok_products = [p for p in self.results if p.get('is_business')]
        if ok_products:
            self.logger.info("\n--- OK判定商品 ---")
            for i, product in enumerate(ok_products[:10], 1):
                self.logger.info(
                    f"{i}. {product.get('title', '不明')[:40]}... "
                    f"(スコア: {product.get('judgment_score', 0)}点, "
                    f"3日売上: {product.get('sales_3days', 0)}個)"
                )


def main():
    """メイン実行関数"""
    print("=" * 60)
    print("メルカリ統合フローシステム")
    print("=" * 60)
    
    # カテゴリー選択
    print("\nカテゴリーを選択してください:")
    print("1. PC周辺機器")
    print("2. おもちゃ")
    print("3. スポーツ用品")
    print("4. カスタム入力")
    
    choice = input("\n選択 (1-4): ")
    
    category_paths = {
        '1': ['家電・スマホ・カメラ', 'PC/タブレット', 'PC周辺機器'],
        '2': ['おもちゃ・ホビー・グッズ', 'おもちゃ', 'キャラクターグッズ'],
        '3': ['スポーツ・レジャー', 'トレーニング/エクササイズ', 'トレーニング用品']
    }
    
    if choice in category_paths:
        category_path = category_paths[choice]
    elif choice == '4':
        categories = input("カテゴリーをカンマ区切りで入力: ")
        category_path = [c.strip() for c in categories.split(',')]
    else:
        print("無効な選択です")
        return
    
    # 処理数入力
    max_items = input("\n処理する商品数 (デフォルト: 10): ")
    max_items = int(max_items) if max_items.isdigit() else 10
    
    # 実行確認
    print(f"\n以下の条件で実行します:")
    print(f"カテゴリー: {' > '.join(category_path)}")
    print(f"処理数: {max_items}件")
    
    confirm = input("\n実行しますか？ (y/n): ")
    if confirm.lower() != 'y':
        print("キャンセルしました")
        return
    
    # フロー実行
    try:
        flow = MercariIntegratedFlow()
        results = flow.run_integrated_search(
            category_path=category_path,
            max_items=max_items,
            save_results=True
        )
        
        print(f"\n処理が完了しました。{len(results)}件の商品を処理しました。")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()