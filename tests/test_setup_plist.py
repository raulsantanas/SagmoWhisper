"""O ícone usa SF Symbols com paleta de cores (macOS 12+). Sem declarar o
mínimo, o app abriria num macOS antigo e quebraria na primeira gravação."""
import ast
from pathlib import Path


def _plist():
    arvore = ast.parse(Path("setup.py").read_text())
    for no in arvore.body:
        if isinstance(no, ast.Assign) and no.targets[0].id == "_PLIST":
            return {k.value: v for k, v in zip(no.value.keys, no.value.values)}
    raise AssertionError("_PLIST não encontrado em setup.py")


def test_plist_exige_macos_12():
    assert ast.literal_eval(_plist()["LSMinimumSystemVersion"]) == "12.0"
