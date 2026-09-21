"""
data_processing.py
-------------------
All the "business logic": turning the messy, inconsistently-typed
status text in the workbook into clean, reliable categories, and
computing the summary counts shown on the dashboard.

DESIGN PRINCIPLE: we never overwrite the original columns. Every
normalised value is added as a NEW column (e.g. "Eligibility Status"),
so the source data the Career Services team already trusts is always
still there, untouched, in the original columns.

See README.md -> "How the numbers are calculated" for the plain-English
version of the rules encoded here.
"""

import re
import pandas as pd
from config import COLUMNS

# ----------------------------------------------------------------------
# Low level text helpers
# ----------------------------------------------------------------------

def _norm(val) -> str:
    """Lowercase, whitespace-collapsed version of a cell for pattern
    matching. Returns '' for missing values."""
    if pd.isna(val):
        return ""
    return re.sub(r"\s+", " ", str(val)).strip().lower()


def normalize_email(email) -> str:
    """Case-insensitive, whitespace-tolerant email normalisation used
    for BOTH storing a lookup key and matching the search box."""
    if pd.isna(email):
        return ""
    return re.sub(r"\s+", "", str(email)).strip().lower()


# ----------------------------------------------------------------------
# Status normalisation
# ----------------------------------------------------------------------

def normalize_eligibility(val) -> str:
    """
    Source values look like: 'E', 'NE', 'NE-Location', 'NE - Education',
    'Not Eligible', 'Ne-Education', blank, ...

    Rule: value starting with 'ne' (after trimming) OR containing the
    phrase 'not eligible' => Not Eligible. Exactly 'e' => Eligible.
    Anything else (blank, unrecognised) => Unknown, and is flagged in
    the Data Quality section rather than guessed at.
    """
    t = _norm(val)
    if t == "e":
        return "Eligible"
    if t.startswith("ne") or "not eligible" in t:
        return "Not Eligible"
    if t == "":
        return "Unknown"
    return "Unknown"


def normalize_jd_attendance(val) -> str:
    """
    Source values look like: 'A-JD', 'NA-A-JD', 'NS', 'NS - AJD', blank.
    'NS' family = Not Scheduled (the JD round hadn't been scheduled /
    recorded at the time of data entry).
    """
    t = _norm(val)
    if t == "":
        return "Unknown"
    if "na-a-jd" in t.replace(" ", ""):
        return "Not Attended"
    if t.startswith("ns"):
        return "Not Scheduled"
    if "a-jd" in t.replace(" ", ""):
        return "Attended"
    return "Unknown"


def normalize_appeared(val) -> str:
    """
    Source values look like: 'A-PI', 'NA-A-PI', 'A-NA', 'NS',
    'Not appeared', blank.
    Checked in this order: explicit "not appeared" wording, any 'NA'
    marker (not appeared), 'NS' (not scheduled), then 'A-PI' (appeared).
    """
    t = _norm(val)
    if t == "":
        return "Unknown"
    if "not appeared" in t:
        return "Not Appeared"
    compact = t.replace(" ", "")
    if "na" in compact:
        return "Not Appeared"
    if t.startswith("ns"):
        return "Not Scheduled"
    if "a-pi" in compact or compact == "a":
        return "Appeared"
    return "Unknown"


_SELECTED_VALUES = {"s", "s-1", "s1", "selected"}
_REJECTED_SNIPPETS = ["rej", "not selected", "poor communication"]
_NOSHOW_SNIPPETS = ["no show", "not appeared"]


def _classify_selection_raw(val) -> str:
    """Classify the raw 'S' column value into selected / rejected /
    no_show / not_scheduled / blank / other, used as an input signal
    to compute_final_status (never shown to users directly)."""
    t = _norm(val)
    if t == "":
        return "blank"
    if t in _SELECTED_VALUES:
        return "selected"
    if any(s in t for s in _NOSHOW_SNIPPETS):
        return "no_show"
    if any(s in t for s in _REJECTED_SNIPPETS):
        return "rejected"
    if t.startswith("ns"):
        return "not_scheduled"
    if t == "ne":
        return "not_eligible_echo"  # redundant echo of eligibility, ignore
    return "other"


def compute_final_status(eligibility: str, appeared: str, selection_class: str) -> str:
    """
    The single source of truth for "what actually happened" with an
    application, combining eligibility + appeared + selection signals
    so the summary cards never mix these up.

    Rules (in order):
      1. Not Eligible            -> "Not Eligible"      (never counted as an interview rejection)
      2. Selection says No-Show  -> "Not Appeared"       (overrides everything else below)
      3. Not Appeared             -> "Not Appeared"       (never counted as "Rejected")
      4. Not Scheduled / Unknown appearance -> "Pending"  (process not recorded as run yet)
      5. Appeared:
           a. Selection = selected -> "Selected"
           b. Selection = rejected -> "Rejected"
           c. Selection = blank / not_scheduled / other -> "Pending" (result not recorded yet)
    """
    if eligibility != "Eligible":
        return "Not Eligible"

    if selection_class == "no_show":
        return "Not Appeared"

    if appeared == "Not Appeared":
        return "Not Appeared"

    if appeared in ("Not Scheduled", "Unknown"):
        return "Pending"

    # appeared == "Appeared"
    if selection_class == "selected":
        return "Selected"
    if selection_class == "rejected":
        return "Rejected"
    return "Pending"


# ----------------------------------------------------------------------
# Main enrichment entry point
# ----------------------------------------------------------------------

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add every derived column needed by the rest of the app. Safe to
    call once after loading; original columns are left untouched."""
    df = df.copy()
    c = COLUMNS

    df["_email_key"] = df[c["email"]].apply(normalize_email) if c["email"] in df else ""
    df["_company_key"] = (
        df[c["company"]].apply(lambda v: _norm(v)) if c["company"] in df else ""
    )

    df["Eligibility Status"] = (
        df[c["eligible_raw"]].apply(normalize_eligibility) if c["eligible_raw"] in df else "Unknown"
    )
    df["JD Attendance Status"] = (
        df[c["jd_attendance_raw"]].apply(normalize_jd_attendance)
        if c["jd_attendance_raw"] in df else "Unknown"
    )
    df["Appeared Status"] = (
        df[c["appeared_raw"]].apply(normalize_appeared) if c["appeared_raw"] in df else "Unknown"
    )

    selection_class = (
        df[c["selection_raw"]].apply(_classify_selection_raw) if c["selection_raw"] in df else "blank"
    )
    df["_selection_class"] = selection_class

    df["Final Status"] = [
        compute_final_status(e, a, s)
        for e, a, s in zip(df["Eligibility Status"], df["Appeared Status"], selection_class)
    ]

    # Job type, cleaned for display and filtering
    if c["job_type"] in df:
        df["Job Type (Clean)"] = df[c["job_type"]].apply(
            lambda v: {"i": "Internship", "p": "Placement", "i+p": "Internship + Placement (PPO)"}.get(
                _norm(v), (str(v).strip() if pd.notna(v) else "Not specified")
            )
        )
    else:
        df["Job Type (Clean)"] = "Not specified"

    # Compensation: show stipend for internships, salary for placements,
    # whichever is present otherwise. Never invents a number.
    def _compensation(row):
        stip = row.get(c["stipend"]) if c["stipend"] in df else None
        sal = row.get(c["salary"]) if c["salary"] in df else None
        jt = _norm(row.get(c["job_type"])) if c["job_type"] in df else ""
        if "i" in jt and pd.notna(stip):
            base = f"Stipend: {stip}"
        elif "p" in jt and pd.notna(sal):
            base = f"Salary: {sal}"
        elif pd.notna(stip):
            base = f"Stipend: {stip}"
        elif pd.notna(sal):
            base = f"Salary: {sal}"
        else:
            base = "Not recorded"
        return base

    df["Compensation"] = df.apply(_compensation, axis=1)

    return df


# ----------------------------------------------------------------------
# Student-level lookups
# ----------------------------------------------------------------------

def find_student(df: pd.DataFrame, email_query: str) -> pd.DataFrame:
    """Case-insensitive, whitespace-tolerant match on email."""
    key = normalize_email(email_query)
    if not key:
        return df.iloc[0:0]
    return df[df["_email_key"] == key]


def summarize(df_student: pd.DataFrame) -> dict:
    """
    Compute the placement-summary dashboard numbers for one student's
    rows. Every number below is a plain count/nunique over the
    'Final Status' / 'Eligibility Status' / 'Appeared Status' columns
    computed in enrich() - no double logic, no re-guessing.
    """
    total_applications = len(df_student)
    unique_companies = df_student["_company_key"].nunique()

    eligible = int((df_student["Eligibility Status"] == "Eligible").sum())
    not_eligible = int((df_student["Eligibility Status"] == "Not Eligible").sum())

    appeared = int((df_student["Appeared Status"] == "Appeared").sum())
    not_appeared = int((df_student["Final Status"] == "Not Appeared").sum())

    selected = int((df_student["Final Status"] == "Selected").sum())
    rejected = int((df_student["Final Status"] == "Rejected").sum())
    pending = int((df_student["Final Status"] == "Pending").sum())

    return {
        "total_applications": total_applications,
        "unique_companies": unique_companies,
        "eligible": eligible,
        "not_eligible": not_eligible,
        "appeared": appeared,
        "not_appeared": not_appeared,
        "selected": selected,
        "rejected": rejected,
        "pending": pending,
    }


# ----------------------------------------------------------------------
# Data quality checks (workbook-wide)
# ----------------------------------------------------------------------

def data_quality_report(df: pd.DataFrame) -> dict:
    c = COLUMNS
    issues = {}

    if c["email"] in df:
        issues["missing_email"] = df[df[c["email"]].isna()]
    if c["company"] in df:
        issues["missing_company"] = df[df[c["company"]].isna()]

    issues["unknown_eligibility"] = df[df["Eligibility Status"] == "Unknown"]

    # Logical inconsistency: marked Not Eligible but shows an Appeared/
    # Selected/Rejected outcome anyway (shouldn't happen if the process
    # was followed correctly).
    inconsistent_mask = (df["Eligibility Status"] == "Not Eligible") & (
        df["Appeared Status"] == "Appeared"
    )
    issues["inconsistent_not_eligible"] = df[inconsistent_mask]

    # Potential duplicate applications: same student + same company +
    # same designation appearing more than once.
    dup_cols = [c["email"], c["company"]]
    if c["designation"] in df:
        dup_cols.append(c["designation"])
    dup_mask = df.duplicated(subset=dup_cols, keep=False) & df[c["email"]].notna() & df[c["company"]].notna()
    issues["potential_duplicates"] = df[dup_mask].sort_values(dup_cols)

    return issues
