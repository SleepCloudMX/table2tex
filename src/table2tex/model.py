from dataclasses import dataclass, field


@dataclass
class ColumnMeta:
    index: int
    descend: bool = False        # True = smaller is better
    is_numeric: bool = False     # all data cells in this column are numeric
    bg_color: str | None = None  # e.g. 'blue!12'


@dataclass
class TableData:
    headers: list[list[str]]       # header rows, each is list of raw cell text
    data: list[list[str]]          # data rows, raw cell text (stripped of tex formatting)
    columns: list[ColumnMeta]
    source: str                    # 'md' | 'xlsx' | 'tex'

    # TeX-specific: for in-place string substitution
    tex_source: str | None = None          # original .tex file content
    tex_body_start: int | None = None      # char offset where table body begins in tex_source
    tex_body_end: int | None = None        # char offset where table body ends
    tex_rows: list[list[str]] | None = None  # original cell texts per row (with tex formatting)
    tex_hlines: set[int] | None = None     # row indices (0-based) where \hline appears before the row
    tex_env_type: str | None = None        # 'array' or 'tabular'
    tex_col_spec: str | None = None        # column specification string
    tex_trailing_hline: bool = False       # True if body ends with \hline
