"""
data_loader.py
---------------
Everything related to reading the Excel workbook off disk / upload
buffer, validating it, and handing back a clean DataFrame.

No business logic (status normalisation, summary counts, etc.) lives
here on purpose - see data_processing.py for that.
"""

from dataclasses import dataclass, field
import pandas as pd
import streamlit as st

from config import COLUMNS, REQUIRED_COLUMNS


@dataclass
class LoadResult:
    ok: bool
    df: pd.DataFrame = None
    sheet_used: str = None
    sheets_available: list = field(default_factory=list)
    missing_required: list = field(default_factory=list)
    missing_optional: list = field(default_factory=list)
    error: str = None


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from column headers so 'Designation ' ->
    'Designation'. Column CONTENT is not touched here."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _pick_best_sheet(sheets: dict) -> str:
    """If the workbook has multiple sheets, pick the one that contains
    the most of our required columns (after header cleaning)."""
    best_name, best_score = None, -1
    for name, df in sheets.items():
        cleaned = _clean_columns(df)
        score = sum(1 for c in REQUIRED_COLUMNS if c in cleaned.columns)
        if score > best_score:
            best_name, best_score = name, score
    return best_name


@st.cache_data(show_spinner=False)
def load_workbook(file_bytes: bytes) -> LoadResult:
    """
    Load an Excel workbook from raw bytes (works for both an uploaded
    file and a file read from disk). Cached by Streamlit on the exact
    bytes, so re-uploading an unchanged file is instant, and uploading
    a genuinely new/updated workbook automatically busts the cache.
    """
    try:
        all_sheets = pd.read_excel(pd.io.common.BytesIO(file_bytes), sheet_name=None)
    except Exception as exc:  # noqa: BLE001 - surface any read error to the UI
        return LoadResult(ok=False, error=f"Could not read the Excel file: {exc}")

    if not all_sheets:
        return LoadResult(ok=False, error="The workbook appears to be empty.")

    sheet_name = _pick_best_sheet(all_sheets)
    df = _clean_columns(all_sheets[sheet_name])

    missing_required = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    missing_optional = [
        v for k, v in COLUMNS.items()
        if v not in REQUIRED_COLUMNS and v not in df.columns
    ]

    if missing_required:
        return LoadResult(
            ok=False,
            sheet_used=sheet_name,
            sheets_available=list(all_sheets.keys()),
            missing_required=missing_required,
            missing_optional=missing_optional,
            error=(
                "The workbook is missing required column(s): "
                + ", ".join(missing_required)
                + ". Please check the file and try again."
            ),
        )

    # Normalise blank-ish string cells (nbsp, empty strings, '--') to real NaN
    # WITHOUT altering genuinely meaningful text. This only touches
    # obviously-placeholder values.
    placeholder_values = {"", "--", "\xa0", "N/A", "NA", "n/a"}
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(
                lambda v: pd.NA if isinstance(v, str) and v.strip() in placeholder_values else v
            )
            df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)

    return LoadResult(
        ok=True,
        df=df,
        sheet_used=sheet_name,
        sheets_available=list(all_sheets.keys()),
        missing_required=[],
        missing_optional=missing_optional,
    )
