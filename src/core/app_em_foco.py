"""Nome do app na frente: sinal para o classificador (ROADMAP 2.1).

No Linux devolve None; o classificador decide só pelo texto."""
import sys


def app_em_foco(platform: str = sys.platform, workspace=None) -> str | None:
    if platform != "darwin":
        return None
    app = (workspace or _workspace_do_macos()).frontmostApplication()
    return str(app.localizedName()) if app is not None else None


def _workspace_do_macos():
    # Import tardio: o AppKit não existe no Linux.
    from AppKit import NSWorkspace

    return NSWorkspace.sharedWorkspace()
