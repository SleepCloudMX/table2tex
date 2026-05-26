"""
Convert tables (Markdown, Excel, TeX) to LaTeX with best-value highlighting.

Usage:
    python -m table2tex data.md -o output.tex
    python -m table2tex data.xlsx --descend 2 4 -o output.tex
    python -m table2tex data.tex --descend 1 --column-bg 3:blue!5 -o out.tex
"""

import argparse
import sys
from pathlib import Path

from table2tex.parser import parse_table
from table2tex.formatter import format_table


def main():
    parser = argparse.ArgumentParser(
        description='Convert tables to LaTeX with best-value highlighting.'
    )
    parser.add_argument('input', type=str, help='Input file (.md, .csv, .xlsx, .xls, .tex)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output .tex file (default: print to stdout)')
    parser.add_argument('--descend', type=int, nargs='*', default=None,
                        metavar='COL',
                        help='1-based column indices where smaller is better')
    parser.add_argument('--column-bg', type=str, nargs='*', default=None,
                        metavar='COL:COLOR',
                        help='Column background colors, e.g. "3:blue!5" (1-based)')
    parser.add_argument('--no-document', action='store_true',
                        help='Output only the tabular body, no document wrapper')
    parser.add_argument('--sheet', type=str, default=None,
                        help='Excel sheet name (default: active sheet)')

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Parse
    table = parse_table(str(input_path), sheet_name=args.sheet)

    # Apply --descend overrides
    if args.descend is not None:
        for col_1b in args.descend:
            ci = col_1b - 1
            if ci < 0 or ci >= len(table.columns):
                print(f"Error: Column {col_1b} exceeds table width ({len(table.columns)})",
                      file=sys.stderr)
                sys.exit(1)
            table.columns[ci].descend = True

    # Apply --column-bg
    bg_colors: dict[int, str] = {}
    if args.column_bg is not None:
        for spec in args.column_bg:
            col_str, color = spec.split(':', 1)
            ci = int(col_str) - 1
            if ci < 0 or ci >= len(table.columns):
                print(f"Error: Column {col_str} exceeds table width ({len(table.columns)})",
                      file=sys.stderr)
                sys.exit(1)
            bg_colors[ci] = color

    # Format
    output_tex = format_table(table, bg_colors=bg_colors, no_document=args.no_document)

    # Output
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_tex, encoding='utf-8')
        print(f"Written to {out_path}")
    else:
        print(output_tex)


if __name__ == '__main__':
    main()
