@echo off
REM Run table2tex tests — converts sample.md, sample.tex, sample.xlsx
REM Usage: run_test.bat   (from tests/ directory)

cd /d "%~dp0"

echo Activating conda environment...
call conda activate ai
if errorlevel 1 (
    echo Failed to activate conda environment 'ai'
    exit /b 1
)

if not exist "output" mkdir "output"

echo.
echo ========================================
echo  (1) Markdown basic conversion
echo ========================================
table2tex sample.md -o output\sample_md.tex
if errorlevel 1 (echo FAILED) else (echo OK)

echo.
echo ========================================
echo  (2) Markdown with column background
echo ========================================
table2tex sample.md --column-bg 5:blue!12 6:yellow!12 -o output\sample_md_bg.tex
if errorlevel 1 (echo FAILED) else (echo OK)

echo.
echo ========================================
echo  (3) TeX with smaller-is-better columns
echo ========================================
table2tex sample.tex --descend 2 5 6 7 8 -o output\sample_tex.tex
if errorlevel 1 (echo FAILED) else (echo OK)

echo.
echo ========================================
echo  (4) Excel basic conversion
echo ========================================
table2tex sample.xlsx -o output\sample_xl.tex
if errorlevel 1 (echo FAILED) else (echo OK)

echo.
echo ========================================
echo  (5) CSV basic conversion
echo ========================================
table2tex sample.csv -o output\sample_csv.tex
if errorlevel 1 (echo FAILED) else (echo OK)

echo.
echo ========================================
echo  (6) Markdown with row/column exclusion
echo ========================================
table2tex sample.md --exclude-cols Model --exclude-rows "DynamicEarth (MCI)" "DynamicEarth (IMC)" -o output\sample_exclude.tex
if errorlevel 1 (echo FAILED) else (echo OK)

echo.
echo ========================================
echo  All tests done. Output in tests\output\
echo ========================================
dir /b output\
