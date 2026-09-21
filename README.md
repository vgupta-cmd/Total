# Student Placement Tracker

A Streamlit web app for the Univo Career Services team to look up a student
by email and see their complete LineupX placement application history —
profile, summary dashboard, company-wise history table, timeline, and
data-quality checks.

---

## 1. What's in your workbook (`Total_Data.xlsx`)

The app was built by directly inspecting your uploaded file. It has **one
sheet ("Sheet1")** with **9,452 rows** and these columns (the app strips
trailing spaces from headers like `"Designation "` automatically):

| Column | What it is | Used for |
|---|---|---|
| `S.no` | Row number | — |
| `Enrollment Number` | Student enrollment ID | Profile |
| `Name` | Student name | Profile |
| `Email id` | Student email (mostly `@amityonline.com`, some `@gmail.com`) | **Search key** |
| `Mobile` | Phone number | Profile (staff-only) |
| `Program` | Degree program | Profile |
| `Session` | Batch/session | Profile |
| `Specialisation` | Specialisation (often blank) | Profile |
| `DOP` | Date — used as the **application/posting date** | Timeline |
| `LOR` | Date — used as the **response deadline** | Timeline |
| `Company Name` | Employer | History table |
| `Domain` | Industry/sector | History table |
| `Designation` | Job title applied for | History table |
| `Job Type` | `I` (Internship) / `P` (Placement) / `I+P` (Internship+PPO) | History table |
| `Stipend` / `Salary` | Compensation figures | History table (combined as "Compensation") |
| `Eligible` | Eligibility for the role (`E`, `NE`, `NE-Location`, `NE - Education`, `Not Eligible`, ...) | Summary + filters |
| `A-JD` | JD-round attendance (`A-JD`, `NA-A-JD`, `NS`, ...) | Summary + filters |
| `A` | Interview/PI appearance (`A-PI`, `NA-A-PI`, `A-NA`, `NS`, `Not appeared`) | Summary + filters |
| `S` | Final selection outcome (`S`, `Rej`, `NS`, `No show`, `Not selected`, ...) | Summary + filters |
| `Feedback` | Free-text notes (`N-S`, `Rejected`, `Approved`, ...) | History table (shown as-is) |

**None of the original columns are ever modified.** Every status shown in
the app is a *new, derived* column (e.g. "Eligibility Status") computed
from the raw text — see section 3 below for the exact rules.

---

## 2. Project structure

```
student_placement_tracker/
├── app.py                        # Main Streamlit app (all 4 pages)
├── config.py                     # Column mapping + app settings (edit here if headers change)
├── auth.py                       # Simple staff password gate
├── data_loader.py                # Reads & validates the Excel workbook
├── data_processing.py            # Status normalisation + summary calculations
├── utils.py                      # Excel/CSV export helpers
├── requirements.txt
├── .gitignore                    # Keeps real student data & secrets out of git
├── .streamlit/
│   ├── config.toml               # App theme
│   └── secrets.toml.example      # Template for an alternative password method
└── data/                         # (you create this) put Total_Data.xlsx here, OR upload in-app
```

---

## 3. How application counts are calculated

This was the trickiest part of your data, so here are the exact rules used
(see `data_processing.py` for the code):

1. **Eligibility Status** — from the `Eligible` column: exactly `E` →
   *Eligible*; anything starting with `NE` or containing "not eligible"
   (any casing/spacing) → *Not Eligible*; blank/unrecognised → *Unknown*
   (flagged in Data Quality, not guessed at).
2. **Appeared Status** — from the `A` column: any value containing "NA"
   (e.g. `NA-A-PI`, `A-NA`) or the phrase "not appeared" → *Not Appeared*;
   `NS`-prefixed → *Not Scheduled*; `A-PI` → *Appeared*.
3. **Final Status** (the single "what happened" field) combines the two
   above with the `S` column, in this order:
   - Not Eligible → **`Not Eligible`** — *never* counted as an interview
     rejection, per your instructions.
   - `S` = "No show" → **`Not Appeared`** (overrides everything else).
   - Not Appeared → **`Not Appeared`** — *never* counted as "Rejected".
   - Appeared not yet recorded / not scheduled → **`Pending`**.
   - Appeared, and `S` says selected (`S`, `S-1`, "Selected") →
     **`Selected`**.
   - Appeared, and `S` says rejected (`Rej`, "Not selected", "profile
     rejected by HR", "poor communication", ...) → **`Rejected`**.
   - Appeared, but `S` is blank / `NS` / unrecognised → **`Pending`**
     (result not recorded yet — *not* assumed to be a rejection).

**Applications vs. unique companies:** every row is one application.
`Unique Companies` counts distinct company names (trimmed/lowercased for
comparison) — so 2 applications to the same company = 2 applications, 1
unique company, exactly as you asked.

**Duplicates:** rows are never silently merged or deleted. The Data
Quality page lists rows that share the same student + company (+
designation) so staff can review them manually.

### A genuine ambiguity — please review

The `S` column also contains the raw value `NS`, and the `A-JD` column
contains values like `NS - AJD`. It isn't 100% certain from the data alone
whether `NS` means "Not Scheduled", "Not Selected", or something else
specific to your process. The app currently treats `NS` as **"Not
Scheduled / Pending"** (i.e., not yet counted as a rejection), which is
the safer interpretation given your instruction not to invent rejections.
If `NS` actually means something more specific in your process, update
`_classify_selection_raw()` in `data_processing.py` accordingly.

---

## 4. Assumptions & limitations

- **"Gmail search"** in your brief is implemented as a search on the
  `Email id` column generally — most emails in the workbook are actually
  `@amityonline.com`, with a handful of `@gmail.com`/`@yahoo.com`. The
  search works the same for any of them.
- **`DOP`/`LOR`** are treated as "application/posting date" and "response
  deadline" respectively, based on the data pattern (`DOP` is always ≤
  `LOR`). These are the only two dates in the workbook, so the timeline
  cannot show separate dates for "attended interview" or "offer given" —
  it shows outcome status alongside these two dates instead. No dates or
  events are invented.
- The workbook has a **single sheet**. The loader is written to scan all
  sheets and pick the one that best matches the expected columns, so it
  will keep working if a future version of the file has multiple sheets.
- **762 rows** are recorded as `Selected` workbook-wide; this comes
  directly from the `S` column values `S`, `S-1`, `s` — the workbook does
  not have a separate "offer accepted / joined" field, so "Selected" means
  "selection outcome recorded," not necessarily "joined the company."

---

## 5. Privacy & security

- The app requires a **staff password** (`auth.py`) before any data is
  shown. This is a single shared password suitable only for a **trusted,
  local prototype** — it is **not** real user-level authentication.
- Individual student records are only ever shown one at a time, after an
  exact/normalised email match — there is no page that lists or exports
  the entire student database at once.
- Mobile number / enrollment number are shown only on the individual
  student profile (never in aggregate tables), marked 🔒.
- Uploaded workbooks are kept **in memory for the browser session only**
  — the app does not write uploaded files to disk.
- No real student data is included in this codebase or in any example
  file.

### Before using this beyond a trusted local prototype, you should add:

1. **Real per-user authentication** (e.g. your institution's SSO/SAML/OAuth
   via `streamlit-authenticator` or a reverse-proxy auth layer), not a
   single shared password.
2. **HTTPS** — deploy behind a proper TLS-terminating reverse proxy
   (nginx, Streamlit Community Cloud, or your institution's app hosting).
3. **Access logging/audit trail** — who searched which student and when.
4. **Role-based access** (e.g. read-only staff vs. admins who see the
   Admin Analytics page).
5. **A managed database** instead of an Excel file, once record volume or
   concurrent-editor needs grow beyond what a single workbook can handle
   safely.
6. Store the staff password as a **secret**, never in code — this
   prototype already reads it from an environment variable
   (`STAFF_PASSWORD`); see `.streamlit/secrets.toml.example` for an
   alternative using Streamlit's built-in secrets manager.

### Running the local prototype securely

- Run it only on a machine you trust, on your local network — do **not**
  port-forward it to the public internet as-is.
- Set a real `STAFF_PASSWORD` (see below) before sharing it with
  colleagues, and don't reuse a password used elsewhere.
- Keep `Total_Data.xlsx` in the `data/` folder, which is already excluded
  from git via `.gitignore`.

---

## 6. Installation (Windows)

1. Install **Python 3.10+** from [python.org](https://python.org) if you
   don't have it (check "Add Python to PATH" during install).
2. Open **Command Prompt** and go to the project folder:
   ```
   cd path\to\student_placement_tracker
   ```
3. (Recommended) create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## 7. Running the app (Windows)

1. Set your staff password for this session:
   ```
   set STAFF_PASSWORD=choose-a-strong-password
   ```
   (PowerShell: `$env:STAFF_PASSWORD="choose-a-strong-password"`)
2. Start the app:
   ```
   streamlit run app.py
   ```
3. Your browser will open automatically at `http://localhost:8501`. Log in
   with the password you set above.

## 8. Loading / replacing your workbook

You have two options:

- **In-app upload (recommended):** go to the **⬆️ Upload / Refresh Data**
  page in the sidebar and choose your `.xlsx` file. It loads instantly and
  stays loaded for the rest of your browser session.
- **Default file:** create a `data` folder in the project directory and
  place `Total_Data.xlsx` inside it (`data/Total_Data.xlsx`). It will load
  automatically each time you start the app. To refresh with an updated
  workbook, replace the file and restart the app (or just use the in-app
  upload instead — no restart needed).

---

## 9. Future improvements

- Real SSO-based authentication and per-staff audit logs.
- A dedicated "offer accepted / joined" outcome if that data becomes
  available, distinct from "Selected."
- Automatic email alerts to staff when a student's application status
  changes (would need a live data source rather than a static workbook).
- A proper database backend (e.g. PostgreSQL) to support multiple staff
  editing data concurrently.
- PDF export of the individual student report, in addition to the current
  Excel export.
