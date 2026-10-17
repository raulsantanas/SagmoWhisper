"""Ícone de onda da barra de menu, colorido conforme o estado do ditado."""
from AppKit import (
    NSColor,
    NSCompositingOperationSourceOver,
    NSFontWeightRegular,
    NSImage,
    NSImageSymbolConfiguration,
    NSMakeRect,
    NSMakeSize,
    NSZeroRect,
)

from src.core.menu_status import COR_DO_ICONE
from src.macos.cores import hex_to_nscolor

_PONTOS = 16.0
_TAMANHO = 18.0
_ALERTA_LADO = 9.0


def _simbolo(nome: str, pontos: float, cor: NSColor | None):
    config = NSImageSymbolConfiguration.configurationWithPointSize_weight_(
        pontos, NSFontWeightRegular
    )
    if cor is not None:
        config = config.configurationByApplyingConfiguration_(
            NSImageSymbolConfiguration.configurationWithPaletteColors_([cor])
        )
    imagem = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
        nome, "SagmoWhisper"
    )
    return imagem.imageWithSymbolConfiguration_(config)


def _com_alerta(onda):
    alerta = _simbolo(
        "exclamationmark.triangle.fill", _ALERTA_LADO, hex_to_nscolor("#F5B942")
    )

    def desenhar(rect):
        _desenhar(onda, NSMakeRect(0, 2, _TAMANHO - 4, _TAMANHO - 4))
        lado = _ALERTA_LADO + 1
        _desenhar(alerta, NSMakeRect(_TAMANHO - lado, 0, lado, lado))
        return True

    return NSImage.imageWithSize_flipped_drawingHandler_(
        NSMakeSize(_TAMANHO, _TAMANHO), False, desenhar
    )


def _desenhar(imagem, destino):
    imagem.drawInRect_fromRect_operation_fraction_(
        destino, NSZeroRect, NSCompositingOperationSourceOver, 1.0
    )


def imagem_do_icone(estado: str) -> NSImage:
    cor = COR_DO_ICONE[estado]
    if estado == "erro":
        # Desenho próprio não pode ser template; labelColor acompanha a barra.
        return _com_alerta(_simbolo("waveform", _PONTOS, NSColor.labelColor()))
    pintura = None if cor is None else hex_to_nscolor(cor)
    imagem = _simbolo("waveform", _PONTOS, pintura)
    imagem.setTemplate_(cor is None)
    return imagem
