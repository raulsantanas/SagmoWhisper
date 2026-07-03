from src.linux.session_check import check_session


def _tem_xclip(name):
    return "/usr/bin/xclip" if name == "xclip" else None


def _sem_clipboard(name):
    return None


def test_wayland_e_recusado_com_instrucao_do_xorg():
    msg = check_session(
        env={"XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"},
        which=_tem_xclip,
    )
    assert msg is not None
    assert "Ubuntu on Xorg" in msg


def test_sem_display_grafico_e_recusado():
    msg = check_session(env={}, which=_tem_xclip)
    assert msg is not None
    assert "sessão gráfica" in msg


def test_sem_xclip_e_recusado_com_comando_de_instalacao():
    msg = check_session(env={"DISPLAY": ":0"}, which=_sem_clipboard)
    assert msg is not None
    assert "xclip" in msg


def test_xsel_tambem_serve_como_clipboard():
    def which(name):
        return "/usr/bin/xsel" if name == "xsel" else None

    assert check_session(env={"DISPLAY": ":0"}, which=which) is None


def test_sessao_xorg_completa_passa():
    env = {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}
    assert check_session(env=env, which=_tem_xclip) is None
