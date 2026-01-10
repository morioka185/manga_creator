# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

# プロジェクトのルートディレクトリ
ROOT_DIR = Path(SPECPATH)

# アイコンファイルのパス（存在する場合のみ使用）
if sys.platform == 'win32':
    icon_file = ROOT_DIR / 'assets' / 'icon.ico'
elif sys.platform == 'darwin':
    icon_file = ROOT_DIR / 'assets' / 'icon.icns'
else:
    icon_file = ROOT_DIR / 'assets' / 'icon.png'

icon_path = str(icon_file) if icon_file and icon_file.exists() else None

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=[
        # 必要なデータファイルがあればここに追加
        # ('assets', 'assets'),
    ],
    hiddenimports=[
        # PyQt6
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # reportlab
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.pdfgen',
        'reportlab.pdfgen.canvas',
        # Pillow
        'PIL',
        'PIL.Image',
        # アプリケーションモジュール
        'src',
        'src.views.main_window',
        'src.views.canvas_scene',
        'src.views.canvas_view',
        'src.views.page_list_widget',
        'src.views.panels.tool_panel',
        'src.views.panels.property_panel',
        'src.views.dialogs.settings_dialog',
        'src.graphics.panel_item',
        'src.graphics.speech_bubble_item',
        'src.graphics.text_item',
        'src.graphics.divider_line_item',
        'src.graphics.bubble_shapes',
        'src.models.project',
        'src.models.page',
        'src.models.panel',
        'src.models.panel_image_data',
        'src.models.divider_line',
        'src.models.speech_bubble',
        'src.models.text_element',
        'src.services.panel_calculator',
        'src.services.export_service',
        'src.services.template_service',
        'src.services.project_serializer',
        'src.services.settings_service',
        'src.commands.undo_commands',
        'src.utils.constants',
        'src.utils.enums',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MangaCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUIアプリなのでコンソールは非表示
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

# Mac用の.appバンドル設定
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='MangaCreator.app',
        icon=icon_path,
        bundle_identifier='com.mangacreator.app',
        info_plist={
            'CFBundleName': 'MangaCreator',
            'CFBundleDisplayName': 'Manga Creator',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
