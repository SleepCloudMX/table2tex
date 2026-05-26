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


def strip_tex_formatting(cell: str) -> str:
    """Remove \\textbf, \\color{red}, \\text, \\textit etc. to extract the core value."""
    s = cell.strip()
    # Remove \color{red}{...}
    s = re.sub(r'\\color\{[^}]*\}\{', '', s)
    # Remove \textbf{...}
    s = re.sub(r'\\textbf\{', '', s)
    # Remove \textit{...}
    s = re.sub(r'\\textit\{', '', s)
    # Remove \text{...}
    s = re.sub(r'\\text\{', '', s)
    # Remove \mathbf{...}
    s = re.sub(r'\\mathbf\{', '', s)
    # Remove closing braces that were opened by the above
    # Count how many we removed and remove that many closing braces at the end
    # Simpler: just remove all orphan } at the end
    s = s.rstrip('}')
    return s.strip()


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
