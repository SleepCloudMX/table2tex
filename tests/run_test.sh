#!/usr/bin/env bash
# Run table2tex tests — converts sample.md, sample.tex, sample.xlsx
# Usage: bash run_test.sh   (from tests/ directory)

set -euo pipefail
cd "$(dirname "$0")"

echo "Activating conda environment..."
eval "$(conda shell.bash hook)"
conda activate ai

mkdir -p output

echo
echo "========================================"
echo " (1) Markdown basic conversion"
echo "========================================"
table2tex sample.md -o output/sample_md.tex && echo OK || echo FAILED

echo
echo "========================================"
echo " (2) Markdown with column background"
echo "========================================"
table2tex sample.md --column-bg 5:blue!12 6:yellow!12 -o output/sample_md_bg.tex && echo OK || echo FAILED

echo
echo "========================================"
echo " (3) TeX with smaller-is-better columns"
echo "========================================"
table2tex sample.tex --descend 2 5 6 7 8 -o output/sample_tex.tex && echo OK || echo FAILED

echo
echo "========================================"
echo " (4) Excel basic conversion"
echo "========================================"
table2tex sample.xlsx -o output/sample_xl.tex && echo OK || echo FAILED

echo
echo "========================================"
echo " All tests done. Output in tests/output/"
echo "========================================"
ls -1 output/
