"""
Convert tables (Markdown, CSV, Excel, TeX) to LaTeX with best-value highlighting.

Usage:
    table2tex data.md -o out.tex
    table2tex input_dir/ -o output_dir/
    table2tex data.md --exclude-cols Model --descend F1
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from table2tex.parser import parse_table, exclude_rows, exclude_cols, expand_multirow_spans
from table2tex.formatter import format_table
from table2tex.utils import strip_tex_formatting

_SUPPORTED = {'.md', '.csv', '.xls', '.xlsx', '.tex'}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Convert tables to LaTeX with best-value highlighting.'
    )
    parser.add_argument('input', type=str,
                        help='Input file or directory (.md, .csv, .xlsx, .xls, .tex)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output .tex file or directory (default: print to stdout)')
    parser.add_argument('--descend', type=str, nargs='*', default=None, metavar='SPEC',
                        help='Columns where smaller is better (index, name, or =name)')
    parser.add_argument('--column-bg', type=str, nargs='*', default=None,
                        metavar='SPEC:COLOR',
                        help='Column background, e.g. "3:blue!5" or "F1:yellow!12"')
    parser.add_argument('--exclude-rows', type=str, nargs='*', default=None, metavar='SPEC',
                        help='Rows to exclude (index or first-column value)')
    parser.add_argument('--exclude-cols', type=str, nargs='*', default=None, metavar='SPEC',
                        help='Columns to exclude (index or header name)')
    parser.add_argument('--no-document', action='store_true',
                        help='Output only the tabular body, no document wrapper')
    parser.add_argument('--sheet', type=str, default=None,
                        help='Excel sheet name (default: active sheet)')

    args = parser.parse_args()

    out_path = Path(args.output) if args.output else None
    if out_path and out_path.exists() and out_path.is_dir() and out_path.suffix:
        print("Error: output must be a directory when input is a directory",
              file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if input_path.is_dir():
        _process_directory(input_path, out_path, args)
    else:
        _process_single(input_path, out_path, args)


# ---------------------------------------------------------------------------
# single file
# ---------------------------------------------------------------------------

def _process_single(input_path: Path, out_path: Path | None, args):
    output_tex, _ = _convert_one(input_path, args)

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_tex, encoding='utf-8')
        print(f"Written to {out_path}")
    else:
        print(output_tex)


# ---------------------------------------------------------------------------
# directory
# ---------------------------------------------------------------------------

def _process_directory(input_dir: Path, out_dir: Path | None, args):
    if out_dir and out_dir.suffix:
        print("Error: output must be a directory when input is a directory",
              file=sys.stderr)
        sys.exit(1)

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        f for f in input_dir.iterdir()
        if f.suffix.lower() in _SUPPORTED and f.is_file()
    )
    if not files:
        print(f"No supported files found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    stem_to_files: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        stem_to_files[f.stem].append(f)

    output_names: dict[Path, str] = {}
    for stem, file_list in stem_to_files.items():
        if len(file_list) == 1:
            output_names[file_list[0]] = f'{stem}.tex'
        else:
            for f in file_list:
                ext_label = f.suffix.lstrip('.')
                output_names[f] = f'{stem}.{ext_label}.tex'

    results: list[tuple[str, str, str]] = []
    for f in files:
        name = output_names[f]
        print(f"Processing {f.name} ...", file=sys.stderr)
        try:
            output_tex, env_type = _convert_one(f, args)
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            continue

        if out_dir:
            (out_dir / name).write_text(output_tex, encoding='utf-8')
            print(f"  -> {name}", file=sys.stderr)
        else:
            print(f"\n{'=' * 60}")
            print(f"  {name}")
            print('=' * 60)
            print(output_tex)

        label = Path(name).stem
        results.append((label, env_type, output_tex))

    if out_dir and results:
        summary = _build_summary(results)
        (out_dir / 'summary.md').write_text(summary, encoding='utf-8')
        print(f"\nSummary written to {out_dir / 'summary.md'}")


# ---------------------------------------------------------------------------
# conversion helper
# ---------------------------------------------------------------------------

def _convert_one(input_path: Path, args) -> tuple[str, str]:
    """Convert a single file. Returns (output_tex, env_type)."""
    table = parse_table(str(input_path), sheet_name=args.sheet)

    # --- resolve column specs (before exclusion, against original table) ---
    headers0 = table.headers[0] if table.headers else []
    num_cols = max(
        len(headers0),
        max((len(r) for r in table.data), default=0),
    )

    descend_indices: set[int] = set()
    if args.descend is not None:
        for spec in args.descend:
            idx = _resolve_col_spec(spec, headers0, num_cols)
            if idx is not None:
                descend_indices.add(idx)
            else:
                print(f"Warning: --descend '{spec}' not resolved in {input_path.name}",
                      file=sys.stderr)

    bg_specs: dict[int, str] = {}  # old_col_idx → color
    if args.column_bg is not None:
        for spec in args.column_bg:
            col_spec, color = _split_bg_spec(spec)
            if col_spec is None:
                print(f"Warning: --column-bg '{spec}' invalid format in "
                      f"{input_path.name}", file=sys.stderr)
                continue
            idx = _resolve_col_spec(col_spec, headers0, num_cols)
            if idx is not None:
                bg_specs[idx] = color
            else:
                print(f"Warning: --column-bg '{col_spec}' not resolved in "
                      f"{input_path.name}", file=sys.stderr)

    # --- resolve row exclusion ---
    excluded_rows: set[int] = set()
    if args.exclude_rows is not None:
        for spec in args.exclude_rows:
            indices = _resolve_row_spec(spec, table)
            if indices:
                excluded_rows.update(indices)
            else:
                print(f"Warning: --exclude-rows '{spec}' not resolved in "
                      f"{input_path.name}", file=sys.stderr)
        # Expand multirow spans in TeX
        excluded_rows = expand_multirow_spans(table, excluded_rows)

    # --- resolve column exclusion ---
    excluded_cols: set[int] = set()
    if args.exclude_cols is not None:
        for spec in args.exclude_cols:
            indices = _resolve_col_specs(spec, headers0, num_cols, table.data)
            if indices:
                excluded_cols.update(indices)
            else:
                print(f"Warning: --exclude-cols '{spec}' not resolved in "
                      f"{input_path.name}", file=sys.stderr)

    # --- apply exclusions ---
    exclude_rows(table, excluded_rows)
    col_map = exclude_cols(table, excluded_cols)

    # --- remap descend / bg to new column indices ---
    for old_idx in descend_indices:
        if old_idx in col_map:
            table.columns[col_map[old_idx]].descend = True
    bg_colors: dict[int, str] = {}
    for old_idx, color in bg_specs.items():
        if old_idx in col_map:
            bg_colors[col_map[old_idx]] = color

    # --- format ---
    output_tex = format_table(table, bg_colors=bg_colors, no_document=args.no_document)
    env_type = 'array' if r'\begin{array}' in output_tex else 'tabular'
    return output_tex, env_type


# ---------------------------------------------------------------------------
# spec resolution  (index | name | =name  →  0-based index)
# ---------------------------------------------------------------------------

def _resolve_col_spec(
    spec: str, headers: list[str], num_cols: int,
) -> int | None:
    """Resolve a single column spec to a 0-based index."""
    spec = spec.strip()
    if not spec:
        return None

    # =name  → force name match
    if spec.startswith('='):
        return _find_col_by_name(spec[1:], headers)

    # integer → 1-based index
    try:
        idx = int(spec) - 1
        if 0 <= idx < num_cols:
            return idx
        return None  # out of range
    except ValueError:
        pass

    # name match
    return _find_col_by_name(spec, headers)


def _find_col_by_name(name: str, headers: list[str]) -> int | None:
    for ci, h in enumerate(headers):
        if strip_tex_formatting(h) == name:
            return ci
    return None


def _resolve_row_spec(spec: str, table) -> list[int]:
    """Resolve a row spec to a list of 0-based data-row indices."""
    spec = spec.strip()
    if not spec:
        return []

    # =name
    if spec.startswith('='):
        return _find_rows_by_name(spec[1:], table.data)

    # integer
    try:
        idx = int(spec) - 1
        if 0 <= idx < len(table.data):
            return [idx]
        return []
    except ValueError:
        pass

    # name match
    return _find_rows_by_name(spec, table.data)


_MULTIROW_CONTENT_RE = re.compile(
    r'\\multirow\{[^}]*\}\{[^}]*\}\{(.+)\}\s*$'
)


def _find_rows_by_name(name: str, data: list[list[str]]) -> list[int]:
    indices: list[int] = []
    for ri, row in enumerate(data):
        if not row:
            continue
        cell = strip_tex_formatting(row[0])
        # \multirow{n}{align}{content} → extract content
        m = _MULTIROW_CONTENT_RE.match(cell)
        if m:
            cell = strip_tex_formatting(m.group(1))
        if cell == name:
            indices.append(ri)
    return indices


def _resolve_col_specs(
    spec: str, headers: list[str], num_cols: int, data: list[list[str]],
) -> list[int]:
    """Resolve a column-exclusion spec, may match multiple columns by name."""
    spec = spec.strip()
    if not spec:
        return []

    if spec.startswith('='):
        name = spec[1:]
        return _find_cols_by_name(name, headers)

    try:
        idx = int(spec) - 1
        if 0 <= idx < num_cols:
            return [idx]
        return []
    except ValueError:
        pass

    # name match — may return multiple matching columns
    return _find_cols_by_name(spec, headers)


def _find_cols_by_name(name: str, headers: list[str]) -> list[int]:
    indices: list[int] = []
    for ci, h in enumerate(headers):
        if strip_tex_formatting(h) == name:
            indices.append(ci)
    return indices


def _split_bg_spec(raw: str) -> tuple[str | None, str]:
    """Split 'COL:COLOR' on the last colon. Returns (col_spec, color)."""
    parts = raw.rsplit(':', 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, ''


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def _build_summary(results: list[tuple[str, str, str]]) -> str:
    lines: list[str] = ['# Summary', '']
    for stem, env_type, output_tex in results:
        body = _extract_table_body(output_tex, env_type)
        lines.append(f'#### {stem}')
        lines.append('')
        if env_type == 'array':
            lines.append('$$')
            lines.append(body)
            lines.append('$$')
        else:
            lines.append('```latex')
            lines.append(body)
            lines.append('```')
        lines.append('')
    return '\n'.join(lines) + '\n'


def _extract_table_body(output: str, env_type: str) -> str:
    begin = f'\\begin{{{env_type}}}'
    end = f'\\end{{{env_type}}}'
    start = output.find(begin)
    if start == -1:
        return output.strip()
    stop = output.rfind(end)
    if stop == -1:
        return output[start:].strip()
    return output[start:stop + len(end)].strip()


if __name__ == '__main__':
    main()
