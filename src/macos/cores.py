from AppKit import NSColor


def hex_to_nscolor(hex_color: str, alpha: float = 1.0) -> NSColor:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return NSColor.colorWithRed_green_blue_alpha_(r, g, b, alpha)
