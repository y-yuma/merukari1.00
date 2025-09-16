"""
画像判定ツール - 簡易セットアップスクリプト（Mac対応）
"""

import os
import sys
from pathlib import Path

def create_directories():
    """必要ディレクトリ作成"""
    print("📁 ディレクトリ構造作成中...")
    
    required_dirs = [
        "config",
        "core", 
        "tools",
        "data",
        "data/images",
        "data/images/upload",
        "data/images/mercari_ok",
        "data/images/mercari_ng",
        "data/images/temp",
        "data/results",
        "logs"
    ]
    
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ {dir_path}")

def create_config_file():
    """設定ファイル作成"""
    print("\n⚙️ 設定ファイル作成中...")
    
    config_path = Path("config/config.json")
    if not config_path.exists():
        config_content = """{
  "system": {
    "version": "1.0.0"
  },
  "image_analysis": {
    "business_threshold": 70,
    "max_image_size": 1280
  },
  "folders": {
    "upload": "data/images/upload",
    "mercari_ok": "data/images/mercari_ok",
    "mercari_ng": "data/images/mercari_ng", 
    "temp": "data/images/temp",
    "results": "data/results",
    "logs": "logs"
  },
  "file_handling": {
    "supported_formats": [".jpg", ".jpeg", ".png", ".bmp"],
    "backup_original": true
  }
}"""
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print("✅ config/config.json")
    else:
        print("⚠️ config/config.json (既存)")

def create_init_files():
    """__init__.pyファイル作成"""
    init_files = ["core/__init__.py", "tools/__init__.py"]
    
    for init_file in init_files:
        init_path = Path(init_file)
        if not init_path.exists():
            init_path.touch()
            print(f"✅ {init_file}")

def create_readme():
    """README作成"""
    upload_readme = Path("data/images/upload/README.txt")
    if not upload_readme.exists():
        readme_content = """画像アップロード用フォルダ

使用方法:
1. 判定したい画像をこのフォルダに配置
2. python tools/image_judgment_tool.py interactive を実行
3. 結果は mercari_ok または mercari_ng フォルダに保存

対応形式: .jpg, .jpeg, .png, .bmp
"""
        with open(upload_readme, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print("✅ アップロード用README作成")

def check_python_packages():
    """Pythonパッケージチェック"""
    print("\n📦 パッケージチェック中...")
    
    required_packages = [
        ('opencv-python', 'cv2'),
        ('numpy', 'numpy'),
        ('pillow', 'PIL')
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name}")
    
    if missing_packages:
        print(f"\n💡 以下のコマンドでインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    """メイン実行"""
    print("🚀 メルカリ画像判定ツール - セットアップ開始")
    print("=" * 60)
    
    # ディレクトリ作成
    create_directories()
    
    # 設定ファイル作成
    create_config_file()
    
    # __init__.py作成
    create_init_files()
    
    # README作成
    create_readme()
    
    # パッケージチェック
    packages_ok = check_python_packages()
    
    print("\n" + "=" * 60)
    print("📋 セットアップ結果")
    print("=" * 60)
    
    if packages_ok:
        print("\n🎉 セットアップ完了！")
        print("\n🚀 次のステップ:")
        print("1. 画像を data/images/upload/ に配置")
        print("2. python tools/image_judgment_tool.py interactive で実行")
    else:
        print("\n⚠️ パッケージのインストールが必要です")
        print("上記のpipコマンドを実行してください")
    
    print(f"\n📁 プロジェクトルート: {Path.cwd()}")

if __name__ == "__main__":
    main()