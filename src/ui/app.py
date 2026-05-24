"""
src/ui/app.py

Streamlit MVP — Job Acquisition OS
Multi-page app. Each page is a separate concern.
"""
import streamlit as st

st.set_page_config(
    page_title="Job Acquisition OS",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar navigation
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=Job+OS", use_column_width=True)
    st.markdown("---")
    st.markdown("### Navigation")
    st.page_link("pages/1_Job_Discovery.py",  label="🔍 Job Discovery",     icon="🔍")
    st.page_link("pages/2_Resume_Tailor.py",  label="📄 Resume Tailoring",  icon="📄")
    st.page_link("pages/3_Cold_Email.py",     label="✉️ Cold Email",        icon="✉️")
    st.page_link("pages/4_Applications.py",   label="📊 Applications",      icon="📊")
    st.markdown("---")
    st.caption("Powered by local AI + Gemini")

# Home page
st.title("🎯 Job Acquisition Operating System")
st.markdown("""
Your AI-powered job search command center.

| Module | What it does |
|--------|-------------|
| 🔍 **Job Discovery** | Scrape and rank opportunities from 10+ sources |
| 📄 **Resume Tailoring** | AI-strategic tailoring with identity preservation |
| ✉️ **Cold Email** | Deeply personalized outreach generation |
| 📊 **Applications** | Track every application, reply, and interview |
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Jobs Discovered", "—", help="Total jobs in database")
with col2:
    st.metric("Applications", "—", help="Active applications")
with col3:
    st.metric("Avg Interview Probability", "—", help="Across tailored resumes")
