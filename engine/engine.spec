# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Paths relative to this spec file (engine/)
spec_dir = Path(SPECPATH)
project_root = spec_dir.parent

a = Analysis(
    [str(spec_dir / 'cli.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(spec_dir / 'profiles' / '*.yaml'), 'engine/profiles'),
    ],
    hiddenimports=[
        'engine.llm.client',
        'engine.llm.settings',
        'engine.llm.prompts',
        'engine.llm.schemas',
        'engine.formatter.docx_formatter',
        'engine.diagnostics.diagnose',
        'engine.fixer.apply_fixes',
        'engine.converters.pandoc',
        'engine.pipeline',
        'engine.profiles.loader',
        'engine.models',
        'engine.style_utils',
        'docx',
        'yaml',
        'openai',
        'pydantic',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='docforge-engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
)
