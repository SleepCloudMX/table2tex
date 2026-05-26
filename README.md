# table2tex

将 Markdown / Excel / TeX 表格转为 LaTeX，自动对每列最优值标红、次优值加粗。

## 安装

```bash
conda create -n convert python=3.12 -y
conda activate convert
pip install -e .
```

依赖：Python ≥ 3.10，openpyxl ≥ 3.1。`pip install -e .` 会自动安装 openpyxl。

> 本地开发环境名为 `ai` 而非 `convert`，按自己实际环境调整。

## 基本用法

安装后直接使用 `table2tex` 命令（也可通过 `python -m table2tex` 调用）。

### （1）Markdown → LaTeX

```bash
table2tex data.md -o out.tex
```

### （2）Excel → LaTeX

```bash
table2tex data.xlsx -o out.tex
table2tex data.xlsx --sheet Sheet2 -o out.tex   # 指定工作表
```

### （3）TeX → LaTeX

输入 TeX 表时只在原文本上替换 cell 内容，完整保留 `\begin{array}` / `\begin{tabular}`、`\multirow`、`\hline`、导言区等所有结构。已有的 `\textbf` 和 `\color{red}` 会被剥离后重新排名。

```bash
table2tex data.tex -o out.tex
```

### （4）指定越小越好的列

默认越大越好。`--descend` 指定越小越好的列（1-based 列号）：

```bash
# 第 2、5、6 列越小越好
table2tex data.tex --descend 2 5 6 -o out.tex
```

### （5）列背景色

F1 列蓝色背景、IoU 列黄色背景（1-based 列号）：

```bash
table2tex data.md --column-bg 5:blue!12 6:yellow!12 -o out.tex
```

有列背景色时自动切换为 beamer 文档类（需要 `colortbl` 宏包），无背景色则用 `ctexart`（支持中文）。

### （6）只输出表格片段

```bash
table2tex data.md --no-document
```

不含 `\documentclass`、`\begin{document}` 等包装，可直接粘贴到现有 LaTeX 文档。

### （7）打印到 stdout

省略 `-o` 则结果直接打印到终端：

```bash
table2tex data.md
```

## 参数

| 参数 | 说明 |
|------|------|
| `input` | 输入文件路径（.md / .xlsx / .xls / .tex） |
| `-o, --output` | 输出 .tex 路径（默认打印到 stdout，自动创建父目录） |
| `--descend COL [COL ...]` | 1-based 列号，指定越小越好的列 |
| `--column-bg COL:COLOR [...]` | 1-based 列背景色，如 `5:blue!12`。颜色为 xcolor 语法 |
| `--no-document` | 只输出 tabular 块 |
| `--sheet NAME` | Excel 工作表名（默认用活动工作表） |

## 标注规则

- 每列**最优值** → `\color{red}{value}`
- 每列**次优值** → `\textbf{value}`
- 并列最优/次优共享同色标注
- 列中数值少于 2 个时不标注
- 含 `%` 的列正常处理（剥离 `%` → 比较 → 拼回 `\%`）
- 含 `--` 等非数值单元格仅跳过，不影响该列参与比较

## 示例

以下示例基于这张对比表（`sample.md`）：

```
| Model              | OA    | Prec  | Recall | F1    | IoU   |
|--------------------|-------|-------|--------|-------|-------|
| ChangeCLIP         | 78.29 | 15.87 | 87.01  | 26.85 | 15.50 |
| DynamicEarth (MCI) | --    | --    | --     | 53.6  | 36.6  |
| DynamicEarth (IMC) | --    | --    | --     | 69.7  | 53.5  |
| SegEarthOV3        | 97.35 | 62.02 | 94.98  | 75.04 | 60.05 |
| OmniOVCD           | 97.92 | 68.17 | 94.80  | 79.31 | 65.71 |
| CoRegOVCD          | --    | 79.72 | 86.57  | 83.01 | 70.95 |
| DirectOVCD         | 98.45 | 76.35 | 91.26  | 83.14 | 71.14 |
```

### （1）基础转换

```bash
table2tex sample.md -o sample.tex
```

输出：

```latex
\documentclass{ctexart}
\usepackage{booktabs, multirow, makecell, xcolor}
\begin{document}
\begin{tabular}{c c c c c c}
\hline
Model & OA & Prec & Recall & F1 & IoU \\
\hline
ChangeCLIP         & 78.29 & 15.87 & 87.01  & 26.85 & 15.50 \\
DynamicEarth (MCI) & --    & --    & --     & 53.6  & 36.6  \\
DynamicEarth (IMC) & --    & --    & --     & 69.7  & 53.5  \\
SegEarthOV3        & 97.35 & 62.02 & \color{red}{94.98}  & 75.04 & 60.05 \\
OmniOVCD           & \textbf{97.92} & 68.17 & \textbf{94.80}  & 79.31 & 65.71 \\
CoRegOVCD          & --    & \color{red}{79.72} & 86.57  & \textbf{83.01} & \textbf{70.95} \\
DirectOVCD         & \color{red}{98.45} & \textbf{76.35} & 91.26  & \color{red}{83.14} & \color{red}{71.14} \\
\hline
\end{tabular}
\end{document}
```

OA 列 98.45 最优（红）、97.92 次优（粗）—— `--` 不影响排名。

### （2）列背景色：F1 蓝色、IoU 黄色

```bash
table2tex sample.md --column-bg 5:blue!12 6:yellow!12 -o sample_bg.tex
```

有列背景色时自动切换为 beamer 模板：

```latex
\documentclass{beamer}
\usepackage{booktabs, multirow, makecell}
\usepackage{xcolor, colortbl}
\begin{document}
\begin{frame}
\centering
\begin{tabular}{c c c c >{\columncolor{blue!12}}c >{\columncolor{yellow!12}}c}
\hline
Model & OA & Prec & Recall & F1 & IoU \\
\hline
...
DirectOVCD & \color{red}{98.45} & \textbf{76.35} & 91.26 & \color{red}{83.14} & \color{red}{71.14} \\
\hline
\end{tabular}
\end{frame}
\end{document}
```

### （3）TeX 输入：越小越好的列

原始 `sample.tex` 是一张包含 `\multirow` 和 `\begin{array}` 的表格。τ、误检实例、误检实例像素、漏检实例、漏检实例像素 这五列越小越好。

```bash
table2tex sample.tex --descend 2 5 6 7 8 -o sample_tex.tex
```

输出保留原始 `\input{settings}`、`\[`、`\begin{array}`、`\multirow` 等所有结构，仅 cell 内容被替换为带红/粗标注的版本。

### （4）Excel 输入

```bash
table2tex sample.xlsx --descend 3 -o sample_xl.tex
```

首行自动识别为表头，合并单元格自动展开。

## 输入格式一览

| 格式 | 后缀 | 处理方式 |
|------|------|----------|
| Markdown | `.md` | 按 `|---|` 分隔行识别表头/数据，`|` 分割单元格 |
| Excel | `.xlsx` `.xls` | 首行作表头，自动展开合并单元格 |
| TeX | `.tex` | 查找 `\begin{array}` 或 `\begin{tabular}`，在原文本上替换 cell 内容 |

TeX 输入中 `\multirow` 行保留不动（其文本一般为标签而非指标），已有的 `\textbf` / `\color{red}` 标注会被剥离后重新排名。
