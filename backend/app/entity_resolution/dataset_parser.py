"""
Dataset parser for CSV and XLSX files.

Parses uploaded files into a list of row dicts and a DatasetSchema preview.
Does NOT store raw rows in the schema — only sample values and counts.
"""

from __future__ import annotations

import csv
import io
from typing import Dict, List, Optional, Tuple

from app.models.er_schemas import ColumnInfo, DatasetSchema


MAX_PREVIEW_ROWS = 10
MAX_SAMPLE_VALUES = 5


def _clean(value: Optional[str]) -> str:
    """Strip and coerce None to empty string."""
    if value is None:
        return ""
    return str(value).strip()


def parse_csv_bytes(
    raw_bytes: bytes,
    filename: str,
    party: str,
    encoding: str = "utf-8-sig",
) -> Tuple[List[Dict[str, str]], DatasetSchema]:
    """
    Parse raw CSV bytes into rows and a DatasetSchema.

    Returns:
        (rows, schema) where rows is a list of {col_name: str} dicts.
    """
    try:
        text = raw_bytes.decode(encoding)
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], _empty_schema(filename, party)

    headers: List[str] = [h.strip() for h in reader.fieldnames]
    rows: List[Dict[str, str]] = []
    for raw_row in reader:
        row = {h: _clean(raw_row.get(h)) for h in headers}
        rows.append(row)

    schema = _build_schema(filename, party, headers, rows)
    return rows, schema


def parse_xlsx_bytes(
    raw_bytes: bytes,
    filename: str,
    party: str,
) -> Tuple[List[Dict[str, str]], DatasetSchema]:
    """
    Parse raw XLSX bytes into rows and a DatasetSchema.
    """
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("openpyxl is required for XLSX support. Install it with: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return [], _empty_schema(filename, party)

    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        return [], _empty_schema(filename, party)

    headers: List[str] = [_clean(str(c)) if c is not None else f"Column_{i}" for i, c in enumerate(all_rows[0])]
    rows: List[Dict[str, str]] = []
    for raw_row in all_rows[1:]:
        row = {headers[i]: _clean(str(c)) if c is not None else "" for i, c in enumerate(raw_row)}
        rows.append(row)

    wb.close()
    schema = _build_schema(filename, party, headers, rows)
    return rows, schema


def _build_schema(
    filename: str,
    party: str,
    headers: List[str],
    rows: List[Dict[str, str]],
) -> DatasetSchema:
    columns: List[ColumnInfo] = []
    for idx, col in enumerate(headers):
        values = [r[col] for r in rows if r.get(col)]
        non_empty = len(values)
        samples = list(dict.fromkeys(v for v in values if v))[:MAX_SAMPLE_VALUES]
        columns.append(
            ColumnInfo(name=col, index=idx, sample_values=samples, non_empty_count=non_empty)
        )

    preview: List[Dict[str, str]] = rows[:MAX_PREVIEW_ROWS]

    return DatasetSchema(
        party=party,
        filename=filename,
        row_count=len(rows),
        columns=columns,
        preview_rows=preview,
    )


def _empty_schema(filename: str, party: str) -> DatasetSchema:
    return DatasetSchema(party=party, filename=filename, row_count=0, columns=[], preview_rows=[])


def parse_file_bytes(
    raw_bytes: bytes,
    filename: str,
    party: str,
) -> Tuple[List[Dict[str, str]], DatasetSchema]:
    """
    Dispatch to CSV or XLSX parser based on file extension.
    """
    name_lower = filename.lower()
    if name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
        return parse_xlsx_bytes(raw_bytes, filename, party)
    # Default: treat as CSV (also handles .txt, .tsv with comma delimiter)
    return parse_csv_bytes(raw_bytes, filename, party)
