"""
auth.py
-------
Minimal password gate for the local prototype.

IMPORTANT: this is intentionally simple (one shared password) so the
prototype can be reviewed quickly. It is NOT sufficient for a real
deployment - see README.md, section "Security & production
deployment" for what to add (per-user accounts / SSO, HTTPS, audit
logging, etc.) before this handles real student data outside a
trusted local machine.
"""

import streamlit as st
from config import STAFF_PASSWORD


def require_login():
    """Blocks the rest of the app from rendering until the correct
    staff password has been entered in this browser session."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown("## 🔒 Career Services Staff Login")
    st.caption(
        "This tool contains student placement records. Access is restricted "
        "to authorized Career Services staff only."
    )

    with st.form("login_form", clear_on_submit=False):
        pwd = st.text_input("Staff password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        if pwd == STAFF_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

    st.stop()
