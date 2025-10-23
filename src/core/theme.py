from collections import namedtuple

ColorPalette = namedtuple(
    "ColorPalette",
    [
        "primary",
        "primary_variant",
        "secondary",
        "background",
        "surface",
        "surface_variant",
        "text_primary",
        "text_secondary",
        "success",
        "warning",
        "error",
        "border",
    ],
)

def get_light_theme() -> ColorPalette:
    return ColorPalette(
        primary="#60263C",
        primary_variant="#4A1E2F",
        secondary="#C8A7A6",
        background="#F7F7F7",
        surface="#FFFFFF",
        surface_variant="#EAEAEA",
        text_primary="#1C1C1E",
        text_secondary="#606266",
        success="#28A745",
        warning="#FD7E14",
        error="#DC3545",
        border="#DCDFE6",
    )

def apply_theme_to_stylesheet(qss_template: str, theme: ColorPalette) -> str:
    styled_qss = qss_template
    for color_name, color_value in theme._asdict().items():
        placeholder = f"@{color_name}"
        styled_qss = styled_qss.replace(placeholder, color_value)
    return styled_qss