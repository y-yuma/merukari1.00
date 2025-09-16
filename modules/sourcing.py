"""
アリババ仕入れ判断モジュール（改訂版）
- 新フロー対応: カメラマーク → ファイル選択 → 商品処理
- 画像検索で上位商品を機械的に取得
- 利益計算と法規制チェック
"""
import pyautogui
import pyperclip
import time
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class AlibabaSourcing:
    """
    アリババ仕入れクラス（新フロー対応）
    画像検索による商品マッチングと利益計算
    """
    def __init__(self, spreadsheet_manager):
        """
        初期化
        Args:
            spreadsheet_manager: スプレッドシート管理オブジェクト
        """
        self.spreadsheet = spreadsheet_manager
        print("アリババ仕入れモジュール初期化中...")
        
        # 座標読み込み
        coord_file = Path('config/coordinate_sets/alibaba.json')
        if not coord_file.exists():
            raise FileNotFoundError(
                "アリババの座標が設定されていません。"
                "python tools/coordinate_mapper.py でメニュー2を実行してください。"
            )
        
        with open(coord_file, 'r', encoding='utf-8') as f:
            self.coords = json.load(f)
        
        # フローバージョンチェック
        metadata = self.coords.get('_metadata', {})
        flow_version = metadata.get('flow_version', '旧版')
        if flow_version == '旧版':
            print("警告: 旧版の座標設定です。新フローの座標再設定をお勧めします。")
        
        # PyAutoGUI設定
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        # 設定
        self.exchange_rate = 21.0  # 人民元→日本円
        self.agent_fee_rate = 0.05  # 代行手数料率
        self.customs_rate = 0.15  # 簡易税率
        self.mercari_fee_rate = 0.10  # メルカリ手数料率
        self.domestic_shipping = 200  # 国内送料（ゆうパケット想定）
        
        print("✓ アリババ仕入れモジュール初期化完了")

    def search_by_image_new_flow(self, image_folder_path: str = "Pictures/メルカリ") -> List[Dict]:
        """
        新フローでの画像検索実行
        Args:
            image_folder_path: 画像フォルダパス
        Returns:
            処理結果のリスト
        """
        print(f"\n新フローでの画像検索を開始: {image_folder_path}")
        
        try:
            # Phase 1: 画像検索開始
            if not self.start_image_search():
                print("エラー: 画像検索の開始に失敗")
                return []
            
            # Phase 2: ファイル選択フロー
            if not self.execute_file_selection_flow():
                print("エラー: ファイル選択に失敗")
                return []
            
            # Phase 3: 検索結果処理（1ページ分）
            results = self.process_search_results_page()
            
            print(f"✓ 新フロー実行完了: {len(results)}件の商品を処理")
            return results
            
        except Exception as e:
            print(f"エラー: 新フロー実行中に問題が発生: {e}")
            return []

    def start_image_search(self) -> bool:
        """
        Phase 1: カメラマークをクリックして画像検索を開始
        """
        try:
            print("Phase 1: カメラマークをクリック中...")
            
            if 'camera_icon' not in self.coords:
                print("エラー: カメラアイコンの座標が設定されていません")
                return False
            
            camera_pos = self.coords['camera_icon']
            pyautogui.click(camera_pos[0], camera_pos[1])
            time.sleep(2)  # ファイルダイアログが開くまで待機
            
            print("✓ カメラマーククリック完了")
            return True
            
        except Exception as e:
            print(f"エラー: カメラマーククリック失敗: {e}")
            return False

    def execute_file_selection_flow(self) -> bool:
        """
        Phase 2: ファイル選択フローの完全実行
        ピクチャ → メルカリ → 最新順ソート → ファイル選択 → 開く
        """
        try:
            print("Phase 2: ファイル選択フロー実行中...")
            
            # 2.1 ピクチャフォルダをクリック
            if 'folder_pictures' in self.coords:
                print("  ピクチャフォルダを選択...")
                pic_pos = self.coords['folder_pictures']
                pyautogui.click(pic_pos[0], pic_pos[1])
                time.sleep(1)
            else:
                print("警告: ピクチャフォルダの座標が未設定")
            
            # 2.2 メルカリフォルダをクリック
            if 'folder_mercari' in self.coords:
                print("  メルカリフォルダを開く...")
                mercari_pos = self.coords['folder_mercari']
                pyautogui.click(mercari_pos[0], mercari_pos[1])
                time.sleep(1)
            else:
                print("警告: メルカリフォルダの座標が未設定")
            
            # 2.3 最新順ソート（2回クリック）
            if 'sort_button' in self.coords:
                print("  ソートを最新順に設定...")
                sort_pos = self.coords['sort_button']
                
                # 1回目クリック（古い順になる）
                pyautogui.click(sort_pos[0], sort_pos[1])
                time.sleep(0.5)
                print("    1回目クリック完了（古い順）")
                
                # 2回目クリック（最新順になる）
                pyautogui.click(sort_pos[0], sort_pos[1])
                time.sleep(0.5)
                print("    2回目クリック完了（最新順）")
            else:
                print("警告: ソートボタンの座標が未設定")
            
            # 2.4 ファイルを選択
            if 'file_select_area' in self.coords:
                print("  最新の画像ファイルを選択...")
                file_pos = self.coords['file_select_area']
                pyautogui.click(file_pos[0], file_pos[1])
                time.sleep(0.5)
            else:
                print("警告: ファイル選択エリアの座標が未設定")
            
            # 2.5 開くボタンをクリック
            if 'open_button' in self.coords:
                print("  開くボタンをクリック...")
                open_pos = self.coords['open_button']
                pyautogui.click(open_pos[0], open_pos[1])
                time.sleep(3)  # アップロード・検索処理待機
                print("  画像アップロード・検索処理待機中...")
            else:
                print("警告: 開くボタンの座標が未設定")
            
            print("✓ ファイル選択フロー完了")
            return True
            
        except Exception as e:
            print(f"エラー: ファイル選択フロー失敗: {e}")
            return False

    def process_search_results_page(self) -> List[Dict]:
        """
        Phase 3: 検索結果の処理（1ページ分の商品を順次処理）
        """
        results = []
        processed_count = 0
        max_products = 10  # 最大処理商品数
        
        try:
            print("Phase 3: 検索結果処理を開始...")
            
            # 商品を1番目から順に処理
            for product_index in range(1, max_products + 1):
                print(f"\n--- 商品 {product_index} の処理開始 ---")
                
                try:
                    product_data = self.extract_product_with_image_check(product_index)
                    
                    if product_data:
                        results.append(product_data)
                        processed_count += 1
                        print(f"✓ 商品 {product_index} 処理成功")
                        
                        # 利益計算（メルカリ価格が必要）
                        if 'mercari_price' in product_data and 'alibaba_price' in product_data:
                            profit_info = self.calculate_profit(
                                product_data['mercari_price'],
                                product_data['alibaba_price'],
                                product_data.get('weight', 0.1)
                            )
                            product_data['profit_info'] = profit_info
                            print(f"  利益計算: {profit_info['profit']}円 ({profit_info['profit_rate']}%)")
                    else:
                        print(f"✗ 商品 {product_index} 処理失敗またはスキップ")
                    
                    # 処理間隔
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"エラー: 商品 {product_index} 処理中に例外: {e}")
                    continue
            
            print(f"\n✓ 検索結果処理完了: {processed_count}/{max_products}件成功")
            return results
            
        except Exception as e:
            print(f"エラー: 検索結果処理で例外: {e}")
            return results

    def extract_product_with_image_check(self, product_index: int) -> Optional[Dict]:
        """
        個別商品の処理（画像判定含む）
        Args:
            product_index: 商品番号（1-10）
        Returns:
            商品データまたはNone
        """
        try:
            # 4. 商品を新しいタブで開く
            if not self.open_product_in_new_tab(product_index):
                return None
            
            # 5. タブ切り替え（Control+Tab）
            self.switch_to_product_tab()
            
            # 6. 右下の写真エリアをクリック
            if not self.click_image_zoom_area():
                return None
            
            # 7. 大きくなった画像をキャプチャ & 判定
            image_ok = self.capture_and_judge_image()
            
            if image_ok:
                print("  画像判定: OK - データ取得を実行")
                
                # 8. 価格とMOQを取得
                product_data = self.extract_product_data(product_index)
                
                # 9. リンクをコピー
                product_url = self.copy_current_url()
                if product_url:
                    product_data['url'] = product_url
                
                # 10. ページを閉じる
                self.close_current_tab()
                
                return product_data
            else:
                print("  画像判定: NG - 次の商品へ")
                # 9. ページを閉じる
                self.close_current_tab()
                return None
                
        except Exception as e:
            print(f"エラー: 商品 {product_index} 個別処理で例外: {e}")
            try:
                self.close_current_tab()  # エラー時もタブを閉じる
            except:
                pass
            return None

    def open_product_in_new_tab(self, product_index: int) -> bool:
        """商品を新しいタブで開く（Control+クリック）"""
        try:
            # 商品位置の座標を取得
            if product_index == 1:
                coord_key = 'product_1_left'
            else:
                coord_key = f'product_{product_index}'
            
            if coord_key not in self.coords:
                print(f"エラー: {coord_key}の座標が設定されていません")
                return False
            
            product_pos = self.coords[coord_key]
            
            # Control+クリックで新しいタブで開く
            print(f"  商品 {product_index} をControl+クリック...")
            pyautogui.keyDown('ctrl')
            pyautogui.click(product_pos[0], product_pos[1])
            pyautogui.keyUp('ctrl')
            time.sleep(2)  # タブが開くまで待機
            
            return True
            
        except Exception as e:
            print(f"エラー: 商品 {product_index} オープン失敗: {e}")
            return False

    def switch_to_product_tab(self):
        """商品タブに切り替え（Control+Tab）"""
        try:
            print("  商品タブに切り替え...")
            pyautogui.hotkey('ctrl', 'tab')
            time.sleep(1)
        except Exception as e:
            print(f"エラー: タブ切り替え失敗: {e}")

    def click_image_zoom_area(self) -> bool:
        """右下の写真エリアをクリック"""
        try:
            if 'image_zoom_area' not in self.coords:
                print("エラー: 画像ズームエリアの座標が設定されていません")
                return False
            
            print("  右下の写真エリアをクリック...")
            zoom_pos = self.coords['image_zoom_area']
            pyautogui.click(zoom_pos[0], zoom_pos[1])
            time.sleep(1)  # 画像が大きくなるまで待機
            
            return True
            
        except Exception as e:
            print(f"エラー: 画像ズーム失敗: {e}")
            return False

    def capture_and_judge_image(self) -> bool:
        """
        画像キャプチャと判定（プレースホルダー実装）
        将来の画像判定ツール実装予定
        """
        try:
            if 'large_image_area' not in self.coords:
                print("警告: 大きい画像エリアの座標が設定されていません")
                # 座標なしでも処理継続（デフォルトでOK）
                return True
            
            print("  画像をキャプチャ中...")
            
            # スクリーンショット（将来の画像判定用）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot = pyautogui.screenshot()
            
            # デバッグ用保存
            save_path = Path(f'temp_images/alibaba_capture_{timestamp}.png')
            save_path.parent.mkdir(parents=True, exist_ok=True)
            screenshot.save(save_path)
            
            print(f"  画像保存: {save_path}")
            
            # TODO: ここに将来の画像判定ロジックを実装
            # 現在はプレースホルダーとして常にOKを返す
            print("  画像判定: OK（プレースホルダー - 将来実装予定）")
            return True
            
        except Exception as e:
            print(f"エラー: 画像判定で例外: {e}")
            # エラー時もOKとして処理継続
            return True

    def extract_product_data(self, product_index: int) -> Dict:
        """価格とMOQの取得"""
        product_data = {
            'product_index': product_index,
            'timestamp': datetime.now().isoformat(),
            'alibaba_price': None,
            'moq': None,
            'weight': 0.1,  # デフォルト値
            'title': None
        }
        
        try:
            # 価格取得
            price = self.extract_price_from_page()
            if price:
                product_data['alibaba_price'] = price
                print(f"  価格取得: {price}元")
            else:
                print("  価格取得: 失敗")
            
            # MOQ取得
            moq = self.extract_moq_from_page()
            if moq:
                product_data['moq'] = moq
                print(f"  MOQ取得: {moq}個")
            else:
                print("  MOQ取得: 失敗")
            
            # タイトル取得（オプション）
            title = self.extract_title_from_page()
            if title:
                product_data['title'] = title
                print(f"  タイトル: {title[:30]}...")
            
            return product_data
            
        except Exception as e:
            print(f"エラー: データ取得で例外: {e}")
            return product_data

    def extract_price_from_page(self) -> Optional[float]:
        """価格の抽出（クリップボード方式）"""
        try:
            if 'price_area' not in self.coords:
                print("警告: 価格エリアの座標が設定されていません")
                return None
            
            price_pos = self.coords['price_area']
            
            # 価格エリアをダブルクリックしてテキスト選択
            pyautogui.doubleClick(price_pos[0], price_pos[1])
            time.sleep(0.5)
            
            # コピー
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)
            
            # クリップボードから取得
            price_text = pyperclip.paste()
            
            # 数値部分を抽出（正規表現使用）
            price_match = re.search(r'[\d.]+', price_text.replace(',', ''))
            if price_match:
                return float(price_match.group())
            
            return None
            
        except Exception as e:
            print(f"エラー: 価格抽出で例外: {e}")
            return None

    def extract_moq_from_page(self) -> Optional[int]:
        """MOQの抽出"""
        try:
            if 'moq_area' not in self.coords:
                print("警告: MOQエリアの座標が設定されていません")
                return None
            
            moq_pos = self.coords['moq_area']
            
            # MOQエリアをダブルクリック
            pyautogui.doubleClick(moq_pos[0], moq_pos[1])
            time.sleep(0.5)
            
            # コピー
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)
            
            # クリップボードから取得
            moq_text = pyperclip.paste()
            
            # 数値部分を抽出
            moq_match = re.search(r'\d+', moq_text)
            if moq_match:
                return int(moq_match.group())
            
            return None
            
        except Exception as e:
            print(f"エラー: MOQ抽出で例外: {e}")
            return None

    def extract_title_from_page(self) -> Optional[str]:
        """商品タイトルの抽出（オプション）"""
        try:
            # タイトルエリアの座標があれば使用
            if 'product_title' in self.coords:
                title_pos = self.coords['product_title']
                pyautogui.tripleClick(title_pos[0], title_pos[1])
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.5)
                return pyperclip.paste().strip()
            
            return None
            
        except Exception as e:
            print(f"エラー: タイトル抽出で例外: {e}")
            return None

    def copy_current_url(self) -> Optional[str]:
        """現在のページのURLをコピー"""
        try:
            print("  URLをコピー中...")
            
            # アドレスバーにフォーカス
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.5)
            
            # コピー
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)
            
            # URLを取得
            url = pyperclip.paste()
            print(f"  URL: {url[:50]}...")
            
            return url
            
        except Exception as e:
            print(f"エラー: URL取得で例外: {e}")
            return None

    def close_current_tab(self):
        """現在のタブを閉じる（Control+W）"""
        try:
            print("  タブを閉じる...")
            pyautogui.hotkey('ctrl', 'w')
            time.sleep(1)
        except Exception as e:
            print(f"エラー: タブクローズで例外: {e}")

    def calculate_profit(self, mercari_price: int, alibaba_price: float, weight: float) -> Dict:
        """
        利益計算
        Args:
            mercari_price: メルカリ販売価格（円）
            alibaba_price: アリババ価格（元）
            weight: 商品重量（kg）
        Returns:
            利益情報の辞書
        """
        try:
            # 仕入れ原価（円）
            product_cost = alibaba_price * self.exchange_rate
            
            # 国際送料（重量ベース）
            shipping_cost = self.calculate_shipping(weight)
            
            # 代行手数料
            agent_fee = product_cost * self.agent_fee_rate
            
            # 関税（簡易税率）
            customs = (product_cost + shipping_cost) * self.customs_rate
            
            # 総仕入れコスト
            total_cost = product_cost + shipping_cost + agent_fee + customs
            
            # メルカリ手数料
            mercari_fee = mercari_price * self.mercari_fee_rate
            
            # 利益
            profit = mercari_price - total_cost - mercari_fee - self.domestic_shipping
            
            # 利益率
            profit_rate = (profit / mercari_price) * 100 if mercari_price > 0 else 0
            
            return {
                'total_cost': round(total_cost, 0),
                'profit': round(profit, 0),
                'profit_rate': round(profit_rate, 1),
                'breakdown': {
                    'product': round(product_cost, 0),
                    'shipping': round(shipping_cost, 0),
                    'agent': round(agent_fee, 0),
                    'customs': round(customs, 0),
                    'mercari_fee': round(mercari_fee, 0),
                    'domestic_shipping': self.domestic_shipping
                }
            }
            
        except Exception as e:
            print(f"エラー: 利益計算で例外: {e}")
            return {
                'total_cost': 0,
                'profit': 0,
                'profit_rate': 0,
                'breakdown': {}
            }

    def calculate_shipping(self, weight_kg: float) -> float:
        """
        国際送料計算
        Args:
            weight_kg: 重量（kg）
        Returns:
            送料（円）
        """
        # 重量別料金（元/kg）
        if weight_kg <= 0.5:
            rate_yuan = 50
        elif weight_kg <= 1.0:
            rate_yuan = 45
        elif weight_kg <= 5.0:
            rate_yuan = 40
        else:
            rate_yuan = 35
        
        shipping_yuan = weight_kg * rate_yuan
        shipping_yen = shipping_yuan * self.exchange_rate
        return shipping_yen

    def check_legal_compliance(self, product: Dict) -> bool:
        """
        法規制チェック（簡易版）
        Args:
            product: 商品情報
        Returns:
            問題なければTrue
        """
        try:
            title = product.get('title', '')
            
            # 基本的な禁止キーワードチェック
            prohibited_keywords = [
                '電池', 'バッテリー', '液体', '粉末', 
                '刃物', 'ナイフ', '薬品', '医薬品',
                '食品', '化粧品', 'PSE', '電気製品'
            ]
            
            for keyword in prohibited_keywords:
                if keyword in title:
                    print(f"法規制チェック: 禁止キーワード検出 - {keyword}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"エラー: 法規制チェックで例外: {e}")
            # エラー時は安全側に倒す
            return False

    def update_spreadsheet_with_sourcing(self, product: Dict):
        """
        スプレッドシートに仕入れ情報を更新
        Args:
            product: 商品情報（alibaba情報含む）
        """
        try:
            if not product.get('url'):
                print("警告: 商品URLがありません")
                return
            
            # 更新データ準備
            update_data = {
                'G': product.get('url', ''),  # 仕入URL
                'H': str(product.get('alibaba_price', 0)),  # 仕入価格
                'I': str(product.get('moq', 0)),  # MOQ
                'J': str(product.get('weight', 0)),  # 重量
            }
            
            # 利益情報があれば追加
            if 'profit_info' in product:
                profit_info = product['profit_info']
                update_data['M'] = f"{profit_info.get('profit_rate', 0)}%"  # 利益率
                update_data['N'] = str(profit_info.get('profit', 0))  # 利益額
            
            # スプレッドシート更新（実装はspreadsheet_managerに依存）
            if hasattr(self.spreadsheet, 'update_product_sourcing'):
                self.spreadsheet.update_product_sourcing(product.get('mercari_url', ''), update_data)
                print(f"スプレッドシート更新: {product.get('title', '')[:30]}...")
            else:
                print("スプレッドシート更新機能が利用できません")
            
        except Exception as e:
            print(f"エラー: スプレッドシート更新で例外: {e}")

    def save_results_to_file(self, results: List[Dict], filename_prefix: str = "alibaba_results"):
        """
        結果をJSONファイルに保存
        Args:
            results: 処理結果のリスト
            filename_prefix: ファイル名のプレフィックス
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{filename_prefix}_{timestamp}.json'
            filepath = Path('data/exports') / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # メタデータ付きで保存
            output_data = {
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'total_products': len(results),
                    'flow_version': 'new_flow_v1.0',
                    'exchange_rate': self.exchange_rate
                },
                'results': results
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n結果を保存しました: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"エラー: 結果保存で例外: {e}")
            return None

    # 旧フロー対応（後方互換性のため残す）
    def search_by_image_top3(self, image_path: str) -> List[Dict]:
        """
        旧フロー: 画像検索で上位3件を取得（後方互換性）
        新フローの使用を推奨
        """
        print("警告: 旧フローのメソッドです。新フロー search_by_image_new_flow() の使用を推奨します")
        
        # 新フローにリダイレクト
        return self.search_by_image_new_flow()


def main():
    """テスト実行用のメイン関数"""
    print("=" * 60)
    print("    アリババRPA仕入れモジュール テスト実行")
    print("=" * 60)
    
    # モックのスプレッドシート管理オブジェクト
    class MockSpreadsheet:
        def update_product_sourcing(self, url, data):
            print(f"モック: スプレッドシート更新 - {data}")
    
    try:
        # システム初期化
        alibaba = AlibabaSourcing(MockSpreadsheet())
        
        # 新フロー実行
        results = alibaba.search_by_image_new_flow()
        
        # 結果保存
        if results:
            alibaba.save_results_to_file(results)
            
            # サマリー表示
            print("\n" + "=" * 60)
            print("処理サマリー")
            print("=" * 60)
            print(f"処理商品数: {len(results)}")
            
            for i, result in enumerate(results, 1):
                print(f"商品 {i}:")
                print(f"  価格: {result.get('alibaba_price', '取得失敗')}元")
                print(f"  MOQ: {result.get('moq', '取得失敗')}個")
                print(f"  URL: {result.get('url', '取得失敗')[:50]}...")
                if 'profit_info' in result:
                    profit = result['profit_info']
                    print(f"  利益: {profit.get('profit', 0)}円 ({profit.get('profit_rate', 0)}%)")
        else:
            print("処理対象の商品がありませんでした")
    
    except Exception as e:
        print(f"システムエラー: {e}")


if __name__ == "__main__":
    main()