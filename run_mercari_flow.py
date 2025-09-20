"""
メルカリ統合フロー簡単実行スクリプト
コマンドライン引数で簡単に実行できるようにするラッパー
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from main_mercari_flow import MercariIntegratedFlow


def quick_run():
    """クイック実行（デフォルト設定）"""
    print("\n" + "=" * 60)
    print("メルカリ統合フロー - クイック実行")
    print("=" * 60)
    print("\n事前準備を確認してください:")
    print("1. Google Chromeが起動している")
    print("2. メルカリにログイン済み")
    print("3. メルカリのページが開いている")
    print("4. 座標設定が完了している")
    
    ready = input("\n準備ができていますか？ (y/n): ")
    if ready.lower() != 'y':
        print("準備ができたら再度実行してください")
        return
    
    # デフォルト設定で実行
    flow = MercariIntegratedFlow()
    
    # PC周辺機器カテゴリーで10件処理
    results = flow.run_integrated_search(
        category_path=['家電・スマホ・カメラ', 'PC/タブレット', 'PC周辺機器'],
        max_items=10,
        save_results=True
    )
    
    print(f"\n✅ 処理完了: {len(results)}件")
    
    # OK商品を表示
    ok_products = [p for p in results if p.get('is_business')]
    if ok_products:
        print(f"\n📊 業者商品（OK判定）: {len(ok_products)}件")
        for i, product in enumerate(ok_products[:5], 1):
            print(f"  {i}. {product.get('title', '不明')[:40]}...")
            print(f"     スコア: {product.get('judgment_score', 0)}点")
            print(f"     3日売上: {product.get('sales_3days', 0)}個")


def test_run():
    """テスト実行（少数で動作確認）"""
    print("\n" + "=" * 60)
    print("メルカリ統合フロー - テスト実行")
    print("=" * 60)
    print("※ 3件のみ処理してシステムの動作を確認します")
    
    flow = MercariIntegratedFlow()
    
    # 3件だけテスト
    results = flow.run_integrated_search(
        category_path=['家電・スマホ・カメラ', 'PC/タブレット', 'PC周辺機器'],
        max_items=3,
        save_results=False  # テストなので保存しない
    )
    
    print(f"\n✅ テスト完了: {len(results)}件処理")
    
    # 詳細表示
    for i, product in enumerate(results, 1):
        print(f"\n商品{i}:")
        print(f"  タイトル: {product.get('title', '不明')[:50]}...")
        print(f"  価格: {product.get('price', 0)}円")
        print(f"  判定: {'OK (業者)' if product.get('is_business') else 'NG (個人)'}")
        print(f"  スコア: {product.get('judgment_score', 0)}点")
        print(f"  理由: {', '.join(product.get('judgment_reasons', [])[:2])}")


def custom_run(category_name: str = 'pc', items: int = 10):
    """カスタム実行"""
    category_map = {
        'pc': ['家電・スマホ・カメラ', 'PC/タブレット', 'PC周辺機器'],
        'toy': ['おもちゃ・ホビー・グッズ', 'おもちゃ', 'キャラクターグッズ'],
        'sports': ['スポーツ・レジャー', 'トレーニング/エクササイズ', 'トレーニング用品']
    }
    
    if category_name not in category_map:
        print(f"❌ 不明なカテゴリー: {category_name}")
        print(f"利用可能: {', '.join(category_map.keys())}")
        return
    
    flow = MercariIntegratedFlow()
    
    results = flow.run_integrated_search(
        category_path=category_map[category_name],
        max_items=items,
        save_results=True
    )
    
    print(f"\n✅ 処理完了: {len(results)}件")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='メルカリ統合フロー実行')
    parser.add_argument(
        'mode',
        choices=['quick', 'test', 'custom'],
        default='quick',
        nargs='?',
        help='実行モード'
    )
    parser.add_argument(
        '--category',
        choices=['pc', 'toy', 'sports'],
        default='pc',
        help='カテゴリー（customモード用）'
    )
    parser.add_argument(
        '--items',
        type=int,
        default=10,
        help='処理する商品数（customモード用）'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'test':
        test_run()
    elif args.mode == 'custom':
        custom_run(args.category, args.items)
    else:
        quick_run()