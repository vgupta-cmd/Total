"""
utils.py
--------
Small reusable helpers, mainly for turning a DataFrame into
downloadable bytes (Excel / CSV) using openpyxl / pandas.
"""

import io
import pandas as pd


def to_excel_bytes(sheets: dict) -> bytes:
    """sheets: {sheet_name: DataFrame}. Returns .xlsx file bytes."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe_name = name[:31]  # Excel sheet name limit
            df.to_excel(writer, sheet_name=safe_name, index=False)
    return buffer.getvalue()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")
