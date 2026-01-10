#!/usr/bin/env python3
"""
Manga Creator ビルドスクリプト
Windows (.exe) / Mac (.app) / Linux の実行ファイルを作成します

使い方:
    python build.py
"""
import os
import subprocess
import sys
import shutil
import stat
from pathlib import Path

# スクリプトのディレクトリを基準にする
SCRIPT_DIR = Path(__file__).parent.resolve()


def check_pyinstaller():
    """PyInstallerがインストールされているか確認"""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        return False


def install_dependencies():
    """依存関係をインストール"""
    print("依存関係をインストールしています...")
    requirements_path = SCRIPT_DIR / "requirements.txt"

    if not requirements_path.exists():
        print(f"エラー: {requirements_path} が見つかりません。")
        sys.exit(1)

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"エラー: 依存関係のインストールに失敗しました: {e}")
        sys.exit(1)


def remove_readonly(func, path, excinfo):
    """読み取り専用属性を削除して再試行（Windows対応）"""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clean_build():
    """以前のビルド成果物を削除"""
    print("以前のビルド成果物を削除しています...")
    dirs_to_remove = ["build", "dist"]

    for dir_name in dirs_to_remove:
        dir_path = SCRIPT_DIR / dir_name
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path, onerror=remove_readonly)
                print(f"  削除: {dir_name}/")
            except PermissionError:
                print(f"エラー: {dir_name}/ を削除できません。")
                print("MangaCreator.exe が実行中でないことを確認してください。")
                sys.exit(1)
            except OSError as e:
                print(f"エラー: {dir_name}/ の削除に失敗: {e}")
                sys.exit(1)


def build_executable():
    """実行ファイルをビルド"""
    print("実行ファイルをビルドしています...")
    print("（これには数分かかる場合があります）")

    spec_path = SCRIPT_DIR / "manga_creator.spec"
    if not spec_path.exists():
        print(f"エラー: {spec_path} が見つかりません。")
        return False

    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", str(spec_path), "--noconfirm"],
            cwd=str(SCRIPT_DIR)
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("エラー: PyInstallerが見つかりません。")
        print("pip install pyinstaller を実行してください。")
        return False
    except OSError as e:
        print(f"エラー: ビルドプロセスの実行に失敗: {e}")
        return False


def main():
    print("=" * 50)
    print("Manga Creator ビルドスクリプト")
    print("=" * 50)
    print(f"ビルドディレクトリ: {SCRIPT_DIR}")
    print()

    # PyInstallerの確認
    if not check_pyinstaller():
        print("PyInstallerが見つかりません。インストールします...")
        install_dependencies()

    # クリーンビルド
    clean_build()
    print()

    # ビルド実行
    if build_executable():
        print()
        print("=" * 50)
        print("ビルド成功!")
        print("=" * 50)

        dist_path = SCRIPT_DIR / "dist"
        if sys.platform == "win32":
            exe_path = dist_path / "MangaCreator.exe"
        elif sys.platform == "darwin":
            exe_path = dist_path / "MangaCreator.app"
        else:
            exe_path = dist_path / "MangaCreator"

        if exe_path.exists():
            print(f"実行ファイル: {exe_path}")
            print()
            print("このファイルを配布してください。")
            print("ユーザーはダブルクリックで起動できます。")
        else:
            print(f"警告: 実行ファイルが見つかりません: {exe_path}")
            print("PyInstallerの出力を確認してください。")
            sys.exit(1)
    else:
        print()
        print("=" * 50)
        print("ビルド失敗")
        print("=" * 50)
        print("エラーログを確認してください。")
        sys.exit(1)


if __name__ == "__main__":
    main()
