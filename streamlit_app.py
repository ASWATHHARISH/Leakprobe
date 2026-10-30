"""Streamlit entry point for the LeakProbe - Water Leak Detection System."""
import streamlit as st

from leakprobe.ui.pages import (
    render_about,
    render_benchmarks,
    render_llm_run_history,
)
from leakprobe.ui.employee_dashboard import render_monitoring_dashboard
from leakprobe.ui.monitoring import render_evaluation_replay
from leakprobe.ui.outcomes import render_outcome_review, render_reference_outcomes

st.set_page_config(
    page_title="LeakProbe",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("LeakProbe")
st.sidebar.caption("AI-Assisted Water Leak Monitoring & Investigation")
st.sidebar.caption("Employee monitoring desk")
st.sidebar.caption("92 pressure + 117 flow channels")
st.sidebar.caption("Automatic assessment · employee verification")

page = st.navigation(
    {
        "Operations": [
            st.Page(render_monitoring_dashboard, title="Monitoring", icon="💧", default=True),
            st.Page(render_outcome_review, title="History & outcomes", icon=":material/history:"),
        ],
        "Administration": [
            st.Page(render_evaluation_replay, title="Window replay", icon=":material/tune:"),
            st.Page(render_reference_outcomes, title="Reference outcomes", icon=":material/fact_check:"),
            st.Page(render_llm_run_history, title="Investigation history", icon="🧠"),
            st.Page(render_benchmarks, title="Model validation", icon=":material/monitoring:"),
            st.Page(render_about, title="About", icon=":material/info:"),
        ],
    },
    position="sidebar",
)
page.run()
