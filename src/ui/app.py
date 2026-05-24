"""
src/ui/app.py  —  Streamlit multi-page entry point.
Run: streamlit run src/ui/app.py
"""
import streamlit as st

st.set_page_config(
    page_title="Job Acquisition OS",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.markdown("## 🎯 Job Acquisition OS")
    st.markdown("---")
    st.page_link("pages/1_Job_Discovery.py",  label="🔍 Job Discovery")
    st.page_link("pages/2_Resume_Tailor.py",  label="📄 Resume Tailoring")
    st.page_link("pages/3_Cold_Email.py",     label="✉️  Cold Outreach")
    st.page_link("pages/4_Applications.py",   label="📊 Applications")
    st.markdown("---")
    st.caption("Local AI + Gemini · pdflatex · pgvector")

st.title("🎯 Job Acquisition Operating System")
st.markdown(
    "> *Maximum intelligence, minimum API cost.*"
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Jobs in DB",          "—")
col2.metric("Applications",        "—")
col3.metric("Avg ATS Score",       "—")
col4.metric("Interview Probability","—")

st.markdown("---")
st.markdown("""
| Module | Description |
|--------|-------------|
| 🔍 **Job Discovery** | Semantic search across 10+ sources — ranked by composite score |
| 📄 **Resume Tailoring** | LaTeX / Markdown tailoring with identity preservation + PDF compile |
| ✉️ **Cold Outreach** | 120-word personalised emails that don't sound like cold emails |
| 📊 **Applications** | Full lifecycle tracking with funnel analytics |
""")