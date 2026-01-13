"""Forge起動管理サービス"""
import subprocess
import time
import sys
from pathlib import Path
from typing import Optional

from src.services.forge_service import ForgeService


class ForgeLauncher:
    """Forge起動管理（シングルトン）"""

    _instance: Optional['ForgeLauncher'] = None
    _process: Optional[subprocess.Popen] = None

    @classmethod
    def get_instance(cls) -> 'ForgeLauncher':
        """シングルトンインスタンス取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def launch(
        self,
        forge_path: str,
        api_port: int = 7860,
        additional_args: Optional[list] = None,
        api_only: bool = True
    ) -> bool:
        """
        Forgeを起動（--api フラグ付き）

        Args:
            forge_path: Forgeのインストールパス
            api_port: APIポート番号
            additional_args: 追加の起動引数
            api_only: UIなしでAPIのみモードで起動するか

        Returns:
            bool: 起動成功したかどうか
        """
        if self.is_running():
            return True

        forge_dir = Path(forge_path)
        launch_script = forge_dir / "launch.py"

        if not launch_script.exists():
            # webui.bat や run.bat を試す
            for script_name in ["webui.bat", "run.bat", "webui-user.bat"]:
                script = forge_dir / script_name
                if script.exists():
                    launch_script = script
                    break
            else:
                print(f"起動スクリプトが見つかりません: {forge_path}")
                return False

        # 起動コマンドを構築
        if launch_script.suffix == ".py":
            # Pythonスクリプトの場合
            venv_python = forge_dir / "venv" / "Scripts" / "python.exe"
            if venv_python.exists():
                cmd = [str(venv_python), str(launch_script)]
            else:
                cmd = [sys.executable, str(launch_script)]

            cmd.extend(["--api", f"--port={api_port}"])

            # APIのみモード（UIなし）
            if api_only:
                cmd.append("--nowebui")

            if additional_args:
                cmd.extend(additional_args)
        else:
            # バッチファイルの場合
            cmd = [str(launch_script)]

        try:
            # Forgeのログ出力用
            print(f"[ForgeLauncher] 起動コマンド: {' '.join(cmd)}")

            # CREATE_NEW_CONSOLE フラグで別コンソールウィンドウで起動
            # PIPEを使用しないことで、Forgeの標準入出力を正常に動作させる
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_CONSOLE

            self._process = subprocess.Popen(
                cmd,
                cwd=str(forge_dir),
                creationflags=creationflags,
            )
            return True

        except Exception as e:
            print(f"Forge起動エラー: {e}")
            return False

    def is_running(self) -> bool:
        """Forgeプロセスが実行中か確認"""
        if self._process is None:
            return False
        return self._process.poll() is None

    def wait_for_api(
        self,
        base_url: str,
        timeout: int = 120,
        progress_callback=None
    ) -> bool:
        """
        API接続可能になるまで待機

        Args:
            base_url: APIのベースURL
            timeout: タイムアウト秒数
            progress_callback: 進捗コールバック関数 (elapsed_seconds) -> None

        Returns:
            bool: 接続成功したかどうか
        """
        start = time.time()
        check_interval = 2

        while time.time() - start < timeout:
            elapsed = int(time.time() - start)

            if progress_callback:
                progress_callback(elapsed)

            if ForgeService.check_connection(base_url):
                return True

            # プロセスが終了していたら失敗
            if self._process and self._process.poll() is not None:
                return False

            time.sleep(check_interval)

        return False

    def shutdown(self):
        """Forgeプロセスを終了"""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
            finally:
                self._process = None

    def get_process_status(self) -> str:
        """プロセス状態を取得"""
        if self._process is None:
            return "停止中"

        poll_result = self._process.poll()
        if poll_result is None:
            return "実行中"
        else:
            return f"終了（コード: {poll_result}）"
