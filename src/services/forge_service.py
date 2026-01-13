"""Stable Diffusion WebUI Forge API通信サービス"""
import base64
import requests
from typing import Tuple, List, Optional, Dict, Any


class ForgeError(Exception):
    """Forge関連エラー基底クラス"""
    pass


class ForgeConnectionError(ForgeError):
    """接続エラー"""
    pass


class ForgeAPIError(ForgeError):
    """API呼び出しエラー"""
    pass


class ForgeService:
    """Stable Diffusion WebUI Forge API通信サービス"""

    DEFAULT_TIMEOUT = 10
    GENERATION_TIMEOUT = 600  # 10分に延長

    @staticmethod
    def check_connection(base_url: str) -> bool:
        """API接続確認"""
        try:
            response = requests.get(
                f"{base_url}/sdapi/v1/progress",
                timeout=ForgeService.DEFAULT_TIMEOUT
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    @staticmethod
    def get_models(base_url: str) -> List[str]:
        """利用可能なモデル一覧取得"""
        try:
            response = requests.get(
                f"{base_url}/sdapi/v1/sd-models",
                timeout=ForgeService.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            return [model['title'] for model in response.json()]
        except requests.RequestException as e:
            raise ForgeAPIError(f"モデル一覧の取得に失敗: {e}")

    @staticmethod
    def get_samplers(base_url: str) -> List[str]:
        """サンプラー一覧取得"""
        try:
            response = requests.get(
                f"{base_url}/sdapi/v1/samplers",
                timeout=ForgeService.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            return [sampler['name'] for sampler in response.json()]
        except requests.RequestException as e:
            raise ForgeAPIError(f"サンプラー一覧の取得に失敗: {e}")

    @staticmethod
    def get_controlnet_models(base_url: str) -> List[str]:
        """ControlNetモデル一覧取得"""
        try:
            response = requests.get(
                f"{base_url}/controlnet/model_list",
                timeout=ForgeService.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            return data.get('model_list', [])
        except requests.RequestException:
            return []

    @staticmethod
    def get_controlnet_modules(base_url: str) -> List[str]:
        """ControlNetプリプロセッサ一覧取得"""
        try:
            response = requests.get(
                f"{base_url}/controlnet/module_list",
                timeout=ForgeService.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            return data.get('module_list', [])
        except requests.RequestException:
            return []

    @staticmethod
    def get_ip_adapter_models(base_url: str) -> List[str]:
        """IP-Adapterモデル一覧取得（ControlNet経由）"""
        try:
            models = ForgeService.get_controlnet_models(base_url)
            # IP-Adapterモデルをフィルタリング
            ip_models = [m for m in models if 'ip-adapter' in m.lower() or 'ip_adapter' in m.lower()]
            return ip_models
        except Exception:
            return []

    @staticmethod
    def find_best_ip_adapter_model(base_url: str, is_sdxl: bool = False) -> Optional[str]:
        """最適なIP-Adapterモデルを検索"""
        models = ForgeService.get_ip_adapter_models(base_url)
        if not models:
            return None

        # SDXLまたはSD1.5用のモデルを優先
        for model in models:
            model_lower = model.lower()
            if is_sdxl:
                if 'sdxl' in model_lower:
                    return model
            else:
                if 'sd15' in model_lower or 'sd1.5' in model_lower:
                    return model

        # マッチしなければ最初のモデルを返す
        return models[0] if models else None

    @staticmethod
    def image_to_base64(image_path: str) -> str:
        """画像ファイルをBase64エンコード"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    @staticmethod
    def txt2img(
        base_url: str,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: int = -1,
        sampler_name: str = "Euler a",
        controlnet_args: Optional[List[Dict[str, Any]]] = None,
        ip_adapter_image: Optional[str] = None,
        ip_adapter_weight: float = 0.8,
        regional_prompter_args: Optional[Dict[str, Any]] = None,
        adetailer_args: Optional[List[Dict[str, Any]]] = None,
        progress_callback=None
    ) -> Tuple[bool, str, str]:
        """
        txt2img API呼び出し（進捗コールバック対応）

        Args:
            progress_callback: 進捗コールバック関数 (progress_percent, step, total_steps, status_message, elapsed_sec) -> None
            regional_prompter_args: Regional Prompter設定（複数キャラクター用）
            adetailer_args: ADetailer設定（顔補正用）

        Returns:
            Tuple[bool, str, str]: (成功フラグ, Base64画像またはエラーメッセージ, 使用シード)
        """
        import threading
        import time

        # サンプラー名が空の場合はデフォルト値を使用
        if not sampler_name or sampler_name.strip() == "":
            sampler_name = "Euler"

        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "seed": seed,
            "sampler_name": sampler_name,
            "batch_size": 1,
            "n_iter": 1,
            "save_images": False,
            "send_images": True,
        }

        # デバッグ: ペイロード内容をログ
        print(f"[Forge] ペイロード: prompt={prompt[:50]}..., size={width}x{height}, steps={steps}, sampler={sampler_name}")

        # alwayson_scripts の初期化
        alwayson_scripts: Dict[str, Any] = {}

        # ControlNet/IP-Adapter設定（オプション）
        # 注意: これらの機能はForge側で拡張機能が有効な場合のみ動作
        controlnet_units = []

        if controlnet_args:
            controlnet_units.extend(controlnet_args)

        # IP-Adapter設定（参照画像がある場合）
        if ip_adapter_image:
            # IP-Adapterモデルを自動検出
            ip_model = ForgeService.find_best_ip_adapter_model(base_url)
            if ip_model:
                print(f"[Forge] IP-Adapter使用: {ip_model}, weight={ip_adapter_weight}")
                controlnet_units.append({
                    "enabled": True,
                    "module": "ip-adapter_clip_h",  # CLIP特徴抽出
                    "model": ip_model,
                    "image": ip_adapter_image,
                    "weight": ip_adapter_weight,
                    "resize_mode": "Crop and Resize",
                    "control_mode": "Balanced",
                })
            else:
                print("[Forge] IP-Adapterモデルが見つかりません。参照画像なしで生成します。")

        if controlnet_units:
            alwayson_scripts["ControlNet"] = {"args": controlnet_units}

        # 利用可能なスクリプトを取得（拡張機能の存在確認用）
        available_scripts = []
        try:
            scripts_data = ForgeService.get_scripts(base_url)
            available_scripts = [s.lower() for s in scripts_data.get("txt2img", [])]
        except Exception:
            pass

        # Regional Prompter設定（複数キャラクター用）
        if regional_prompter_args:
            # Regional Prompterが利用可能か確認
            rp_available = any("regional" in s and "prompt" in s for s in available_scripts)
            if rp_available:
                print(f"[Forge] Regional Prompter使用: {regional_prompter_args.get('mode', 'Columns')}")
                # Regional Prompterのargs配列を構築
                rp_args = [
                    regional_prompter_args.get("active", True),      # 1. Active
                    regional_prompter_args.get("debug", False),      # 2. Debug
                    regional_prompter_args.get("mode", "Matrix"),    # 3. Mode
                    regional_prompter_args.get("matrix_mode", "Columns"),  # 4. Mode(Matrix)
                    "Mask",                                          # 5. Mode(Mask)
                    "Prompt",                                        # 6. Mode(Prompt)
                    regional_prompter_args.get("ratios", "1,1"),     # 7. Ratios
                    "0",                                             # 8. Base Ratios
                    regional_prompter_args.get("use_base", False),   # 9. Use Base
                    regional_prompter_args.get("use_common", False), # 10. Use Common
                    regional_prompter_args.get("use_neg_common", False),  # 11. Use Neg-Common
                    regional_prompter_args.get("calcmode", "Attention"),  # 12. Calcmode
                    False,                                           # 13. Not Change AND
                    "0",                                             # 14. LoRA Textencoder
                    "0",                                             # 15. LoRA U-Net
                    "0",                                             # 16. Threshold
                    "",                                              # 17. Mask
                    "0",                                             # 18. LoRA stop step
                    "0",                                             # 19. LoRA Hires stop step
                    False                                            # 20. Flip
                ]
                alwayson_scripts["Regional Prompter"] = {"args": rp_args}
            else:
                print("[Forge] Regional Prompter未インストール: スキップして通常生成します")

        # ADetailer設定（顔補正用）
        if adetailer_args:
            # ADetailerが利用可能か確認
            ad_available = any("adetailer" in s for s in available_scripts)
            if ad_available:
                print(f"[Forge] ADetailer使用: {len(adetailer_args)}個のモデル")
                ad_args = [
                    True,   # ad_enable
                    False,  # skip_img2img
                ]
                # 各検出モデルの設定を追加
                for ad_config in adetailer_args:
                    ad_args.append({
                        "ad_model": ad_config.get("ad_model", "face_yolov8n.pt"),
                        "ad_prompt": ad_config.get("ad_prompt", ""),
                        "ad_negative_prompt": ad_config.get("ad_negative_prompt", ""),
                        "ad_confidence": ad_config.get("ad_confidence", 0.3),
                        "ad_denoising_strength": ad_config.get("ad_denoising_strength", 0.4),
                    })
                alwayson_scripts["ADetailer"] = {"args": ad_args}
            else:
                print("[Forge] ADetailer未インストール: スキップして通常生成します")

        if alwayson_scripts:
            payload["alwayson_scripts"] = alwayson_scripts

        # 結果を格納する変数
        result_container = {"response": None, "error": None}

        def make_request():
            try:
                # デバッグ: リクエスト内容をログ
                print(f"[Forge] リクエスト: {width}x{height}, steps={steps}, sampler={sampler_name}")

                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                response = requests.post(
                    f"{base_url}/sdapi/v1/txt2img",
                    json=payload,
                    headers=headers,
                    timeout=ForgeService.GENERATION_TIMEOUT
                )
                if response.status_code != 200:
                    # エラーレスポンスの詳細を取得
                    error_text = response.text
                    print(f"[Forge] エラーレスポンス (HTTP {response.status_code}): {error_text}")

                    try:
                        error_detail = response.json()
                        if 'detail' in error_detail:
                            detail = error_detail['detail']
                            if isinstance(detail, list):
                                # バリデーションエラーの詳細
                                msgs = [f"{e.get('loc', '')}: {e.get('msg', '')}" for e in detail]
                                result_container["error"] = f"パラメータエラー:\n" + "\n".join(msgs)
                            else:
                                result_container["error"] = f"Forgeエラー: {detail}"
                        elif 'error' in error_detail:
                            error_msg = error_detail['error']
                            # エラーメッセージに詳細情報を追加
                            if 'errors' in error_detail:
                                error_msg += f"\n詳細: {error_detail['errors']}"
                            result_container["error"] = f"Forgeエラー: {error_msg}"
                        elif 'errors' in error_detail:
                            result_container["error"] = f"Forgeエラー: {error_detail['errors']}"
                        elif 'message' in error_detail:
                            result_container["error"] = f"Forgeエラー: {error_detail['message']}"
                        else:
                            result_container["error"] = f"Forgeエラー ({response.status_code}): {error_text[:1000]}"
                    except Exception as parse_err:
                        print(f"[Forge] JSONパースエラー: {parse_err}")
                        result_container["error"] = f"Forgeエラー ({response.status_code}): {error_text[:1000]}"
                    return
                result_container["response"] = response.json()
            except requests.exceptions.Timeout:
                result_container["error"] = "タイムアウト: Forgeからの応答がありません"
            except requests.exceptions.ConnectionError:
                result_container["error"] = "接続エラー: Forgeに接続できません"
            except Exception as e:
                import traceback
                result_container["error"] = f"例外: {str(e)}\n{traceback.format_exc()}"

        # リクエストを別スレッドで実行
        request_thread = threading.Thread(target=make_request)
        request_thread.start()

        # 進捗をポーリング
        start_time = time.time()
        while request_thread.is_alive():
            if progress_callback:
                try:
                    elapsed = int(time.time() - start_time)
                    progress_data = ForgeService.get_progress(base_url)
                    progress_pct = progress_data.get('progress', 0) * 100
                    state = progress_data.get('state', {})
                    step = state.get('sampling_step', 0)
                    total = state.get('sampling_steps', steps)
                    job = state.get('job', '')
                    eta = progress_data.get('eta_relative', 0)

                    # 状態メッセージの生成
                    if progress_pct == 0 and step == 0:
                        if job:
                            status = f"準備中 ({job})..."
                        else:
                            status = "モデル読込/準備中..."
                    else:
                        if eta > 0:
                            status = f"残り約{int(eta)}秒"
                        else:
                            status = ""

                    progress_callback(progress_pct, step, total, status, elapsed)
                except Exception:
                    # エラー時も経過時間は表示
                    elapsed = int(time.time() - start_time)
                    progress_callback(0, 0, steps, "接続中...", elapsed)

            # タイムアウトチェック
            if time.time() - start_time > ForgeService.GENERATION_TIMEOUT:
                return False, "生成がタイムアウトしました", ""

            time.sleep(0.5)  # ポーリング間隔を短縮

        request_thread.join()

        # エラーチェック
        if result_container["error"]:
            return False, f"API呼び出しエラー: {result_container['error']}", ""

        result = result_container["response"]
        if not result:
            return False, "レスポンスが空です", ""

        images = result.get('images', [])

        if not images:
            return False, "画像が生成されませんでした", ""

        # 最初の画像を返す（Base64エンコード済み）
        info = result.get('info', '{}')
        if isinstance(info, str):
            import json
            try:
                info_dict = json.loads(info)
                used_seed = str(info_dict.get('seed', ''))
            except:
                used_seed = ''
        else:
            used_seed = str(info.get('seed', ''))

        return True, images[0], used_seed

    @staticmethod
    def get_progress(base_url: str) -> Dict[str, Any]:
        """生成進捗を取得"""
        try:
            response = requests.get(
                f"{base_url}/sdapi/v1/progress",
                timeout=ForgeService.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return {"progress": 0, "state": {"job": ""}}

    @staticmethod
    def get_options(base_url: str) -> Dict[str, Any]:
        """現在のForge設定を取得"""
        try:
            response = requests.get(
                f"{base_url}/sdapi/v1/options",
                timeout=ForgeService.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return {}

    @staticmethod
    def check_ready(base_url: str) -> Tuple[bool, str]:
        """Forgeが生成可能な状態か確認"""
        try:
            options = ForgeService.get_options(base_url)
            model = options.get('sd_model_checkpoint', '')
            if not model:
                return False, "モデルが選択されていません。Forgeでモデルを選択してください。"
            return True, f"モデル: {model}"
        except Exception as e:
            return False, f"状態確認エラー: {e}"

    @staticmethod
    def get_scripts(base_url: str) -> Dict[str, List[str]]:
        """利用可能なスクリプト一覧取得"""
        try:
            response = requests.get(
                f"{base_url}/sdapi/v1/scripts",
                timeout=ForgeService.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return {"txt2img": [], "img2img": []}

    @staticmethod
    def get_extensions(base_url: str) -> List[Dict[str, Any]]:
        """インストール済み拡張機能一覧取得"""
        try:
            response = requests.get(
                f"{base_url}/sdapi/v1/extensions",
                timeout=ForgeService.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return []

    @staticmethod
    def check_extension_status(base_url: str) -> Dict[str, Dict[str, Any]]:
        """
        複数キャラクター生成に必要な拡張機能の状態を確認

        Returns:
            Dict with extension status:
            {
                "regional_prompter": {"installed": bool, "enabled": bool, "name": str},
                "adetailer": {"installed": bool, "enabled": bool, "name": str},
                "controlnet": {"installed": bool, "enabled": bool, "name": str},
            }
        """
        result = {
            "regional_prompter": {"installed": False, "enabled": False, "name": ""},
            "adetailer": {"installed": False, "enabled": False, "name": ""},
            "controlnet": {"installed": False, "enabled": False, "name": ""},
        }

        # スクリプト一覧から確認（alwayson_scriptsで使えるか）
        scripts = ForgeService.get_scripts(base_url)
        txt2img_scripts = [s.lower() for s in scripts.get("txt2img", [])]

        # Regional Prompter確認
        for script in scripts.get("txt2img", []):
            script_lower = script.lower()
            if "regional" in script_lower and "prompt" in script_lower:
                result["regional_prompter"]["installed"] = True
                result["regional_prompter"]["enabled"] = True
                result["regional_prompter"]["name"] = script
                break

        # ADetailer確認
        for script in scripts.get("txt2img", []):
            script_lower = script.lower()
            if "adetailer" in script_lower or "after detailer" in script_lower:
                result["adetailer"]["installed"] = True
                result["adetailer"]["enabled"] = True
                result["adetailer"]["name"] = script
                break

        # ControlNet確認（IP-Adapter用）
        for script in scripts.get("txt2img", []):
            script_lower = script.lower()
            if "controlnet" in script_lower:
                result["controlnet"]["installed"] = True
                result["controlnet"]["enabled"] = True
                result["controlnet"]["name"] = script
                break

        # 拡張機能一覧からも確認（インストール状況）
        extensions = ForgeService.get_extensions(base_url)
        for ext in extensions:
            name = ext.get("name", "").lower()
            enabled = ext.get("enabled", False)

            if "regional" in name and "prompt" in name:
                result["regional_prompter"]["installed"] = True
                if enabled:
                    result["regional_prompter"]["enabled"] = True

            if "adetailer" in name:
                result["adetailer"]["installed"] = True
                if enabled:
                    result["adetailer"]["enabled"] = True

            if "controlnet" in name:
                result["controlnet"]["installed"] = True
                if enabled:
                    result["controlnet"]["enabled"] = True

        return result

    @staticmethod
    def get_adetailer_models(base_url: str) -> List[str]:
        """ADetailerで利用可能なモデル一覧取得"""
        # ADetailerはスクリプトとして動作するため、直接APIはない
        # 一般的なモデル名を返す
        return [
            "face_yolov8n.pt",
            "face_yolov8s.pt",
            "hand_yolov8n.pt",
            "person_yolov8n-seg.pt",
            "person_yolov8s-seg.pt",
            "mediapipe_face_full",
            "mediapipe_face_short",
        ]
