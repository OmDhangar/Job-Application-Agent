"""
src/ui/pages/2_Resume_Tailor.py

Resume tailoring page with full LaTeX support:
  • Upload .tex / .pdf / .docx
  • Choose output format (LaTeX or Markdown)
  • View tailored resume inline
  • Download .tex and compiled .pdf
  • View scores, audit flags, strategy, and recruiter critique
"""
from __future__ import annotations

import io
import httpx
import streamlit as st

API = "http://localhost:8000/api/v1"

st.title("📄 AI Resume Tailoring")
st.caption(
    "Identity-preserving · ATS-optimized · LaTeX-native · "
    "2 Gemini calls total (tailoring + critique)"
)

# ── Sidebar inputs ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Inputs")

    resume_file = st.file_uploader(
        "Upload résumé",
        type=["pdf", "docx", "tex"],
        help=".tex gives best results — structure is preserved exactly",
    )

    output_fmt = st.radio(
        "Output format",
        ["latex", "markdown"],
        index=0,
        help="LaTeX → also compiles to PDF automatically",
    )

    job_desc = st.text_area(
        "Paste job description",
        height=280,
        placeholder="Copy the full JD here — the more detail, the better the tailoring",
    )

    candidate_email = st.text_input("Email (optional, to save results)")

    run_btn = st.button(
        "🚀 Tailor Resume",
        type="primary",
        use_container_width=True,
        disabled=not (resume_file and job_desc.strip()),
    )

# ── Guard ─────────────────────────────────────────────────────────────────────
if not run_btn:
    st.info("Upload your résumé and paste a JD in the sidebar to begin.")
    with st.expander("💡 Tips for best results"):
        st.markdown("""
- **Upload the `.tex` source** of your resume for structure-preserving tailoring.
  The system will reorder bullets and projects without breaking your LaTeX.
- **Paste the complete JD** — not just the title. Requirements and responsibilities
  drive the strategy generation.
- **LaTeX output** compiles automatically with pdflatex — you get both the
  editable `.tex` and the final `.pdf` in one click.
- The system **never fabricates** skills or companies — it only reframes what's real.
        """)
    st.stop()

# ── Call API ──────────────────────────────────────────────────────────────────
file_bytes = resume_file.read()
filename   = resume_file.name

with st.spinner(
    "Running pipeline: parse → identity extract → JD analyse → strategy → "
    "Gemini tailor → audit → Gemini critique → score"
    + (" → pdflatex compile" if output_fmt == "latex" else "")
    + "..."
):
    try:
        resp = httpx.post(
            f"{API}/tailoring/run",
            files={"resume": (filename, file_bytes, "application/octet-stream")},
            data={
                "job_description":  job_desc,
                "output_format":    output_fmt,
                "candidate_email":  candidate_email,
            },
            timeout=180,
        )
        resp.raise_for_status()
        result = resp.json()
    except httpx.ConnectError:
        st.error("Cannot connect to API. Start it with: `uvicorn src.api.main:app --reload`")
        st.stop()
    except httpx.HTTPStatusError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text[:300]}")
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.stop()

# ── Scores row ────────────────────────────────────────────────────────────────
st.success("✅ Tailoring complete")
scores = result.get("scores", {})

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("ATS Score",            f"{scores.get('ats_score', 0):.0f}/100")
col2.metric("Authenticity",         f"{scores.get('authenticity_score', 0):.0f}/100")
col3.metric("Readability",          f"{scores.get('recruiter_readability', 0):.0f}/100")
col4.metric("Credibility",          f"{scores.get('technical_credibility', 0):.0f}/100")
col5.metric("Interview Probability",f"{scores.get('interview_probability', 0):.0f}%")

# ── Identity audit ────────────────────────────────────────────────────────────
audit = result.get("audit", {})
if audit.get("passed"):
    st.success("🛡️ Identity audit passed — no fabrication detected")
else:
    with st.expander(
        f"⚠️ Identity Audit — {len(audit.get('issues', []))} issue(s) detected",
        expanded=True,
    ):
        severity_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        sev = audit.get("severity", "low")
        st.markdown(f"**Severity:** {severity_color.get(sev, '⚪')} {sev.upper()}")
        for issue in audit.get("issues", []):
            if "FABRICATED" in issue:
                st.error(issue)
            elif "STUFFING" in issue:
                st.warning(issue)
            else:
                st.info(issue)

st.markdown("---")

# ── Strategy panel ────────────────────────────────────────────────────────────
strategy = result.get("strategy", {})
if strategy:
    with st.expander("📋 Tailoring Strategy Applied"):
        c1, c2 = st.columns(2)
        c1.markdown(f"**Role type detected:** `{strategy.get('target_role_type', '—')}`")
        c2.markdown(f"**ATS keywords used:** {', '.join(strategy.get('ats_keywords', []))}")
        if strategy.get("primary_emphasis"):
            st.markdown(f"**Led with:** {', '.join(strategy['primary_emphasis'])}")
        if strategy.get("compress"):
            st.markdown(f"**Compressed:** {', '.join(strategy['compress'])}")
        st.markdown(f"**Bullet verbs:** {', '.join(strategy.get('bullet_focus', []))}")
        st.caption(strategy.get("authenticity_notes", ""))

# ── Tailored resume ───────────────────────────────────────────────────────────
tailored = result.get("tailored_resume", "")
st.subheader("📄 Tailored Résumé")

if output_fmt == "latex":
    # Show raw LaTeX in a code block + download buttons
    tab_src, tab_preview = st.tabs(["LaTeX Source", "Plain Text Preview"])

    with tab_src:
        st.code(tailored, language="latex", line_numbers=True)

    with tab_preview:
        # Rough plain-text render for quick scan
        import re
        plain = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", tailored)
        plain = re.sub(r"\\[a-zA-Z]+|[{}%]", " ", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        st.text_area("Plain text (approximate)", plain, height=400)

    st.markdown("#### Downloads")
    dl1, dl2, dl3 = st.columns(3)

    # .tex download — always available
    dl1.download_button(
        "📥 Download .tex",
        data=tailored.encode("utf-8"),
        file_name="tailored_resume.tex",
        mime="application/x-tex",
        use_container_width=True,
    )

    # PDF — compile on demand via /compile-pdf endpoint
    if dl2.button("📥 Compile & Download PDF", use_container_width=True):
        with st.spinner("Compiling PDF with pdflatex..."):
            try:
                pdf_resp = httpx.post(
                    f"{API}/tailoring/compile-pdf",
                    data={"latex_source": tailored},
                    timeout=60,
                )
                if pdf_resp.status_code == 200:
                    st.download_button(
                        "⬇️ Save PDF",
                        data=pdf_resp.content,
                        file_name="tailored_resume.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                else:
                    st.error(f"Compile failed: {pdf_resp.text[:200]}")
            except Exception as e:
                st.error(f"Compile error: {e}")

    # .txt download
    dl3.download_button(
        "📥 Download .txt",
        data=plain,
        file_name="tailored_resume.txt",
        mime="text/plain",
        use_container_width=True,
    )

else:
    # Markdown output
    st.markdown(tailored)
    c1, c2 = st.columns(2)
    c1.download_button("📥 Download .md", tailored, "tailored_resume.md", "text/markdown")
    c2.download_button("📥 Download .txt", tailored, "tailored_resume.txt", "text/plain")

# ── Recruiter critique ────────────────────────────────────────────────────────
critique = result.get("critique", "")
if critique:
    with st.expander("🎯 Recruiter Critique"):
        st.markdown(critique)