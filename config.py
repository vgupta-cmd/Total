"""
config.py
---------
Central place for app settings and the Excel column mapping.

Editing this file is the ONLY thing you should need to do if your
Excel workbook's column headers ever change slightly (e.g. renamed,
reordered). Nothing else in the app hardcodes column positions -
everything looks columns up by name through this file.
"""

import os

# ---------------------------------------------------------------------
# App identity
# ---------------------------------------------------------------------
APP_TITLE = "Student Placement Tracker"
APP_SUBTITLE = "Univo Career Services · LineupX Placement Records"
APP_ICON = "🎓"

# ---------------------------------------------------------------------
# Authentication (simple shared-password gate for the local prototype)
# ---------------------------------------------------------------------
# For a quick local prototype we use ONE shared staff password.
# Set it as an environment variable before launching Streamlit:
#
#   Windows (Command Prompt):   set STAFF_PASSWORD=your-password
#   Windows (PowerShell):       $env:STAFF_PASSWORD="your-password"
#
# If not set, a default demo password is used - CHANGE THIS before
# giving the app to anyone else. See README.md, section "Security".
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "univo-careers-2026")

# ---------------------------------------------------------------------
# Default data file (optional)
# ---------------------------------------------------------------------
# If a workbook already exists at this path when the app starts, it is
# loaded automatically. Otherwise staff must upload it from the
# sidebar. Keep real student data OUT of source control (see .gitignore).
DEFAULT_DATA_PATH = os.environ.get("DATA_PATH", "data/Total_Data.xlsx")

# ---------------------------------------------------------------------
# Column mapping
# ---------------------------------------------------------------------
# Keys = internal names used throughout the app.
# Values = the exact column header found in the workbook, AFTER we
#          strip leading/trailing whitespace from every header on load
#          (see data_loader.clean_columns). This means "Designation "
#          in the raw file is matched here as "Designation".
COLUMNS = {
    "serial_no":        "S.no",
    "enrollment_no":     "Enrollment Number",
    "name":              "Name",
    "email":             "Email id",
    "mobile":            "Mobile",
    "program":           "Program",
    "session":           "Session",
    "specialisation":    "Specialisation",
    "dop":               "DOP",          # Date of Posting (application/posting date)
    "lor":               "LOR",          # Last date of Response (deadline)
    "company":           "Company Name",
    "domain":            "Domain",
    "designation":       "Designation",
    "job_type":          "Job Type",
    "stipend":           "Stipend",
    "salary":            "Salary",
    "eligible_raw":      "Eligible",
    "jd_attendance_raw": "A-JD",
    "appeared_raw":      "A",
    "selection_raw":     "S",
    "feedback":          "Feedback",
}

# Columns that MUST exist for the app to function at all.
REQUIRED_COLUMNS = [
    COLUMNS["name"],
    COLUMNS["email"],
    COLUMNS["company"],
    COLUMNS["eligible_raw"],
    COLUMNS["appeared_raw"],
    COLUMNS["selection_raw"],
]

# Columns that are nice to have but the app will degrade gracefully
# (showing "Not available in source data") if they are missing.
OPTIONAL_COLUMNS = [v for k, v in COLUMNS.items() if v not in REQUIRED_COLUMNS]

# Fields considered "sensitive" - shown only on the individual student
# record after a successful staff search, never in any aggregate /
# admin table.
SENSITIVE_FIELDS = ["mobile", "enrollment_no"]
