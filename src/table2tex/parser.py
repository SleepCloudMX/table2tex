import re
from pathlib import Path

from table2tex.model import TableData, ColumnMeta
from table2tex.utils import parse_cell_value, strip_tex_formatting, split_tex_cells


def parse_table(filepath: str, sheet_name: str | None = None) -> TableData:
    """Dispatch to the appropriate parser based on file extension."""
    ext = Path(filepath).suffix.lower()
    if ext == '.md':
        return _parse_markdown(filepath)
    elif ext in ('.csv', '.xls', '.xlsx'):
        return _parse_tabular(filepath, sheet_name=sheet_name)
    elif ext == '.tex':
        return _parse_tex(filepath)
    else:
        raise ValueError(f"Unsupported format: {ext}")


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def _parse_markdown(filepath: str) -> TableData:
    text = Path(filepath).read_text(encoding='utf-8')
    lines = text.splitlines()

    # Locate separator row (|---|...|)
    sep_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^\s*\|?\s*[-:]{3,}\s*(\|\s*[-:]{3,}\s*)*\|?\s*$', line):
            sep_idx = i
            break

    if sep_idx is None:
        raise ValueError("No markdown table separator row found (expected |---|...|)")

    header_lines = lines[:sep_idx]
    data_lines = lines[sep_idx + 1:]

    def _split_md_row(row: str) -> list[str]:
        # Strip leading/trailing | then split
        r = row.strip()
        if r.startswith('|'):
            r = r[1:]
        if r.endswith('|'):
            r = r[:-1]
        return [c.strip() for c in r.split('|')]

    headers = [_split_md_row(hl) for hl in header_lines if hl.strip()]
    data = [_split_md_row(dl) for dl in data_lines if dl.strip()]

    # Normalise column count
    max_cols = max((len(h) for h in headers), default=0)
    max_cols = max(max_cols, max((len(d) for d in data), default=0))
    headers = [_pad_row(h, max_cols) for h in headers]
    data = [_pad_row(d, max_cols) for d in data]

    columns = _build_column_meta(data, max_cols)
    return TableData(headers=headers, data=data, columns=columns, source='md')


# ---------------------------------------------------------------------------
# CSV / Excel (via pandas)
# ---------------------------------------------------------------------------

def _parse_tabular(filepath: str, sheet_name: str | None = None) -> TableData:
    import pandas as pd

    ext = Path(filepath).suffix.lower()
    if ext == '.csv':
        df = pd.read_csv(filepath, dtype=str, keep_default_na=False, na_values=[])
    else:
        df = pd.read_excel(filepath, sheet_name=sheet_name or 0, dtype=str)

    if df.empty:
        raise ValueError("Table file is empty")

    headers = [[str(c) for c in df.columns]]
    data = [
        ['' if pd.isna(v) else str(v) for v in row]
        for row in df.values.tolist()
    ]

    max_cols = max((len(h) for h in headers), default=0)
    max_cols = max(max_cols, max((len(d) for d in data), default=0))
    headers = [_pad_row(h, max_cols) for h in headers]
    data = [_pad_row(d, max_cols) for d in data]

    columns = _build_column_meta(data, max_cols)
    return TableData(headers=headers, data=data, columns=columns, source=ext.lstrip('.'))


# ---------------------------------------------------------------------------
# TeX
# ---------------------------------------------------------------------------

_TABLE_ENV_RE = re.compile(
    r'\\begin\{(array|tabular)\}(?:\[[^\]]*\])?\{([^}]*)\}(.*?)\\end\{\1\}',
    re.DOTALL,
)

# Matches \hline, \toprule, \midrule, \bottomrule, \cmidrule(lr){1-2} etc.
_RULE_RE = re.compile(
    r'\s*\\(?:hline|toprule|midrule|bottomrule'
    r'|cmidrule(?:\([^)]*\))?(?:\{[^}]*\})?'
    r')\s*'
)


def _parse_tex(filepath: str) -> TableData:
    text = Path(filepath).read_text(encoding='utf-8')

    m = _TABLE_ENV_RE.search(text)
    if not m:
        raise ValueError("No tabular or array environment found in TeX file")

    env_type = m.group(1)
    col_spec = m.group(2)
    body = m.group(3)
    body_start = m.start(3)

    # Split body by \\ to get raw row fragments (may contain \hline)
    raw_fragments = _split_tex_body(body)

    # Clean each fragment: remove \hline, track positions
    cell_rows: list[list[str]] = []
    tex_row_strs: list[str] = []
    hlines: set[int] = set()

    for frag in raw_fragments:
        # Check if this fragment starts with \hline
        has_hline = bool(_RULE_RE.match(frag))
        cleaned = _RULE_RE.sub('', frag).strip()
        if not cleaned:
            # It was only an \hline, record it for the row before which it appears
            hlines.add(len(cell_rows))
            continue

        cells = split_tex_cells(cleaned)
        if cells:
            if has_hline:
                hlines.add(len(cell_rows))
            cell_rows.append(cells)
            tex_row_strs.append(cleaned)

    if not cell_rows:
        raise ValueError("No data rows found in TeX table body")

    # Header detection: first row is header unless all its cells are numeric
    first_stripped = [strip_tex_formatting(c) for c in cell_rows[0]]
    first_all_numeric = all(
        parse_cell_value(c)[0] or not c.strip() for c in first_stripped
    )
    if first_all_numeric:
        headers: list[list[str]] = []
        tex_headers: list[list[str]] = []
        data_start = 0
    else:
        headers = [first_stripped]
        tex_headers = [cell_rows[0]]
        data_start = 1

    data = []
    tex_rows = []
    for row in cell_rows[data_start:]:
        stripped = [strip_tex_formatting(c) for c in row]
        data.append(stripped)
        tex_rows.append(row)

    max_cols = max((len(h) for h in headers), default=0)
    max_cols = max(max_cols, max((len(d) for d in data), default=0))
    headers = [_pad_row(h, max_cols) for h in headers]
    data = [_pad_row(d, max_cols) for d in data]
    tex_headers = [_pad_row(h, max_cols) for h in tex_headers]
    tex_rows = [_pad_row(r, max_cols) for r in tex_rows]

    columns = _build_column_meta(data, max_cols)

    # Adjust hlines for header offset: hlines track positions in tex_rows (which includes headers)
    # Already correct since hlines was computed against cell_rows

    # Check for trailing rule command after last row
    trailing_hline = bool(re.search(r'\\(?:hline|toprule|midrule|bottomrule)\s*$', body))

    return TableData(
        headers=headers,
        data=data,
        columns=columns,
        source='tex',
        tex_source=text,
        tex_body_start=body_start,
        tex_body_end=m.end(3),
        tex_rows=tex_headers + tex_rows,
        tex_hlines=hlines,
        tex_env_type=env_type,
        tex_col_spec=col_spec,
        tex_trailing_hline=trailing_hline,
    )


def _split_tex_body(body: str) -> list[str]:
    """Split TeX table body into row fragments by \\ .
    Each fragment is the text between two \\ markers."""
    parts = re.split(r'\\\\(?:\*|\[[^\]]*\])?', body)
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _pad_row(row: list[str], n: int) -> list[str]:
    while len(row) < n:
        row.append('')
    return row


def _build_column_meta(data: list[list[str]], num_cols: int) -> list[ColumnMeta]:
    columns = []
    for ci in range(num_cols):
        numeric_count = 0
        for row in data:
            cell = row[ci] if ci < len(row) else ''
            is_num, _, _ = parse_cell_value(cell)
            if is_num:
                numeric_count += 1
        # Process column if it has at least 2 numeric values
        columns.append(ColumnMeta(index=ci, is_numeric=numeric_count >= 2))
    return columns
