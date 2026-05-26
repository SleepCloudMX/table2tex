import re
from typing import Tuple, Optional


_NUMBER_RE = re.compile(r'^-?[\d,]+(?:\.\d+)?(?:[eE][+-]?\d+)?%?$')


def parse_cell_value(text: str) -> Tuple[bool, Optional[float], bool]:
    """
    Analyse a cell's raw text.
    Returns (is_numeric, float_value_or_None, has_percent).
    """
    t = text.strip()
    if not t:
        return False, None, False

    has_percent = t.endswith('%')
    working = t[:-1] if has_percent else t

    if not _NUMBER_RE.match(working):
        return False, None, False

    cleaned = working.replace(',', '')
    try:
        val = float(cleaned)
        return True, val, has_percent
    except ValueError:
        return False, None, False


_FMT_CMD_RE = re.compile(
    r'\\(?:textbf|textit|text|mathbf|boldsymbol|emph|color\{[^}]*\})\s*\{'
)

_TEX_UNESCAPE_MAP = {
    r'\%': '%', r'\$': '$', r'\&': '&', r'\_': '_',
    r'\#': '#', r'\{': '{', r'\}': '}', r'\textasciitilde{}': '~',
}


def strip_tex_formatting(cell: str) -> str:
    """Strip TeX formatting commands (\\textbf, \\color{red}, bare braces etc.)
    to extract the core value. Handles nested wrappers like {\\textbf{79.31}}."""
    s = cell.strip()
    prev = None
    while s != prev:
        prev = s
        m = _FMT_CMD_RE.match(s)
        if m:
            inner = s[m.end():]
            close = _find_matching_brace(inner)
            if close >= 0:
                s = inner[:close]
                continue
        # Bare {...} wrapper
        if s.startswith('{') and s.endswith('}'):
            if _find_matching_brace(s[1:]) == len(s) - 2:
                s = s[1:-1]
                continue
        break
    # Unescape TeX escapes so that parse_cell_value works on e.g. 96.88\%
    for escape, char in _TEX_UNESCAPE_MAP.items():
        s = s.replace(escape, char)
    return s.strip()


def _find_matching_brace(text: str) -> int:
    """Return the index of the '}' that matches the opening brace at position 0.
    Returns -1 if not found."""
    depth = 1
    for i, ch in enumerate(text):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1


def split_tex_cells(row: str) -> list[str]:
    """Split a TeX table row by &, respecting brace depth."""
    cells = []
    depth = 0
    current: list[str] = []
    for ch in row:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        elif ch == '&' and depth == 0:
            cells.append(''.join(current).strip())
            current = []
            continue
        current.append(ch)
    cells.append(''.join(current).strip())
    return cells
