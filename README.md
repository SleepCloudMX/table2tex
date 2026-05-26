# table2tex

将 Markdown / Excel / TeX 表格转为 LaTeX，自动对每列最优值标红、次优值加粗。

## 安装

```bash
conda activate ai
pip install -e .
```

依赖：Python ≥ 3.10，openpyxl ≥ 3.1。

## 基本用法

```bash
# Markdown → LaTeX
python -m table2tex data.md -o out.tex

# Excel → LaTeX
python -m table2tex data.xlsx -o out.tex

# TeX → LaTeX（仅添加红/粗标注，保留原有结构）
python -m table2tex data.tex -o out.tex

# 不指定 -o 则打印到 stdout
python -m table2tex data.md
```

## 标注规则

- **每列最优值** → `\color{red}{value}`（红色）
- **每列次优值** → `\textbf{value}`（加粗）
- 并列最优/次优：多个单元格共享同色标注
- 默认**越大越好**，通过 `--descend` 指定越小越好的列
- 列中数值少于 2 个时不标注（无法比较）
- 含 `%` 的列正常处理（剥离 → 比较 → 拼回）
- 含 `--` 等非数值单元格仅跳过，不影响该列参与比较

## 参数

| 参数 | 说明 |
|------|------|
| `input` | 输入文件路径（.md / .xlsx / .xls / .tex） |
| `-o, --output` | 输出 .tex 路径（默认打印到 stdout） |
| `--descend COL [COL ...]` | 1-based 列号，指定越小越好的列 |
| `--column-bg COL:COLOR [...]` | 1-based 列背景色，如 `5:blue!12`（自动启用 beamer 模板） |
| `--no-document` | 只输出 tabular 块，不含 `\documentclass` 等包装 |
| `--sheet NAME` | Excel 工作表名（默认用活动工作表） |

## 示例

以下示例基于 input/sample.md（论文实验对比表）：

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

### 基础转换

```bash
python -m table2tex input/sample.md -o output/sample.tex
```

输出（默认 `ctexart` 文档类，支持中文）：

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

OA 列：98.45 最优（红）、97.92 次优（粗）——`--` 被跳过不影响排名。

### 列背景色（F1 蓝色、IoU 黄色）

```bash
python -m table2tex input/sample.md --column-bg 5:blue!12 6:yellow!12 -o output/sample_bg.tex
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

### 指定越小越好的列 + Excel 输入

```bash
# τ 列和误检/漏检列 → 越小越好
python -m table2tex input/sample.tex --descend 2 5 6 7 8 -o output/sample_tex.tex
```

输入是 TeX 表时，只在原文本上替换 cell 内容，**完整保留** `\begin{array}` / `\begin{tabular}`、`\multirow`、`\hline`、导言区等所有结构。

```bash
# Excel 同样支持 --descend 和 --column-bg
python -m table2tex data.xlsx --descend 3 --column-bg 4:red!5 -o out.tex
```

### 只输出表格片段

```bash
python -m table2tex data.md --no-document
```

输出不含 `\documentclass`、`\begin{document}` 等包装，可直接粘贴到现有 LaTeX 文档中。

## 输入格式说明

| 格式 | 后缀 | 处理方式 |
|------|------|----------|
| Markdown | `.md` | 按 `|---|` 分隔行识别表头/数据，`|` 分割单元格 |
| Excel | `.xlsx` `.xls` | 首行作表头，自动展开合并单元格 |
| TeX | `.tex` | 查找 `\begin{array}` 或 `\begin{tabular}`，在原文本上替换 cell 内容 |

TeX 输入会自动剥离已有的 `\textbf`、`\color{red}` 标注后重新排名；`\multirow` 行保留不动（其文本一般为标签而非指标）。

## 列背景色

`--column-bg` 使用 1-based 列号，颜色为 xcolor 语法：

```
--column-bg 3:blue!12 5:green!10 7:yellow!20
```

有列背景色时自动使用 beamer 文档类（需要 `colortbl` 宏包），无背景色则用 `ctexart`。
