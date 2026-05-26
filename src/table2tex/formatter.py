from table2tex.model import TableData, ColumnMeta
from table2tex.utils import parse_cell_value


def format_table(
    table: TableData,
    bg_colors: dict[int, str] | None = None,
    no_document: bool = False,
) -> str:
    """
    Process a parsed table: rank columns, apply highlights, and produce LaTeX output.

    Parameters
    ----------
    bg_colors : dict[int, str] | None
        0-based column index → color string, e.g. {3: 'blue!12'}.
    no_document : bool
        If True, output only the tabular block (no \\documentclass wrapper).
    """
    # Apply bg colors to column metadata
    if bg_colors:
        for ci, color in bg_colors.items():
            if ci < len(table.columns):
                table.columns[ci].bg_color = color

    # Compute highlights
    highlights: dict[tuple[int, int], int] = {}  # (row, col) -> 1 (best) or 2 (second)
    _compute_highlights(table, highlights)

    if table.source == 'tex':
        return _format_tex(table, highlights)
    else:
        return _format_from_scratch(table, highlights, no_document)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def _compute_highlights(table: TableData, highlights: dict[tuple[int, int], int]) -> None:
    for col in table.columns:
        if not col.is_numeric:
            continue

        entries: list[tuple[int, float]] = []
        for ri, row in enumerate(table.data):
            cell = row[col.index] if col.index < len(row) else ''
            is_num, val, _ = parse_cell_value(cell)
            if is_num and val is not None:
                entries.append((ri, val))

        if len(entries) < 1:
            continue

        unique = sorted(set(v for _, v in entries), reverse=not col.descend)
        best_val = unique[0]
        second_val = unique[1] if len(unique) > 1 else None

        for ri, val in entries:
            if val == best_val:
                highlights[(ri, col.index)] = 1
            elif second_val is not None and val == second_val:
                highlights[(ri, col.index)] = 2


# ---------------------------------------------------------------------------
# TeX output (string substitution)
# ---------------------------------------------------------------------------

def _format_tex(table: TableData, highlights: dict[tuple[int, int], int]) -> str:
    tex_rows = table.tex_rows
    hlines = table.tex_hlines or set()
    if tex_rows is None:
        raise ValueError("tex_rows is missing from TableData")

    num_header_rows = len(table.headers)

    # Rebuild body rows, inserting \hline at tracked positions
    body_parts: list[str] = []
    for ri, row in enumerate(tex_rows):
        if ri in hlines:
            body_parts.append(r'\hline')

        cells_out: list[str] = []
        for ci, cell_tex in enumerate(row):
            h = None
            data_ri = ri - num_header_rows
            if data_ri >= 0:
                h = highlights.get((data_ri, ci))

            if h is not None:
                core = ''
                if data_ri < len(table.data) and ci < len(table.data[data_ri]):
                    core = table.data[data_ri][ci]
                formatted = _apply_highlight(core, h)
                cells_out.append(formatted)
            else:
                cells_out.append(cell_tex)

        body_parts.append(' & '.join(cells_out) + r' \\')

    if table.tex_trailing_hline:
        body_parts.append(r'\hline')

    new_body = '\n'.join(body_parts)

    assert table.tex_body_start is not None
    assert table.tex_body_end is not None
    result = (
        table.tex_source[:table.tex_body_start]
        + new_body
        + table.tex_source[table.tex_body_end:]
    )
    return result


# ---------------------------------------------------------------------------
# Fresh LaTeX generation (md / xlsx)
# ---------------------------------------------------------------------------

def _format_from_scratch(
    table: TableData,
    highlights: dict[tuple[int, int], int],
    no_document: bool,
) -> str:
    use_bg = any(c.bg_color for c in table.columns)
    lines: list[str] = []

    if not no_document:
        if use_bg:
            lines.append(r'\documentclass{beamer}')
            lines.append(r'\usepackage{booktabs, multirow, makecell}')
            lines.append(r'\usepackage{xcolor, colortbl}')
            lines.append(r'\begin{document}')
            lines.append(r'\begin{frame}')
            lines.append(r'\centering')
        else:
            lines.append(r'\documentclass{article}')
            lines.append(r'\usepackage{booktabs, multirow, makecell, xcolor}')
            lines.append(r'\begin{document}')

    # Build column specification
    col_spec = _build_col_spec(table)
    lines.append(r'\begin{tabular}{' + col_spec + '}')
    lines.append(r'\hline')

    # Headers
    for header_row in table.headers:
        cells = [_escape_tex(h) for h in header_row]
        lines.append(' & '.join(cells) + r' \\')
        lines.append(r'\hline')

    # Data rows
    for ri, row in enumerate(table.data):
        cells: list[str] = []
        for ci, cell_text in enumerate(row):
            h = highlights.get((ri, ci))
            if h is not None:
                cells.append(_apply_highlight(cell_text, h))
            else:
                cells.append(_escape_tex(cell_text))
        lines.append(' & '.join(cells) + r' \\')

    lines.append(r'\hline')
    lines.append(r'\end{tabular}')

    if not no_document:
        if use_bg:
            lines.append(r'\end{frame}')
        lines.append(r'\end{document}')

    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_highlight(core: str, level: int) -> str:
    """Wrap a core cell value with LaTeX highlight."""
    # Handle percent suffix
    has_pct = core.endswith('%')
    inner = core[:-1] if has_pct else core

    if level == 1:
        out = f'\\color{{red}}{{{inner}}}'
    else:
        out = f'\\textbf{{{inner}}}'

    if has_pct:
        out += r'\%'
    return out


def _escape_tex(text: str) -> str:
    """Escape special TeX characters in a plain text cell."""
    replacements = [
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\^{}'),
    ]
    for char, repl in replacements:
        text = text.replace(char, repl)
    return text


def _build_col_spec(table: TableData) -> str:
    parts: list[str] = []
    for col in table.columns:
        if col.bg_color:
            parts.append(f'>{{\\columncolor{{{col.bg_color}}}}}c')
        else:
            parts.append('c')
    return ' '.join(parts)
