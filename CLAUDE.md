# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 环境与命令

```bash
conda activate ai              # 开发环境
pip install -e .               # 可编辑安装
table2tex data.md -o out.tex   # CLI 入口，也支持 python -m table2tex
```

没有 lint/format 配置，没有测试框架。验证方式：用 `tests/` 下的 sample 文件跑端到端转换，检查输出 .tex。

## 架构

两阶段流水线：**parse → format**。

```
parse_table(path) → TableData → format_table(table, options) → str
```

### parse_table (parser.py)

按后缀分发到 `_parse_markdown` / `_parse_csv` / `_parse_excel` / `_parse_tex`。四种解析器都输出统一的 `TableData`：

- `headers: list[list[str]]` — 多行表头（纯文本，TeX 已剥离格式）
- `data: list[list[str]]` — 数据行（同上，纯文本）
- `columns: list[ColumnMeta]` — `is_numeric` 为 True 当列中 ≥ 2 个解析成功数值（非数值如 `--` 仅跳过不参与比较）
- `source: 'md' | 'csv' | 'xlsx' | 'tex'`

TeX 解析器额外填充 `tex_source`、`tex_body_start/end`、`tex_rows`（原始 cell 文本含 TeX 格式）、`tex_hlines`、`tex_trailing_hline` 等字段，用于后续字符串替换。

TeX cell 的格式剥离在 `utils.strip_tex_formatting` 中：逐层剥离 `\textbf`/`\color{red}`/裸 `{}`，最后反转 `\%` 等 TeX 转义。以花括号深度追踪实现，不是简单正则替换。

### format_table (formatter.py)

1. `_compute_highlights` — 对每个 `is_numeric=True` 的列，提取所有数值 → 去重排序 → 最优标 1、次优标 2（ties 共享）。`ColumnMeta.descend=True` 时升序（越小越好），否则降序。
2. 按 source 分两路输出：
   - **md/xlsx**：`_format_from_scratch` — 从零生成 `\begin{tabular}...\end{tabular}`。`--column-bg` 时用 beamer + colortbl，否则 ctexart。`_escape_tex` 对纯文本 cell 做 TeX 转义。
   - **tex**：`_format_tex` — 在 `tex_source` 上做字符串替换。重建 body 时按 `tex_hlines` 插入 `\hline`、按 `highlights` 替换需标注的 cell（取 `table.data[row][col]` 核心值 + `_apply_highlight` 包裹），未标注 cell 保留 `tex_rows` 原文。

`_apply_highlight(core, level)` 处理百分号：`96.88%` → `\color{red}{96.88}\%`（数值包在命令内，百分号在外）。

### utils.py

- `parse_cell_value(text)` → `(is_numeric, float_or_None, has_percent)` — 识别 `1,234.56`、`-3.14`、`1.5e3`、`96.88%`
- `split_tex_cells(row)` — 按 `&` 分割，追踪花括号深度避免误拆
- `strip_tex_formatting(cell)` — 见上文架构

### model.py

`TableData` 和 `ColumnMeta` 两个 dataclass。TeX 专属字段以 `tex_` 前缀区分。

### cli.py

argparse，`--descend` 和 `--column-bg` 均为 1-based 列号，进入 `format_table` 前转为 0-based。
