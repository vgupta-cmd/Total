"""
app.py
------
Student Placement Tracker - main Streamlit entry point.

Run with:  streamlit run app.py

Page structure (see sidebar):
  - Student Search        : lookup a student by email, view profile +
                             placement summary + company-wise history
  - Data Quality           : duplicates / missing / inconsistent records
  - Admin Analytics        : optional, workbook-wide statistics
  - Upload / Refresh Data  : replace the loaded workbook
"""

import os
import pandas as pd
import streamlit as st

from config import APP_TITLE, APP_SUBTITLE, APP_ICON, COLUMNS, DEFAULT_DATA_PATH, SENSITIVE_FIELDS
from auth import require_login
from data_loader import load_workbook
from data_processing import enrich, find_student, summarize, data_quality_report
from utils import to_excel_bytes, to_csv_bytes

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

# ----------------------------------------------------------------------
# Light styling (plain CSS injected once - safe even with basic CSS
# knowledge, nothing here needs to be edited to run the app)
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    .metric-card {
        background: #ffffff;
        border: 1px solid #e6e8ec;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(16,24,40,0.06);
    }
    .metric-label { font-size: 0.80rem; color: #667085; font-weight: 600; letter-spacing: .02em; }
    .metric-value { font-size: 1.6rem; font-weight: 700; color: #101828; }
    .badge {
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: 0.78rem; font-weight: 600;
    }
    .badge-green  { background:#DCFCE7; color:#166534; }
    .badge-red    { background:#FEE2E2; color:#991B1B; }
    .badge-amber  { background:#FEF3C7; color:#92400E; }
    .badge-gray   { background:#F1F5F9; color:#475569; }
    .badge-blue   { background:#DBEAFE; color:#1E40AF; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Login gate
# ----------------------------------------------------------------------
require_login()

# ----------------------------------------------------------------------
# Sidebar: branding + navigation + data source
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### {APP_ICON} {APP_TITLE}")
    st.caption(APP_SUBTITLE)
    st.divider()

    page = st.radio(
        "Navigate",
        ["🔍 Student Search", "🧹 Data Quality", "📊 Admin Analytics", "⬆️ Upload / Refresh Data"],
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("Log out"):
        st.session_state["authenticated"] = False
        st.rerun()

# ----------------------------------------------------------------------
# Load data (session-held upload takes priority over the default path)
# ----------------------------------------------------------------------
if "workbook_bytes" not in st.session_state:
    st.session_state["workbook_bytes"] = None
    if os.path.exists(DEFAULT_DATA_PATH):
        with open(DEFAULT_DATA_PATH, "rb") as f:
            st.session_state["workbook_bytes"] = f.read()

workbook_bytes = st.session_state["workbook_bytes"]

if workbook_bytes is None:
    st.warning(
        "No workbook loaded yet. Go to **⬆️ Upload / Refresh Data** in the sidebar "
        "to upload `Total_Data.xlsx` (or place it at `data/Total_Data.xlsx` and restart)."
    )
    st.stop()

with st.spinner("Loading and validating workbook..."):
    result = load_workbook(workbook_bytes)

if not result.ok:
    st.error(result.error or "The workbook could not be loaded.")
    if result.missing_required:
        st.info(
            "Required columns not found: " + ", ".join(result.missing_required) +
            ". Please check the file and re-upload it from **Upload / Refresh Data**."
        )
    st.stop()

df = enrich(result.df)
c = COLUMNS

if result.missing_optional:
    st.info(
        "ℹ️ Some optional columns were not found in the workbook, so related fields "
        "will show as 'Not available in source data': " + ", ".join(result.missing_optional)
    )

# ========================================================================
# PAGE: Student Search
# ========================================================================
if page == "🔍 Student Search":
    st.title("🔍 Student Search")
    st.caption("Search by the student's email address to view their full placement application history.")

    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        query = st.text_input(
            "Email address", key="search_query", placeholder="e.g. chirag49@amityonline.com",
            label_visibility="collapsed",
        )
    with col2:
        search_clicked = st.button("Search", type="primary", use_container_width=True)
    with col3:
        clear_clicked = st.button("Clear", use_container_width=True)

    if clear_clicked:
        st.session_state["search_query"] = ""
        st.rerun()

    if search_clicked or query:
        if not query.strip():
            st.info("Enter an email address above and click **Search**.")
        else:
            student_df = find_student(df, query)

            if student_df.empty:
                st.error(f"No student found with the email **{query.strip()}**. "
                          "Check the spelling, or the student may not be in this workbook.")
            else:
                first = student_df.iloc[0]

                # ---------------- Profile ----------------
                st.subheader("Student Profile")
                p1, p2, p3 = st.columns(3)
                p1.markdown(f"**Name:** {first.get(c['name'], 'Not available')}")
                p1.markdown(f"**Email:** {first.get(c['email'], 'Not available')}")
                if c["enrollment_no"] in df:
                    p1.markdown(f"**Enrollment No.:** {first.get(c['enrollment_no'], 'Not available')}")
                p2.markdown(f"**Program:** {first.get(c['program'], 'Not available') if c['program'] in df else 'Not available in source data'}")
                if c["specialisation"] in df:
                    spec = first.get(c["specialisation"])
                    p2.markdown(f"**Specialisation:** {spec if pd.notna(spec) else 'Not specified'}")
                if c["session"] in df:
                    p2.markdown(f"**Session:** {first.get(c['session'], 'Not available')}")
                if c["mobile"] in df:
                    p3.markdown(f"**Mobile:** {first.get(c['mobile'], 'Not available')} 🔒")
                    p3.caption("Visible to authorized staff only.")

                st.divider()

                # ---------------- Summary dashboard ----------------
                st.subheader("Placement Summary")
                s = summarize(student_df)

                def metric_card(label, value):
                    st.markdown(
                        f"""<div class="metric-card">
                                <div class="metric-label">{label}</div>
                                <div class="metric-value">{value}</div>
                            </div>""",
                        unsafe_allow_html=True,
                    )

                row1 = st.columns(4)
                with row1[0]: metric_card("Total Applications", s["total_applications"])
                with row1[1]: metric_card("Unique Companies", s["unique_companies"])
                with row1[2]: metric_card("Eligible Applications", s["eligible"])
                with row1[3]: metric_card("Not-Eligible Applications", s["not_eligible"])

                row2 = st.columns(4)
                with row2[0]: metric_card("Appeared", s["appeared"])
                with row2[1]: metric_card("Not Appeared", s["not_appeared"])
                with row2[2]: metric_card("Selected", s["selected"])
                with row2[3]: metric_card("Rejected", s["rejected"])

                row3 = st.columns(4)
                with row3[0]: metric_card("Pending Outcome", s["pending"])

                with st.expander("ℹ️ How these numbers are calculated"):
                    st.markdown(
                        """
- **Total Applications** = one row in the workbook = one application (a student applying to two roles at the same company counts as 2 applications).
- **Unique Companies** = distinct companies in those applications (the same example above counts as 1 company).
- **Eligible / Not-Eligible** come straight from the `Eligible` column, normalised (any value starting with "NE" or containing "Not Eligible" = Not Eligible; exactly "E" = Eligible).
- **Appeared / Not Appeared** come from the `A` (appearance) column. A "No show" recorded in the `S` column is also treated as Not Appeared.
- **Selected / Rejected** are only ever counted for applications that were **Eligible AND Appeared** - so a not-eligible application, or one the student never appeared for, is *never* counted as a "Rejected" interview outcome.
- **Pending** = eligible applications where the interview/selection round hasn't happened yet or no result has been recorded.
                        """
                    )

                st.divider()

                # ---------------- Company-wise history table ----------------
                st.subheader("Company-wise Application History")

                display_cols_map = {
                    "Company Name": c["company"],
                    "Domain": c["domain"],
                    "Designation": c["designation"],
                    "Job Type": "Job Type (Clean)",
                    "Eligibility Status": "Eligibility Status",
                    "JD Attendance Status": "JD Attendance Status",
                    "Appeared Status": "Appeared Status",
                    "Final Status": "Final Status",
                    "Compensation": "Compensation",
                    "Feedback": c["feedback"],
                    "Application Date (DOP)": c["dop"],
                    "Response Deadline (LOR)": c["lor"],
                }
                avail = {k: v for k, v in display_cols_map.items() if v in student_df.columns}
                table = student_df[list(avail.values())].copy()
                table.columns = list(avail.keys())

                fcol1, fcol2, fcol3, fcol4 = st.columns(4)
                with fcol1:
                    company_filter = st.multiselect(
                        "Filter by company", sorted(table["Company Name"].dropna().unique())
                    ) if "Company Name" in table else []
                with fcol2:
                    elig_filter = st.multiselect(
                        "Filter by eligibility", sorted(table["Eligibility Status"].dropna().unique())
                    ) if "Eligibility Status" in table else []
                with fcol3:
                    appeared_filter = st.multiselect(
                        "Filter by appeared", sorted(table["Appeared Status"].dropna().unique())
                    ) if "Appeared Status" in table else []
                with fcol4:
                    status_filter = st.multiselect(
                        "Filter by outcome", sorted(table["Final Status"].dropna().unique())
                    ) if "Final Status" in table else []

                search_text = st.text_input("🔎 Search within this student's applications (company, designation, feedback...)")

                filtered = table.copy()
                if company_filter:
                    filtered = filtered[filtered["Company Name"].isin(company_filter)]
                if elig_filter:
                    filtered = filtered[filtered["Eligibility Status"].isin(elig_filter)]
                if appeared_filter:
                    filtered = filtered[filtered["Appeared Status"].isin(appeared_filter)]
                if status_filter:
                    filtered = filtered[filtered["Final Status"].isin(status_filter)]
                if search_text.strip():
                    mask = filtered.astype(str).apply(
                        lambda col: col.str.contains(search_text, case=False, na=False)
                    ).any(axis=1)
                    filtered = filtered[mask]

                st.dataframe(filtered, use_container_width=True, hide_index=True)

                dl1, dl2, dl3 = st.columns(3)
                with dl1:
                    st.download_button(
                        "⬇️ Download filtered results (CSV)",
                        data=to_csv_bytes(filtered),
                        file_name=f"{first.get(c['name'], 'student')}_applications.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with dl2:
                    st.download_button(
                        "⬇️ Download filtered results (Excel)",
                        data=to_excel_bytes({"Applications": filtered}),
                        file_name=f"{first.get(c['name'], 'student')}_applications.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                with dl3:
                    report_sheets = {
                        "Profile": pd.DataFrame([{
                            "Name": first.get(c["name"]),
                            "Email": first.get(c["email"]),
                            "Enrollment No.": first.get(c["enrollment_no"]) if c["enrollment_no"] in df else None,
                            "Program": first.get(c["program"]) if c["program"] in df else None,
                            "Specialisation": first.get(c["specialisation"]) if c["specialisation"] in df else None,
                        }]),
                        "Summary": pd.DataFrame([s]),
                        "Applications": table,
                    }
                    st.download_button(
                        "📄 Export full student report (Excel)",
                        data=to_excel_bytes(report_sheets),
                        file_name=f"{first.get(c['name'], 'student')}_placement_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

                st.divider()

                # ---------------- Company-wise statistics ----------------
                st.subheader("Company-wise Statistics")
                if "Company Name" in table:
                    company_stats = (
                        student_df.groupby(c["company"])
                        .agg(
                            Applications=(c["company"], "count"),
                            Selected=("Final Status", lambda s: (s == "Selected").sum()),
                            Rejected=("Final Status", lambda s: (s == "Rejected").sum()),
                            Pending=("Final Status", lambda s: (s == "Pending").sum()),
                            Not_Eligible=("Final Status", lambda s: (s == "Not Eligible").sum()),
                            Not_Appeared=("Final Status", lambda s: (s == "Not Appeared").sum()),
                        )
                        .reset_index()
                        .rename(columns={c["company"]: "Company", "Not_Eligible": "Not Eligible", "Not_Appeared": "Not Appeared"})
                        .sort_values("Applications", ascending=False)
                    )
                    st.dataframe(company_stats, use_container_width=True, hide_index=True)

                st.divider()

                # ---------------- Timeline ----------------
                st.subheader("Application Timeline")
                st.caption(
                    "Built only from dates recorded in the workbook: **DOP** (application/posting date) "
                    "and **LOR** (response deadline). No events or dates are invented."
                )
                if c["dop"] in student_df.columns:
                    timeline = student_df[[c["company"], c["dop"], c["lor"], "Final Status"]].copy() \
                        if c["lor"] in student_df.columns else student_df[[c["company"], c["dop"], "Final Status"]].copy()
                    timeline = timeline.sort_values(c["dop"])
                    for _, row in timeline.iterrows():
                        dop = row[c["dop"]]
                        lor = row[c["lor"]] if c["lor"] in timeline.columns else None
                        dop_str = dop.strftime("%d %b %Y") if pd.notna(dop) else "Unknown date"
                        lor_str = f" → response due {lor.strftime('%d %b %Y')}" if pd.notna(lor) else ""
                        st.markdown(f"- **{dop_str}**{lor_str} — {row[c['company']]} · `{row['Final Status']}`")
                else:
                    st.info("No date columns (DOP) available in this workbook to build a timeline.")

# ========================================================================
# PAGE: Data Quality
# ========================================================================
elif page == "🧹 Data Quality":
    st.title("🧹 Data Quality")
    st.caption(
        "These checks flag potential issues for review. The original workbook is never modified — "
        "use this list to go clean up records at the source if needed."
    )

    issues = data_quality_report(df)

    tabs = st.tabs([
        f"Potential Duplicates ({len(issues['potential_duplicates'])})",
        f"Missing Email ({len(issues.get('missing_email', []))})",
        f"Missing Company ({len(issues.get('missing_company', []))})",
        f"Unknown Eligibility ({len(issues['unknown_eligibility'])})",
        f"Inconsistent Records ({len(issues['inconsistent_not_eligible'])})",
    ])

    with tabs[0]:
        st.caption("Same student + same company (+ designation, if available) appearing more than once.")
        st.dataframe(issues["potential_duplicates"], use_container_width=True, hide_index=True)
    with tabs[1]:
        st.dataframe(issues.get("missing_email", pd.DataFrame()), use_container_width=True, hide_index=True)
    with tabs[2]:
        st.dataframe(issues.get("missing_company", pd.DataFrame()), use_container_width=True, hide_index=True)
    with tabs[3]:
        st.caption("Rows where the `Eligible` column was blank or didn't match a recognised pattern.")
        st.dataframe(issues["unknown_eligibility"], use_container_width=True, hide_index=True)
    with tabs[4]:
        st.caption("Marked Not Eligible but also shows an 'Appeared' outcome — worth a manual check.")
        st.dataframe(issues["inconsistent_not_eligible"], use_container_width=True, hide_index=True)

# ========================================================================
# PAGE: Admin Analytics
# ========================================================================
elif page == "📊 Admin Analytics":
    st.title("📊 Admin Analytics")
    st.caption("Workbook-wide statistics across all students. Unique students and application records are counted separately.")

    total_students = df["_email_key"].replace("", pd.NA).nunique()
    total_applications = len(df)
    total_companies = df["_company_key"].replace("", pd.NA).nunique()

    row1 = st.columns(4)
    row1[0].metric("Unique Students", total_students)
    row1[1].metric("Total Applications", total_applications)
    row1[2].metric("Unique Companies", total_companies)
    row1[3].metric(
        "Avg. Applications / Student",
        round(total_applications / total_students, 1) if total_students else 0,
    )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Eligibility Breakdown")
        st.bar_chart(df["Eligibility Status"].value_counts())
    with col2:
        st.subheader("Final Outcome Breakdown")
        st.bar_chart(df["Final Status"].value_counts())

    st.divider()
    st.subheader("Top 15 Companies by Applications")
    top_companies = (
        df.groupby(COLUMNS["company"]).size().sort_values(ascending=False).head(15)
    )
    st.bar_chart(top_companies)

    if COLUMNS["program"] in df:
        st.divider()
        st.subheader("Applications by Program")
        st.bar_chart(df[COLUMNS["program"]].value_counts())

# ========================================================================
# PAGE: Upload / Refresh Data
# ========================================================================
elif page == "⬆️ Upload / Refresh Data":
    st.title("⬆️ Upload / Refresh Data")
    st.caption(
        "Upload the latest `Total_Data.xlsx` to load it into the app for this session. "
        "The file is kept in memory for this session only and is not written to disk by the app."
    )

    uploaded = st.file_uploader("Choose an Excel workbook (.xlsx)", type=["xlsx"])
    if uploaded is not None:
        st.session_state["workbook_bytes"] = uploaded.read()
        st.success("Workbook loaded. Switch to **Student Search** to use the new data.")
        st.rerun()

    st.divider()
    st.markdown(
        f"**Currently loaded sheet:** `{result.sheet_used}`  \n"
        f"**Total records:** {len(df)}  \n"
        f"**Sheets found in workbook:** {', '.join(result.sheets_available)}"
    )
