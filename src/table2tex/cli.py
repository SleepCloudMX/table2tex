"""
Convert tables (Markdown, CSV, Excel, TeX) to LaTeX with best-value highlighting.

Usage:
    table2tex data.md -o out.tex
    table2tex input_dir/ -o output_dir/
    table2tex data.md                     # print to stdout
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from table2tex.parser import parse_table
from table2tex.formatter import format_table

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
    parser.add_argument('--descend', type=int, nargs='*', default=None, metavar='COL',
                        help='1-based column indices where smaller is better')
    parser.add_argument('--column-bg', type=str, nargs='*', default=None,
                        metavar='COL:COLOR',
                        help='Column background colors, e.g. "3:blue!5" (1-based)')
    parser.add_argument('--no-document', action='store_true',
                        help='Output only the tabular body, no document wrapper')
    parser.add_argument('--sheet', type=str, default=None,
                        help='Excel sheet name (default: active sheet)')

    args = parser.parse_args()

    # Validate output
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
    # Validate
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

    # Resolve name conflicts: if two files share a stem, use stem.ext.tex
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

    # Convert each file
    results: list[tuple[str, str, str]] = []  # (label, env_type, output_tex)
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

        label = Path(name).stem  # strip .tex
        results.append((label, env_type, output_tex))

    # Write summary
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

    if args.descend is not None:
        for col_1b in args.descend:
            ci = col_1b - 1
            if ci < 0 or ci >= len(table.columns):
                print(f"Warning: column {col_1b} exceeds table width "
                      f"({len(table.columns)}) in {input_path.name}",
                      file=sys.stderr)
                continue
            table.columns[ci].descend = True

    bg_colors: dict[int, str] = {}
    if args.column_bg is not None:
        for spec in args.column_bg:
            col_str, color = spec.split(':', 1)
            ci = int(col_str) - 1
            if ci < 0 or ci >= len(table.columns):
                print(f"Warning: column {col_str} exceeds table width "
                      f"({len(table.columns)}) in {input_path.name}",
                      file=sys.stderr)
                continue
            bg_colors[ci] = color

    output_tex = format_table(table, bg_colors=bg_colors, no_document=args.no_document)
    env_type = 'array' if r'\begin{array}' in output_tex else 'tabular'
    return output_tex, env_type


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def _build_summary(results: list[tuple[str, str, str]]) -> str:
    """Build summary.md from conversion results."""
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
    """Extract just the table environment from full LaTeX output."""
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
