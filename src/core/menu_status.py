"""Estado do ícone da barra e linha de status do menu. Sem AppKit."""

ESTADOS_ICONE = ("parado", "gravando", "transcrevendo", "erro")
# None = imagem template: o macOS pinta o ícone na cor da barra (claro/escuro).
COR_DO_ICONE = {
    "parado": None,
    "gravando": "#FF4D6D",
    "transcrevendo": "#F5B942",
    "erro": None,
}


def linha_de_status(rotulo_tecla: str, erro: str | None) -> tuple[str, str]:
    if erro:
        return "Último erro: " + erro[:80], "#FF6B81"
    return "● Pronto · segure " + rotulo_tecla, "#36D1FF"
