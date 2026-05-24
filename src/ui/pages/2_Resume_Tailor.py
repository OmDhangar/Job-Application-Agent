"""
src/ui/pages/2_Resume_Tailor.py

Resume Tailoring page. Calls the FastAPI backend, displays scored results.
Decoupled: UI knows nothing about AI logic — all calls go through the API.
"""
import httpx
import streamlit as st

API_BASE = "http://localhost:8000/api/v1"

st.title("📄 AI Resume Tailoring")
st.caption("Identity-preserving, ATS-optimized, recruiter-grade tailoring")

# ─── Inputs ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Inputs")
    resume_file = st.file_uploader("Upload your résumé", type=["pdf", "docx"])
    job_desc = st.text_area("Paste job description", height=250)
    candidate_email = st.text_input("Your email (to save results)")
    run_btn = st.button("🚀 Generate Tailored Résumé", type="primary", use_container_width=True)

if not run_btn:
    st.info("Upload your résumé and paste a job description to begin.")
    st.stop()

if not resume_file or not job_desc.strip():
    st.error("Both résumé and job description are required.")
    st.stop()

# ─── Call API ─────────────────────────────────────────────────────────────────
with st.spinner("Running tailoring pipeline (local analysis → strategy → Gemini tailoring → critique)..."):
    try:
        resp = httpx.post(
            f"{API_BASE}/tailoring/run",
            files={"resume": (resume_file.name, resume_file.read(), "application/octet-stream")},
            data={"job_description": job_desc, "candidate_email": candidate_email},
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
    except httpx.ConnectError:
        st.error("Cannot connect to API. Is `uvicorn src.api.main:app` running?")
        st.stop()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

# ─── Scores ───────────────────────────────────────────────────────────────────
scores = result.get("scores", {})
st.success("✅ Tailoring complete")

col1, col2, col3, col4 = st.columns(4)
col1.metric("ATS Score",           f"{scores.get('ats_score', 0):.0f}/100")
col2.metric("Authenticity",        f"{scores.get('authenticity_score', 0):.0f}/100")
col3.metric("Recruiter Readability", f"{scores.get('recruiter_readability', 0):.0f}/100")
col4.metric("Interview Probability", f"{scores.get('interview_probability', 0):.0f}%")

st.markdown("---")

# ─── Audit flags ──────────────────────────────────────────────────────────────
audit = result.get("audit", {})
if not audit.get("passed"):
    with st.expander("⚠️ Identity Audit Flags", expanded=True):
        for issue in audit.get("issues", []):
            st.warning(issue)
else:
    st.success("✅ Identity audit passed — no fabrication detected")

# ─── Strategy ─────────────────────────────────────────────────────────────────
strategy = result.get("strategy", {})
if strategy:
    with st.expander("📋 Tailoring Strategy"):
        st.markdown(f"**Role type detected:** `{strategy.get('target_role_type', '—')}`")
        st.markdown(f"**Leads with:** {', '.join(strategy.get('primary_emphasis', []))}")
        st.markdown(f"**ATS keywords used:** {', '.join(strategy.get('ats_keywords', []))}")

# ─── Tailored resume ──────────────────────────────────────────────────────────
st.subheader("📄 Tailored Résumé")
tailored = result.get("tailored_resume", "")
st.markdown(tailored)

col_a, col_b = st.columns(2)
col_a.download_button("📥 Download as Markdown", tailored, "tailored_resume.md", "text/markdown")
col_b.download_button("📥 Download as Text",     tailored, "tailored_resume.txt", "text/plain")

# ─── Recruiter critique ───────────────────────────────────────────────────────
critique = result.get("critique", "")
if critique:
    with st.expander("🎯 Recruiter Critique"):
        st.markdown(critique)
