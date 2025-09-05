#!/bin/bash
echo "========================================"
echo "メルカリ自動化システム起動"
echo "========================================"
echo

# Python仮想環境の有効化
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "エラー: 仮想環境が見つかりません"
    echo "python3 -m venv venv を実行してください"
    exit 1
fi

# 座標設定確認
if [ ! -f "config/coordinate_sets/mercari.json" ]; then
    echo "座標設定が見つかりません"
    echo "初期設定を開始します..."
    python3 tools/coordinate_mapper.py
    if [ $? -ne 0 ]; then
        echo "座標設定に失敗しました"
        exit 1
    fi
fi

# システム起動
echo
echo "システムを起動しています..."
python3 main.py

# エラーチェック
if [ $? -ne 0 ]; then
    echo
    echo "エラーが発生しました"
    echo "ログファイルを確認してください: logs/error.log"
fi

echo
echo "システムを終了しました"