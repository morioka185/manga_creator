"""一括画像生成ワーカー"""
import base64
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from src.services.forge_service import ForgeService
from src.services.forge_launcher import ForgeLauncher
from src.services.settings_service import SettingsService
from src.services.character_service import CharacterService
from src.services.story_import_service import StorySpec, StoryPanel, StoryPage
from src.services.template_service import TemplateService, PanelOrientation


@dataclass
class GeneratedPanel:
    """生成されたコマの情報"""
    page_index: int
    panel_index: int
    image_path: str
    prompt: str
    negative_prompt: str
    seed: str
    character_ids: List[str]
    # 一括生成時の最終プロンプト（再生成で同じ結果を得るため）
    final_prompt: str = ""
    final_negative_prompt: str = ""


class BatchGenerationWorker(QThread):
    """一括画像生成ワーカー"""

    # シグナル
    progress = pyqtSignal(int, int, str)  # (current, total, message)
    panel_generated = pyqtSignal(object)  # GeneratedPanel
    finished = pyqtSignal(bool, str, list)  # (success, message, generated_panels)

    def __init__(
        self,
        story_spec: StorySpec,
        width: int = 832,
        height: int = 1216,
        steps: int = 20,
        cfg_scale: float = 6.0,
        sampler_name: str = "Euler a",
        use_ip_adapter: bool = True,
        ip_adapter_weight: float = 0.8,
        common_prompt: str = "",
        common_negative_prompt: str = "",
        portrait_size: tuple = None,
        landscape_size: tuple = None,
        auto_size: bool = True,
        save_base_folder: Optional[str] = None,  # 保存先ベースフォルダ（ページごとにサブフォルダ作成）
        use_adetailer: bool = True,  # 複数キャラ時にADetailer（顔補正）を使用
        split_direction: str = "Columns",  # 複数キャラ時の分割方向 ("Columns" or "Rows")
        parent=None
    ):
        super().__init__(parent)
        self._story_spec = story_spec
        self._width = width
        self._height = height
        self._steps = steps
        self._cfg_scale = cfg_scale
        self._sampler_name = sampler_name
        self._use_ip_adapter = use_ip_adapter
        self._ip_adapter_weight = ip_adapter_weight
        self._common_prompt = common_prompt
        self._common_negative_prompt = common_negative_prompt
        # コマの形状に応じたサイズ設定
        self._portrait_size = portrait_size or (832, 1216)
        self._landscape_size = landscape_size or (1216, 832)
        self._auto_size = auto_size  # コマ形状に応じてサイズを自動調整するかどうか
        # 各ページのコマ向き情報をキャッシュ
        self._page_panel_orientations: Dict[int, List[PanelOrientation]] = {}
        # 保存先ベースフォルダ
        self._save_base_folder = save_base_folder
        # 複数キャラクター設定
        self._use_adetailer = use_adetailer
        self._split_direction = split_direction

        self._settings = SettingsService.get_instance()
        self._character_service = CharacterService.get_instance()
        self._cancelled = False
        self._generated_panels: List[GeneratedPanel] = []

    def cancel(self):
        """生成をキャンセル"""
        self._cancelled = True

    def _count_total_panels(self) -> int:
        """総コマ数をカウント"""
        total = 0
        for page in self._story_spec.pages:
            total += len(page.panels)
        return total

    def run(self):
        """生成処理実行"""
        try:
            base_url = self._settings.forge_api_url
            total_panels = self._count_total_panels()
            current_panel = 0

            if total_panels == 0:
                self.finished.emit(False, "生成するコマがありません", [])
                return

            # Forge接続確認
            self.progress.emit(0, total_panels, "Forgeに接続中...")
            if not ForgeService.check_connection(base_url):
                if self._settings.forge_auto_launch:
                    self.progress.emit(0, total_panels, "Forgeを起動中...")
                    launcher = ForgeLauncher.get_instance()

                    if not launcher.launch(
                        self._settings.forge_path,
                        api_only=self._settings.forge_api_only
                    ):
                        self.finished.emit(False, "Forgeの起動に失敗しました", [])
                        return

                    def progress_callback(elapsed):
                        self.progress.emit(0, total_panels, f"Forge起動待機中... ({elapsed}秒)")

                    if not launcher.wait_for_api(
                        base_url,
                        timeout=self._settings.forge_startup_timeout,
                        progress_callback=progress_callback
                    ):
                        self.finished.emit(False, "Forgeの起動がタイムアウトしました", [])
                        return
                else:
                    self.finished.emit(
                        False,
                        "Forgeに接続できません\n設定でForgeのパスとURLを確認してください",
                        []
                    )
                    return

            if self._cancelled:
                self.finished.emit(False, "キャンセルされました", self._generated_panels)
                return

            # Forge状態確認
            self.progress.emit(0, total_panels, "Forge状態を確認中...")
            ready, status_msg = ForgeService.check_ready(base_url)
            if not ready:
                self.finished.emit(False, status_msg, [])
                return

            # 保存先ディレクトリを決定
            if self._save_base_folder:
                base_dir = Path(self._save_base_folder) / "pages"
            else:
                base_dir = Path(tempfile.gettempdir()) / "MangaCreator" / "generated"
            base_dir.mkdir(parents=True, exist_ok=True)

            # ページをpage_numberでソート
            sorted_pages = sorted(self._story_spec.pages, key=lambda p: p.page_number)

            # デバッグ: ソート後のページ一覧を出力
            print(f"[BatchGeneration] Total pages: {len(sorted_pages)}")
            for i, p in enumerate(sorted_pages):
                print(f"[BatchGeneration]   sorted_pages[{i}]: page_number={p.page_number}, panels={len(p.panels)}")

            # 自動サイズ調整が有効な場合、各ページのコマ向き情報を計算
            if self._auto_size:
                self.progress.emit(0, total_panels, "コマサイズを計算中...")
                for page_idx, page in enumerate(sorted_pages):
                    orientations = TemplateService.get_panel_orientations(page.template)
                    self._page_panel_orientations[page_idx] = orientations
                    print(f"[BatchGeneration]   Page {page_idx} ({page.template}): {[o.value for o in orientations]}")

            # 各ページ・コマを生成
            for page_idx, page in enumerate(sorted_pages):
                # パネルをpanel_indexでソート
                sorted_panels = sorted(page.panels, key=lambda p: p.panel_index)
                for panel_idx, panel in enumerate(sorted_panels):
                    if self._cancelled:
                        self.finished.emit(
                            False,
                            "キャンセルされました",
                            self._generated_panels
                        )
                        return

                    current_panel += 1
                    self.progress.emit(
                        current_panel,
                        total_panels,
                        f"ページ{page.page_number} コマ{panel_idx + 1}を生成中..."
                    )

                    # 画像生成
                    result = self._generate_single_panel(
                        base_url, page_idx, panel_idx, panel, base_dir
                    )

                    if result:
                        self._generated_panels.append(result)
                        self.panel_generated.emit(result)
                    else:
                        # エラーでも続行（スキップ）
                        self.progress.emit(
                            current_panel,
                            total_panels,
                            f"ページ{page.page_number} コマ{panel_idx + 1}の生成をスキップ"
                        )

            # 完了
            success_count = len(self._generated_panels)
            self.finished.emit(
                True,
                f"{success_count}/{total_panels}コマの生成が完了しました",
                self._generated_panels
            )

        except Exception as e:
            self.finished.emit(False, f"エラー: {str(e)}", self._generated_panels)

    def _get_size_for_panel(self, page_idx: int, panel_idx: int) -> Tuple[int, int]:
        """コマの向きに応じた生成サイズを取得"""
        if not self._auto_size:
            return (self._width, self._height)

        # ページのコマ向き情報を取得
        orientations = self._page_panel_orientations.get(page_idx, [])

        if panel_idx < len(orientations):
            orientation = orientations[panel_idx]
            size = TemplateService.get_recommended_size(
                orientation,
                self._portrait_size,
                self._landscape_size
            )
            print(f"[BatchGeneration] Panel {page_idx}-{panel_idx}: {orientation.value} -> {size}")
            return size

        # インデックス外の場合はデフォルトサイズを使用
        return (self._width, self._height)

    def _generate_single_panel(
        self,
        base_url: str,
        page_idx: int,
        panel_idx: int,
        panel: StoryPanel,
        base_dir: Path
    ) -> Optional[GeneratedPanel]:
        """単一コマの画像生成"""
        try:
            # コマの向きに応じたサイズを取得
            width, height = self._get_size_for_panel(page_idx, panel_idx)

            # 進捗コールバック（無効化 - 一括生成では個別進捗は表示しない）
            def on_progress(progress_pct, step, total, status, elapsed):
                pass

            # キャラクター情報を収集
            characters = []  # [(Character, None), ...] のリスト
            ip_adapter_image = None
            ip_adapter_weight = self._ip_adapter_weight

            if panel.characters:
                print(f"[Batch] キャラクター検索開始: panel.characters={panel.characters}")
                for char_id in panel.characters:
                    story_char = self._story_spec.get_character_by_id(char_id)
                    print(f"[Batch] char_id={char_id}, story_char={story_char.name if story_char else None}")
                    if story_char:
                        # CharacterServiceから検索（大文字小文字無視）
                        char = self._character_service.get_by_name(story_char.name)
                        if not char:
                            for c in self._character_service.get_all():
                                if c.name.lower() == story_char.name.lower():
                                    char = c
                                    break
                        if char:
                            characters.append((char, None))  # (Character, individual_prompt)
                            print(f"[Batch] キャラクター追加: {char.name}")

                            # IP-Adapter用の参照画像（最初の有効なキャラクターのみ）
                            if self._use_ip_adapter and not ip_adapter_image and char.reference_image_path:
                                import os
                                if os.path.exists(char.reference_image_path):
                                    ip_adapter_image = ForgeService.image_to_base64(char.reference_image_path)
                                    print(f"[Batch] IP-Adapter使用: {char.name}, weight={ip_adapter_weight}")
                        else:
                            print(f"[Batch] キャラクターがCharacterServiceに登録されていません: {story_char.name}")
            else:
                print(f"[Batch] コマにキャラクター指定なし")

            # Regional Prompter / ADetailer 設定
            regional_prompter_args = None
            adetailer_args = None

            # 複数キャラクターの場合はBREAK区切り + Regional Prompter + ADetailer
            if len(characters) >= 2:
                final_prompt = self._build_multi_char_prompt(panel.prompt, characters)
                regional_prompter_args = self._build_regional_prompter_args(len(characters))
                if self._use_adetailer:
                    adetailer_args = self._build_adetailer_args()
                # 複数キャラモードではIP-Adapterは無効化（Regional Prompterと競合）
                ip_adapter_image = None
                print(f"[Batch] 複数キャラクターモード: {len(characters)}人, Regional Prompter有効")
            elif len(characters) == 1:
                # 単一キャラクターの場合
                char = characters[0][0]
                prompt_parts = []
                if char.default_prompt:
                    prompt_parts.append(char.default_prompt)
                if panel.prompt:
                    prompt_parts.append(panel.prompt)
                if self._common_prompt:
                    prompt_parts.append(self._common_prompt)
                final_prompt = ", ".join([p for p in prompt_parts if p])
                print(f"[Batch] 単一キャラクターモード: {char.name}")
            else:
                # キャラクターなしの場合
                prompt_parts = [panel.prompt]
                if self._common_prompt:
                    prompt_parts.append(self._common_prompt)
                final_prompt = ", ".join([p for p in prompt_parts if p])
                print(f"[Batch] キャラクターなしモード")

            # ネガティブプロンプトを構築: コマ別 + 共通
            neg_parts = [panel.negative_prompt]
            if self._common_negative_prompt:
                neg_parts.append(self._common_negative_prompt)
            final_negative_prompt = ", ".join([p for p in neg_parts if p])

            print(f"[Batch] 最終プロンプト: {final_prompt[:100]}...")

            success, result, used_seed = ForgeService.txt2img(
                base_url=base_url,
                prompt=final_prompt,
                negative_prompt=final_negative_prompt,
                width=width,
                height=height,
                steps=self._steps,
                cfg_scale=self._cfg_scale,
                seed=-1,
                sampler_name=self._sampler_name,
                ip_adapter_image=ip_adapter_image,
                ip_adapter_weight=ip_adapter_weight,
                regional_prompter_args=regional_prompter_args,
                adetailer_args=adetailer_args,
                progress_callback=on_progress,
            )

            if not success:
                print(f"生成エラー: {result}")
                return None

            # Base64画像をファイルに保存（ページごとにサブフォルダ）
            image_data = base64.b64decode(result)
            # save_base_folderが指定されている場合はページごとのサブフォルダを作成
            if self._save_base_folder:
                page_dir = base_dir / f"page_{page_idx + 1}"
                page_dir.mkdir(parents=True, exist_ok=True)
                image_path = page_dir / f"{uuid.uuid4()}.png"
            else:
                image_path = base_dir / f"{uuid.uuid4()}.png"

            with open(image_path, 'wb') as f:
                f.write(image_data)

            print(f"[BatchGeneration] Generated: page_idx={page_idx}, panel_idx={panel_idx}")
            return GeneratedPanel(
                page_index=page_idx,
                panel_index=panel_idx,  # ローカルインデックスを使用
                image_path=str(image_path),
                prompt=panel.prompt,
                negative_prompt=panel.negative_prompt,
                seed=used_seed,
                character_ids=panel.characters,
                final_prompt=final_prompt,  # 一括生成時の最終プロンプトを保存
                final_negative_prompt=final_negative_prompt
            )

        except Exception as e:
            print(f"コマ生成エラー: {e}")
            return None

    def _build_multi_char_prompt(self, panel_prompt: str, characters: List[tuple]) -> str:
        """複数キャラクター用プロンプトを構築（BREAK区切り）"""
        char_count = len(characters)
        count_words = {2: "2girls", 3: "3girls", 4: "4girls"}
        base_prompt = count_words.get(char_count, f"{char_count}girls")

        # コマ別プロンプトと共通プロンプトを追加
        if panel_prompt:
            base_prompt = f"{base_prompt}, {panel_prompt}"
        if self._common_prompt:
            base_prompt = f"{base_prompt}, {self._common_prompt}"

        # 各キャラクターのプロンプトをBREAKで区切る
        char_prompts = []
        for char, individual_prompt in characters:
            parts = []
            if char and char.default_prompt:
                parts.append(char.default_prompt)
            if individual_prompt:
                parts.append(individual_prompt)
            if not parts:
                parts.append("1girl")
            char_prompts.append(", ".join(parts))

        # BREAKで結合
        full_prompt = base_prompt + " BREAK " + " BREAK ".join(char_prompts)
        print(f"[Batch] 複数キャラクタープロンプト: {full_prompt[:100]}...")
        return full_prompt

    def _build_regional_prompter_args(self, char_count: int) -> Dict[str, Any]:
        """Regional Prompter設定を構築"""
        # 均等分割の比率を生成
        ratios = ",".join(["1"] * char_count)

        return {
            "active": True,
            "mode": "Matrix",
            "matrix_mode": self._split_direction,  # "Columns" or "Rows"
            "ratios": ratios,
            "use_base": False,
            "use_common": True,
            "use_neg_common": True,
            "calcmode": "Attention",
        }

    def _build_adetailer_args(self) -> List[Dict[str, Any]]:
        """ADetailer設定を構築（顔補正）"""
        return [{
            "ad_model": "face_yolov8n.pt",
            "ad_prompt": "",
            "ad_negative_prompt": "",
            "ad_confidence": 0.3,
            "ad_denoising_strength": 0.4,
        }]
