"""Complete PKD 2025 subclass catalogue with official titles.

Source and version details: PKD_SOURCES.md.
"""

import json
from pathlib import Path

PKD_SOURCE_URL = "https://eli.gov.pl/eli/DU/2024/1936/ogl"

PKD_OPTIONS: dict[str, str] = json.loads(
    (Path(__file__).parent / "data" / "pkd_2025.json").read_text(encoding="utf-8")
)

# Keep the previous defaults; every industry is now available for selection.
DEFAULT_SELECTED_PKD = tuple(
    code for code in PKD_OPTIONS if code.startswith(("38.", "39.")) or code == "46.87.Z"
)


def pkd_label(code: str) -> str:
    return f"{code} — {PKD_OPTIONS[code]}"
