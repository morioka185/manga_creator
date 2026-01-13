"""非同期画像生成ワーカー"""
import base64
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

from src.services.forge_service import ForgeService
from src.services.forge_launcher import ForgeLauncher
from src.services.settings_service import SettingsService
from src.models.character import Character


class GenerationWorker(QThread):
    """非同期画像生成ワーカー"""

    # シグナル
    progress = pyqtSignal(str)  # 進捗メッセージ
    finished = pyqtSignal(bool, str, str)  # (success, image_path or error, seed)

    def __init__(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: int = -1,
        sampler_name: str = "Euler a",
        character: Optional[Character] = None,
        pose_image_path: Optional[str] = None,
        controlnet_module: str = "openpose",
        controlnet_model: str = "",
        controlnet_weight: float = 1.0,
        # 複数キャラクターモード用パラメータ
        multi_char_mode: bool = False,
        characters: Optional[List[tuple]] = None,  # [(Character, prompt), ...]
        split_direction: str = "Columns",  # "Columns" or "Rows"
        use_adetailer: bool = True,
        # 保存先フォルダ（指定されない場合は一時フォルダ）
        save_folder: Optional[str] = None,
        # 一括生成モード（プロンプトを再構築しない）
        batch_mode: bool = False,
        # IP-Adapter用の参照画像パス（batch_mode時に直接指定）
        ip_adapter_image_path: Optional[str] = None,
        ip_adapter_weight: float = 0.8,
        parent=None
    ):
        super().__init__(parent)
        self._prompt = prompt
        self._negative_prompt = negative_prompt
        self._width = width
        self._height = height
        self._steps = steps
        self._cfg_scale = cfg_scale
        self._seed = seed
        self._sampler_name = sampler_name
        self._character = character
        self._pose_image_path = pose_image_path
        self._controlnet_module = controlnet_module
        self._controlnet_model = controlnet_model
        self._controlnet_weight = controlnet_weight
        # 複数キャラクターモード
        self._multi_char_mode = multi_char_mode
        self._characters = characters or []
        self._split_direction = split_direction
        self._use_adetailer = use_adetailer
        # 保存先フォルダ
        self._save_folder = save_folder
        # 一括生成モード
        self._batch_mode = batch_mode
        self._ip_adapter_image_path = ip_adapter_image_path
        self._ip_adapter_weight_override = ip_adapter_weight

        self._settings = SettingsService.get_instance()
        self._cancelled = False

    def cancel(self):
        """生成をキャンセル"""
        self._cancelled = True

    def run(self):
        """生成処理実行"""
        try:
            base_url = self._settings.forge_api_url

            # Forge接続確認
            self.progress.emit("Forgeに接続中...")
            if not ForgeService.check_connection(base_url):
                # 自動起動が有効なら起動を試みる
                if self._settings.forge_auto_launch:
                    self.progress.emit("Forgeを起動中...")
                    launcher = ForgeLauncher.get_instance()

                    if not launcher.launch(
                        self._settings.forge_path,
                        api_only=self._settings.forge_api_only
                    ):
                        self.finished.emit(False, "Forgeの起動に失敗しました", "")
                        return

                    # API待機
                    def progress_callback(elapsed):
                        self.progress.emit(f"Forge起動待機中... ({elapsed}秒)")

                    if not launcher.wait_for_api(
                        base_url,
                        timeout=self._settings.forge_startup_timeout,
                        progress_callback=progress_callback
                    ):
                        self.finished.emit(False, "Forgeの起動がタイムアウトしました", "")
                        return
                else:
                    self.finished.emit(
                        False,
                        "Forgeに接続できません\n設定でForgeのパスとURLを確認してください",
                        ""
                    )
                    return

            if self._cancelled:
                self.finished.emit(False, "キャンセルされました", "")
                return

            # モデルが選択されているか確認
            self.progress.emit("Forge状態を確認中...")
            ready, status_msg = ForgeService.check_ready(base_url)
            if not ready:
                self.finished.emit(False, status_msg, "")
                return
            self.progress.emit(status_msg)

            # プロンプト構築
            prompt = self._prompt
            regional_prompter_args = None
            adetailer_args = None

            if self._batch_mode:
                # 一括生成モード：プロンプトはそのまま使用（再構築しない）
                print(f"[Worker] 一括生成モードで生成: {prompt[:80]}...")
                # BREAK区切りがある場合（複数キャラ）はRegional Prompter + ADetailerを有効化
                if " BREAK " in prompt:
                    break_count = prompt.count(" BREAK ")
                    char_count = break_count  # BREAK数 = キャラクター数（base + キャラ数-1）
                    regional_prompter_args = self._build_regional_prompter_args_for_batch(char_count)
                    adetailer_args = self._build_adetailer_args()
                    print(f"[Worker] 一括生成モード: BREAK区切り検出 ({char_count}人), Regional Prompter有効")
            elif self._multi_char_mode and self._characters:
                # 複数キャラクターモード
                self.progress.emit("複数キャラクタープロンプトを構築中...")
                prompt = self._build_multi_char_prompt()
                regional_prompter_args = self._build_regional_prompter_args()
                if self._use_adetailer:
                    adetailer_args = self._build_adetailer_args()
            elif self._character and self._character.default_prompt:
                # 単一キャラクターモード
                prompt = f"{self._character.default_prompt}, {prompt}"

            # ControlNet設定
            controlnet_args = None
            if self._pose_image_path and self._controlnet_model:
                self.progress.emit("ポーズ画像を処理中...")
                pose_base64 = ForgeService.image_to_base64(self._pose_image_path)
                controlnet_args = [{
                    "enabled": True,
                    "module": self._controlnet_module,
                    "model": self._controlnet_model,
                    "image": pose_base64,
                    "weight": self._controlnet_weight,
                }]

            # IP-Adapter設定
            ip_adapter_image = None
            ip_adapter_weight = self._ip_adapter_weight_override

            if self._batch_mode and self._ip_adapter_image_path:
                # 一括生成モード：直接指定された参照画像を使用
                import os
                if os.path.exists(self._ip_adapter_image_path):
                    self.progress.emit("キャラクター参照画像を処理中...")
                    ip_adapter_image = ForgeService.image_to_base64(self._ip_adapter_image_path)
                    print(f"[Worker] 一括生成モード IP-Adapter: {self._ip_adapter_image_path}")
            elif not self._multi_char_mode and self._character and self._character.reference_image_path:
                # 通常モード：キャラクターから参照画像を取得
                self.progress.emit("キャラクター参照画像を処理中...")
                ip_adapter_image = ForgeService.image_to_base64(
                    self._character.reference_image_path
                )
                ip_adapter_weight = self._character.ip_adapter_weight

            if self._cancelled:
                self.finished.emit(False, "キャンセルされました", "")
                return

            # 画像生成（進捗コールバック付き）
            self.progress.emit("画像を生成中...")

            def on_progress(progress_pct, step, total, status, elapsed):
                if not self._cancelled:
                    if progress_pct > 0 or step > 0:
                        msg = f"生成中... {progress_pct:.0f}% ({step}/{total}) [{elapsed}秒経過]"
                        if status:
                            msg += f" {status}"
                    else:
                        msg = f"{status} [{elapsed}秒経過]" if status else f"準備中... [{elapsed}秒経過]"
                    self.progress.emit(msg)

            success, result, used_seed = ForgeService.txt2img(
                base_url=base_url,
                prompt=prompt,
                negative_prompt=self._negative_prompt,
                width=self._width,
                height=self._height,
                steps=self._steps,
                cfg_scale=self._cfg_scale,
                seed=self._seed,
                sampler_name=self._sampler_name,
                controlnet_args=controlnet_args,
                ip_adapter_image=ip_adapter_image,
                ip_adapter_weight=ip_adapter_weight,
                regional_prompter_args=regional_prompter_args,
                adetailer_args=adetailer_args,
                progress_callback=on_progress,
            )

            if not success:
                self.finished.emit(False, result, "")
                return

            # Base64画像をファイルに保存
            self.progress.emit("画像を保存中...")
            image_data = base64.b64decode(result)

            # 保存先フォルダを決定
            if self._save_folder:
                save_dir = Path(self._save_folder)
            else:
                save_dir = Path(tempfile.gettempdir()) / "MangaCreator" / "generated"
            save_dir.mkdir(parents=True, exist_ok=True)
            image_path = save_dir / f"{uuid.uuid4()}.png"

            with open(image_path, 'wb') as f:
                f.write(image_data)

            self.finished.emit(True, str(image_path), used_seed)

        except Exception as e:
            self.finished.emit(False, f"エラー: {str(e)}", "")

    def _build_multi_char_prompt(self) -> str:
        """複数キャラクター用プロンプトを構築（BREAK区切り）"""
        # 共通プロンプト（人数指定など）
        char_count = len(self._characters)
        count_words = {2: "2girls", 3: "3girls", 4: "4girls"}
        base_prompt = count_words.get(char_count, f"{char_count}girls")

        # 基本プロンプトを追加
        if self._prompt:
            base_prompt = f"{base_prompt}, {self._prompt}"

        # 各キャラクターのプロンプトをBREAKで区切る
        char_prompts = []
        for char, individual_prompt in self._characters:
            parts = []
            # キャラクターのデフォルトプロンプト
            if char and char.default_prompt:
                parts.append(char.default_prompt)
            # 個別プロンプト
            if individual_prompt:
                parts.append(individual_prompt)
            # 何も指定がない場合
            if not parts:
                parts.append("1girl")
            char_prompts.append(", ".join(parts))

        # BREAKで結合
        full_prompt = base_prompt + " BREAK " + " BREAK ".join(char_prompts)
        print(f"[Worker] 複数キャラクタープロンプト: {full_prompt[:100]}...")
        return full_prompt

    def _build_regional_prompter_args(self) -> Dict[str, Any]:
        """Regional Prompter設定を構築"""
        char_count = len(self._characters)
        # 均等分割の比率を生成
        ratios = ",".join(["1"] * char_count)

        return {
            "active": True,
            "mode": "Matrix",
            "matrix_mode": self._split_direction,  # "Columns" or "Rows"
            "ratios": ratios,
            "use_base": False,
            "use_common": True,  # 共通プロンプトを使用
            "use_neg_common": True,
            "calcmode": "Attention",
        }

    def _build_adetailer_args(self) -> List[Dict[str, Any]]:
        """ADetailer設定を構築（顔補正）"""
        # 顔検出モデルを使用
        return [{
            "ad_model": "face_yolov8n.pt",
            "ad_prompt": "",  # 空にすると元プロンプトを使用
            "ad_negative_prompt": "",
            "ad_confidence": 0.3,
            "ad_denoising_strength": 0.4,
        }]

    def _build_regional_prompter_args_for_batch(self, char_count: int) -> Dict[str, Any]:
        """batch_mode用のRegional Prompter設定を構築"""
        ratios = ",".join(["1"] * char_count)
        return {
            "active": True,
            "mode": "Matrix",
            "matrix_mode": "Columns",  # デフォルトは横並び
            "ratios": ratios,
            "use_base": False,
            "use_common": True,
            "use_neg_common": True,
            "calcmode": "Attention",
        }
