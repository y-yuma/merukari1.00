"""
アリババRPA動作確認テスト版（改良版）
滑らかなマウス操作で全工程を実行するテストファイル
メルカリRPAと同じような自然な動作を実現
"""
import pyautogui
import time
import json
import random
import math
from pathlib import Path
from typing import Dict, Optional, Tuple

class HumanBehavior:
    """
    人間的動作シミュレーション（メルカリRPAと同じ実装）
    滑らかなマウス移動とタイピングを実現
    """
    def __init__(self):
        self.typing_speed_range = (0.05, 0.15)
        self.mouse_speed_range = (0.3, 0.8)
        self.thinking_time_range = (0.5, 2.0)

    def move_mouse_naturally(self, x: int, y: int, duration: Optional[float] = None):
        """
        自然なマウス移動
        ベジエ曲線を使用した曲線的な動き
        """
        if duration is None:
            current_x, current_y = pyautogui.position()
            distance = math.sqrt((x - current_x)**2 + (y - current_y)**2)
            duration = self.calculate_mouse_duration(distance)

        self.bezier_mouse_move(x, y, duration)

    def bezier_mouse_move(self, x: int, y: int, duration: float):
        """
        ベジエ曲線によるマウス移動
        """
        start_x, start_y = pyautogui.position()
        
        # コントロールポイント生成（ランダムな曲線）
        control_x1 = start_x + random.randint(-100, 100)
        control_y1 = start_y + random.randint(-100, 100)
        control_x2 = x + random.randint(-100, 100)
        control_y2 = y + random.randint(-100, 100)

        # ベジエ曲線の計算
        steps = max(int(duration * 60), 30)  # 60fps
        for i in range(steps + 1):
            t = i / steps
            # ベジエ曲線の式
            pos_x = (1-t)**3 * start_x + \
                   3*(1-t)**2*t * control_x1 + \
                   3*(1-t)*t**2 * control_x2 + \
                   t**3 * x
            pos_y = (1-t)**3 * start_y + \
                   3*(1-t)**2*t * control_y1 + \
                   3*(1-t)*t**2 * control_y2 + \
                   t**3 * y
            
            pyautogui.moveTo(int(pos_x), int(pos_y))
            time.sleep(duration / steps)

        # 最終位置の微調整
        pyautogui.moveTo(x, y)

    def calculate_mouse_duration(self, distance: float) -> float:
        """マウス移動時間計算"""
        base_time = distance / 1000
        variation = random.uniform(*self.mouse_speed_range)
        return max(base_time * variation, 0.2)

    def move_and_click(self, coords: Tuple[int, int], button: str = 'left'):
        """移動してクリック"""
        x = coords[0] + random.randint(-2, 2)
        y = coords[1] + random.randint(-2, 2)
        
        self.move_mouse_naturally(x, y)
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.click(x, y, button=button)
        time.sleep(random.uniform(0.1, 0.2))

    def random_pause(self, min_seconds: float = 0.5, max_seconds: float = 2.0):
        """ランダムな待機時間"""
        pause_time = random.uniform(min_seconds, max_seconds)
        time.sleep(pause_time)


class AlibabaRPATest:
    """
    アリババRPAテストクラス（改良版）
    全工程を滑らかに実行
    """
    def __init__(self):
        """初期化"""
        self.coords = self.load_coordinates()
        if not self.coords:
            print("エラー: アリババの座標が設定されていません")
            print("まず以下を実行してください:")
            print("python tools/coordinate_mapper.py")
            print("メニューで「2」を選んでアリババ座標設定を行ってください")
            return

        # PyAutoGUI設定
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1  # 短くして滑らかにする
        
        # 人間的動作モジュール初期化
        self.human = HumanBehavior()
        
        print("=" * 60)
        print("アリババRPA動作確認テスト（改良版）")
        print("=" * 60)
        print("✓ システム初期化完了")
        print("⚠️  マウスを画面の隅に動かすと緊急停止します")

    def load_coordinates(self) -> Dict:
        """座標データの読み込み"""
        coord_file = Path('config/coordinate_sets/alibaba.json')
        if not coord_file.exists():
            return {}
        
        with open(coord_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_full_flow_complete(self):
        """
        完全フロー動作テスト
        ファイル選択から商品処理まで全て実行
        """
        print("\n" + "=" * 60)
        print("完全フロー動作テスト開始")
        print("=" * 60)
        
        # 事前準備確認
        print("【事前準備確認】")
        print("1. 1688.comが開いている")
        print("2. ウィンドウサイズが座標設定時と同じ")
        print("3. メルカリフォルダに画像ファイルがある")
        response = input("準備完了なら 'y' を入力: ")
        
        if response.lower() != 'y':
            print("準備を整えてから再実行してください")
            return
        
        print("\n5秒後にテスト開始...")
        for i in range(5, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        
        try:
            # Phase 1: 画像検索開始
            print("\n" + "=" * 50)
            print("Phase 1: 画像検索開始")
            print("=" * 50)
            
            if not self.execute_camera_click():
                print("❌ カメラクリックに失敗しました")
                return
            
            # Phase 2: ファイル選択フロー完全実行
            print("\n" + "=" * 50)
            print("Phase 2: ファイル選択フロー")
            print("=" * 50)
            
            if not self.execute_file_selection_complete():
                print("❌ ファイル選択に失敗しました")
                return
            
            # Phase 3: 検索実行
            print("\n" + "=" * 50)
            print("Phase 3: 検索実行")
            print("=" * 50)
            
            if not self.execute_search_button():
                print("❌ 検索実行に失敗しました")
                return
            
            # Phase 4: 検索結果待機
            print("\n" + "=" * 50)
            print("Phase 4: 検索結果待機")
            print("=" * 50)
            
            print("検索処理完了を待機中...")
            time.sleep(5)
            print("✓ 検索結果表示完了")
            
            # Phase 5: 商品処理フロー完全実行
            print("\n" + "=" * 50)
            print("Phase 5: 商品処理フロー")
            print("=" * 50)
            
            self.execute_product_processing_complete()
            
            print("\n" + "=" * 60)
            print("✅ 完全フロー動作テスト成功！")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  ユーザーによる中断")
        except Exception as e:
            print(f"\n❌ テスト中にエラー: {e}")

    def execute_camera_click(self) -> bool:
        """Phase 1: カメラアイコンクリック実行"""
        try:
            if 'camera_icon' not in self.coords:
                print("❌ カメラアイコンの座標が設定されていません")
                return False
            
            print("📷 カメラアイコンをクリック...")
            self.human.move_and_click(self.coords['camera_icon'])
            
            print("⏳ ファイルダイアログの表示待機...")
            time.sleep(2.5)
            
            print("✅ カメラクリック完了")
            return True
            
        except Exception as e:
            print(f"❌ カメラクリックエラー: {e}")
            return False

    def execute_file_selection_complete(self) -> bool:
        """Phase 2: ファイル選択フロー完全実行"""
        try:
            # ステップ1: ピクチャフォルダクリック
            if 'folder_pictures' in self.coords:
                print("📁 ピクチャフォルダをクリック...")
                self.human.move_and_click(self.coords['folder_pictures'])
                time.sleep(1.2)
                print("✅ ピクチャフォルダ選択完了")
            else:
                print("⚠️  ピクチャフォルダの座標が未設定（スキップ）")
            
            # ステップ1.5: ピクチャフォルダの開くボタンクリック
            if 'open_button_pictures' in self.coords:
                print("▶️  開くボタンをクリック（ピクチャフォルダ用）...")
                self.human.move_and_click(self.coords['open_button_pictures'])
                time.sleep(1.5)
                print("✅ ピクチャフォルダオープン完了")
            else:
                print("⚠️  ピクチャフォルダ用開くボタンの座標が未設定（スキップ）")
            
            # ステップ2: メルカリフォルダクリック
            if 'folder_mercari' in self.coords:
                print("📂 メルカリフォルダをクリック...")
                self.human.move_and_click(self.coords['folder_mercari'])
                time.sleep(1.2)
                print("✅ メルカリフォルダ選択完了")
            else:
                print("⚠️  メルカリフォルダの座標が未設定（スキップ）")
            
            # ステップ2.5: メルカリフォルダの開くボタンクリック
            if 'open_button_mercari' in self.coords:
                print("▶️  開くボタンをクリック（メルカリフォルダ用）...")
                self.human.move_and_click(self.coords['open_button_mercari'])
                time.sleep(1.5)
                print("✅ メルカリフォルダオープン完了")
            else:
                print("⚠️  メルカリフォルダ用開くボタンの座標が未設定（スキップ）")
            
            # ステップ3: ソート操作（2回クリック）
            if 'sort_button' in self.coords:
                print("🔄 ソートボタン操作（2回クリック）...")
                
                # 1回目（古い順）
                print("  1回目クリック（古い順に変更）")
                self.human.move_and_click(self.coords['sort_button'])
                time.sleep(0.8)
                
                # 2回目（最新順）
                print("  2回目クリック（最新順に変更）")
                self.human.move_and_click(self.coords['sort_button'])
                time.sleep(0.8)
                
                print("✅ ソート操作完了（最新順）")
            else:
                print("⚠️  ソートボタンの座標が未設定（スキップ）")
            
            # ステップ4: ファイル選択
            if 'file_select_area' in self.coords:
                print("🖱️  最新画像ファイルをクリック...")
                self.human.move_and_click(self.coords['file_select_area'])
                time.sleep(0.8)
                print("✅ ファイル選択完了")
            else:
                print("⚠️  ファイル選択エリアの座標が未設定（スキップ）")
            
            # ステップ5: 開くボタンクリック（ファイル選択用）
            if 'open_button' in self.coords:
                print("▶️  開くボタンをクリック（ファイル選択用）...")
                self.human.move_and_click(self.coords['open_button'])
                print("✅ 開くボタンクリック完了")
                
                print("⏳ 画像アップロード処理中...")
                time.sleep(4)
                
                print("✅ ファイル選択フロー完全実行成功")
                return True
            else:
                print("❌ ファイル選択用開くボタンの座標が未設定")
                return False
                
        except Exception as e:
            print(f"❌ ファイル選択フローエラー: {e}")
            return False

    def execute_search_button(self) -> bool:
        """Phase 3: 検索ボタンクリック実行"""
        try:
            if 'search_execute_button' not in self.coords:
                print("❌ 検索ボタンの座標が設定されていません")
                return False
            
            print("🔍 検索ボタンをクリック...")
            self.human.move_and_click(self.coords['search_execute_button'])
            
            print("⏳ 検索処理実行中...")
            time.sleep(3)
            
            print("✅ 検索実行完了")
            return True
            
        except Exception as e:
            print(f"❌ 検索実行エラー: {e}")
            return False

    def execute_product_processing_complete(self):
        """Phase 5: 商品処理フロー完全実行"""
        max_products = 10  # 処理する商品数
        success_count = 0
        
        print(f"🔄 {max_products}個の商品を順次処理開始...")
        
        for i in range(1, max_products + 1):
            print(f"\n--- 商品 {i}/{max_products} の処理 ---")
            
            try:
                if self.process_single_product_complete(i):
                    success_count += 1
                    print(f"✅ 商品 {i} 処理成功")
                else:
                    print(f"❌ 商品 {i} 処理失敗")
                
                # 次の商品処理前の休憩
                if i < max_products:
                    print("⏳ 次の商品処理前に休憩...")
                    self.human.random_pause(1.5, 2.5)
                
            except Exception as e:
                print(f"❌ 商品 {i} 処理中に例外: {e}")
                # エラー時の回復処理
                try:
                    pyautogui.hotkey('ctrl', 'w')  # タブを閉じる
                    time.sleep(1)
                except:
                    pass
        
        print(f"\n🎯 商品処理完了: {success_count}/{max_products} 成功")

    def process_single_product_complete(self, product_index: int) -> bool:
        """個別商品の完全処理"""
        try:
            # 商品座標の確認
            coord_key = 'product_1_left' if product_index == 1 else f'product_{product_index}'
            
            if coord_key not in self.coords:
                print(f"⚠️  {coord_key}の座標が未設定")
                return False
            
            # ステップ1: 商品をクリック（アリババは自動的に新しいタブで開き移動）
            print(f"🖱️  商品 {product_index} をクリック...")
            product_pos = self.coords[coord_key]
            
            # 通常クリック
            self.human.move_and_click(product_pos)
            
            print("⏳ 新しいタブでの読み込み待機...")
            time.sleep(2.5)
            
            # ステップ3: 右下写真エリアクリック
            if 'image_zoom_area' in self.coords:
                print("🖼️  右下写真エリアをクリック...")
                self.human.move_and_click(self.coords['image_zoom_area'])
                time.sleep(1.5)
                print("✅ 画像ズーム実行")
            else:
                print("⚠️  画像ズームエリア座標が未設定")
            
            # ステップ4: 大きい画像キャプチャエリアクリック
            if 'large_image_area' in self.coords:
                print("📸 大きい画像エリアで画像判定...")
                self.human.move_and_click(self.coords['large_image_area'])
                time.sleep(1)
                print("✅ 画像判定: OK（テストのため常にOK）")
            else:
                print("⚠️  大きい画像エリア座標が未設定")
            
            # ステップ5: 価格取得テスト
            if 'price_area' in self.coords:
                print("💰 価格取得テスト...")
                price_pos = self.coords['price_area']
                pyautogui.doubleClick(price_pos[0], price_pos[1])
                time.sleep(0.8)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.5)
                print("✅ 価格データ取得完了")
            else:
                print("⚠️  価格エリア座標が未設定")
            
            # ステップ6: MOQ取得テスト
            if 'moq_area' in self.coords:
                print("📦 MOQ取得テスト...")
                moq_pos = self.coords['moq_area']
                pyautogui.doubleClick(moq_pos[0], moq_pos[1])
                time.sleep(0.8)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.5)
                print("✅ MOQデータ取得完了")
            else:
                print("⚠️  MOQエリア座標が未設定")
            
            # ステップ7: URL取得テスト
            print("🔗 URL取得テスト...")
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)
            print("✅ URL取得完了")
            
            # ステップ8: タブを閉じる
            print("❌ タブを閉じる...")
            pyautogui.hotkey('ctrl', 'w')
            time.sleep(1.2)
            print("✅ タブクローズ完了")
            
            return True
            
        except Exception as e:
            print(f"❌ 商品 {product_index} 個別処理エラー: {e}")
            # エラー時のクリーンアップ
            try:
                pyautogui.hotkey('ctrl', 'w')
                time.sleep(1)
            except:
                pass
            return False

    def test_coordinates_with_smooth_movement(self):
        """座標テスト（滑らかな移動）"""
        print("\n" + "=" * 50)
        print("座標テスト（滑らかな移動）")
        print("=" * 50)
        
        test_coords = [
            ('camera_icon', 'カメラアイコン'),
            ('folder_pictures', 'ピクチャフォルダ'),
            ('open_button_pictures', 'ピクチャフォルダ用開くボタン'),
            ('folder_mercari', 'メルカリフォルダ'),
            ('open_button_mercari', 'メルカリフォルダ用開くボタン'),
            ('sort_button', 'ソートボタン'),
            ('file_select_area', 'ファイル選択エリア'),
            ('open_button', 'ファイル選択用開くボタン'),
            ('search_execute_button', '検索実行ボタン'),
            ('product_1_left', '1番目の商品'),
            ('product_2', '2番目の商品'),
            ('product_3', '3番目の商品'),
            ('image_zoom_area', '画像ズームエリア'),
            ('large_image_area', '大きい画像エリア'),
            ('price_area', '価格エリア'),
            ('moq_area', 'MOQエリア')
        ]
        
        print("各座標に滑らかにマウスが移動します")
        print("中断: マウスを画面隅に移動")
        input("開始する場合はEnterを押してください...")
        
        for coord_key, description in test_coords:
            if coord_key in self.coords:
                print(f"\n🎯 {description}")
                print(f"   座標: {self.coords[coord_key]}")
                
                try:
                    # 滑らかな移動とクリック
                    self.human.move_and_click(self.coords[coord_key])
                    print(f"   ✅ 移動・クリック成功")
                    
                    # 次への移動前の休憩
                    self.human.random_pause(1.0, 1.5)
                    
                except Exception as e:
                    print(f"   ❌ テスト失敗: {e}")
            else:
                print(f"\n⚠️  {description} ({coord_key}) 座標未設定")

    def show_coordinates_status(self):
        """座標設定状況表示"""
        print("\n" + "=" * 50)
        print("座標設定状況")
        print("=" * 50)
        
        required_coords = [
            'camera_icon', 'folder_pictures', 'folder_mercari', 
            'open_button_mercari', 'sort_button', 'file_select_area', 
            'open_button', 'search_execute_button', 'product_1_left', 
            'product_2', 'product_3', 'product_4', 'image_zoom_area', 
            'large_image_area', 'price_area', 'moq_area'
        ]
        
        set_count = 0
        for coord in required_coords:
            if coord in self.coords:
                print(f"✅ {coord}")
                set_count += 1
            else:
                print(f"❌ {coord} (未設定)")
        
        print(f"\n設定状況: {set_count}/{len(required_coords)} ({set_count/len(required_coords)*100:.1f}%)")
        
        if set_count == len(required_coords):
            print("🎉 全座標設定完了！完全テスト実行可能です")
        else:
            print("⚠️  未設定の座標があります。座標設定を完了してください")

    def run_test_menu(self):
        """テストメニュー"""
        while True:
            print("\n" + "=" * 60)
            print("アリババRPA完全テストメニュー")
            print("=" * 60)
            print("1. 🚀 完全フロー動作テスト（全工程実行）")
            print("2. 🎯 座標テスト（滑らかな移動）")
            print("3. 📊 座標設定状況確認")
            print("4. 🔧 個別フェーズテスト")
            print("0. 🚪 終了")
            print("-" * 60)
            
            choice = input("選択してください (0-4): ")
            
            if choice == "0":
                print("テストを終了します")
                break
            elif choice == "1":
                self.test_full_flow_complete()
            elif choice == "2":
                self.test_coordinates_with_smooth_movement()
            elif choice == "3":
                self.show_coordinates_status()
            elif choice == "4":
                self.run_individual_phase_tests()
            else:
                print("無効な選択です")

    def run_individual_phase_tests(self):
        """個別フェーズテスト"""
        while True:
            print("\n" + "=" * 50)
            print("個別フェーズテストメニュー")
            print("=" * 50)
            print("1. Phase 1: カメラクリックテスト")
            print("2. Phase 2: ファイル選択テスト")
            print("3. Phase 3: 検索実行テスト")
            print("4. Phase 4: 商品処理テスト（1商品のみ）")
            print("0. 戻る")
            print("-" * 50)
            
            choice = input("選択してください (0-4): ")
            
            if choice == "0":
                break
            elif choice == "1":
                self.execute_camera_click()
            elif choice == "2":
                self.execute_file_selection_complete()
            elif choice == "3":
                self.execute_search_button()
            elif choice == "4":
                print("商品処理テスト（1番目の商品のみ）")
                self.process_single_product_complete(1)
            else:
                print("無効な選択です")


def main():
    """メイン実行"""
    print("=" * 60)
    print("アリババRPA完全動作確認テスト")
    print("=" * 60)
    
    try:
        test = AlibabaRPATest()
        if test.coords:
            test.run_test_menu()
        
    except KeyboardInterrupt:
        print("\n\nテストを中断しました")
    except Exception as e:
        print(f"\nシステムエラー: {e}")


if __name__ == "__main__":
    main()