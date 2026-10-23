"""Hook Stop do Claude Code: fala a linha `VOZ:` da resposta (ROADMAP 3.1).

Configurado em ~/.claude/settings.json. Silencioso e sempre sai com 0."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from src.core.hook_stop import main

    status = main(sys.stdin.read(), os.environ)
except Exception:
    status = 0
sys.exit(status)
