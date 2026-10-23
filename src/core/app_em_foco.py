"""App na frente como bundle id: sinal para o classificador (ROADMAP 2.1).

Bundle id e não nome: o nome vem traduzido ("Mensagens") e o id não muda
com o idioma (DEC-PV-011). No Linux devolve None; o classificador decide só
pelo texto."""
import sys


def app_em_foco(platform: str = sys.platform, workspace=None) -> str | None:
    if platform != "darwin":
        return None
    app = (workspace or _workspace_do_macos()).frontmostApplication()
    bundle_id = app.bundleIdentifier() if app is not None else None
    return str(bundle_id) if bundle_id else None


def _workspace_do_macos():
    # Import tardio: o AppKit não existe no Linux.
    from AppKit import NSWorkspace

    return NSWorkspace.sharedWorkspace()
