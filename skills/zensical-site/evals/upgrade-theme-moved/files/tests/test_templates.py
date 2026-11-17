"""La cabecera propia no debe quedarse atrás respecto a la del tema."""

from importlib.resources import files
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def theme_templates() -> Path:
    """Carpeta de plantillas del tema instalado."""
    return Path(str(files("zensical") / "templates"))


def test_header_override_tracks_theme() -> None:
    upstream = (theme_templates() / "partials" / "header.html").read_text(encoding="utf-8")
    ours = (ROOT / "docs_templates" / "partials" / "header.html").read_text(encoding="utf-8")
    missing = [line for line in upstream.splitlines() if line.strip() and line not in ours]
    assert not missing, f"La cabecera propia no incluye estas líneas del tema: {missing}"
