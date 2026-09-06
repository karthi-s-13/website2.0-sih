"""Lightweight column profiling over the raw Flash Report CSVs (Phase 1:
"profile columns", "identify data types", "identify missing values",
"detect duplicates" at the raw-file level, before any cleaning).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def profile_csv(path: Path) -> dict[str, Any]:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")

    columns: dict[str, Any] = {}
    for col in df.columns:
        series = df[col]
        non_missing = series[~series.isin(["", "-", "--", "NA", "N/A", "na", "n/a"])]
        numeric = pd.to_numeric(non_missing, errors="coerce")
        numeric_ratio = numeric.notna().mean() if len(non_missing) else 0.0

        col_profile: dict[str, Any] = {
            "inferred_type": "numeric" if numeric_ratio > 0.9 else "text",
            "missing_count": int(len(series) - len(non_missing)),
            "missing_pct": round(100 * (len(series) - len(non_missing)) / len(series), 1) if len(series) else 0.0,
            "unique_count": int(non_missing.nunique()),
            "sample_values": non_missing.drop_duplicates().head(3).tolist(),
        }
        if numeric_ratio > 0.9 and numeric.notna().any():
            col_profile["min"] = float(numeric.min())
            col_profile["max"] = float(numeric.max())
        columns[col] = col_profile

    duplicate_key_cols = [c for c in ("project_code", "report_month", "edition") if c in df.columns]
    duplicate_count = 0
    if "project_code" in df.columns:
        key_cols = [c for c in ("project_code", "report_month", "edition") if c in df.columns]
        duplicate_count = int(df.duplicated(subset=key_cols).sum())

    return {
        "file": path.name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "duplicate_key_columns": duplicate_key_cols,
        "duplicate_row_count": duplicate_count,
    }


def profile_directory(directory: Path, pattern: str = "*.csv") -> dict[str, Any]:
    files = sorted(directory.glob(pattern))
    return {
        "source_directory": str(directory),
        "file_count": len(files),
        "files": [profile_csv(f) for f in files],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Flash Report data profile",
        "",
        f"Source directory: `{report['source_directory']}`  ",
        f"Files profiled: {report['file_count']}",
        "",
    ]
    for file_report in report["files"]:
        lines.append(f"## {file_report['file']}")
        lines.append("")
        lines.append(f"{file_report['row_count']} rows, {file_report['column_count']} columns, "
                      f"{file_report['duplicate_row_count']} duplicate rows on "
                      f"{file_report['duplicate_key_columns']}")
        lines.append("")
        lines.append("| column | type | missing | unique | sample |")
        lines.append("|---|---|---|---|---|")
        for col, profile in file_report["columns"].items():
            sample = ", ".join(str(v) for v in profile["sample_values"])
            lines.append(
                f"| {col} | {profile['inferred_type']} | {profile['missing_count']} "
                f"({profile['missing_pct']}%) | {profile['unique_count']} | {sample} |"
            )
        lines.append("")
    return "\n".join(lines)
