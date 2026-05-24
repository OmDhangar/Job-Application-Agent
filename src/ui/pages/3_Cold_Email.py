"""
src/ui/pages/3_Cold_Email.py  —  Cold outreach generation.
"""
import httpx
import streamlit as st

API = "http://localhost:8000/api/v1"

st.title("✉️ Cold Outreach Generator")
st.caption("Specific, human-sounding emails — not templates")

with st.sidebar:
    st.header("Outreach Details")
    company_name   = st.text_input("Company name")
    company_domain = st.text_input("Company domain", placeholder="company.com")
    job_title      = st.text_input("Role you're targeting")
    tech_stack     = st.text_input("Their tech stack (comma-sep)", placeholder="Python, Kafka, Postgres")
    recent_news    = st.text_area("Recent company news / blog post", height=80,
                                  placeholder="e.g. They just raised Series B and are expanding their data platform...")
    cand_summary   = st.text_area("Your 2-sentence summary", height=80,
                                  placeholder="Senior backend engineer, 4yr exp in distributed systems and ML pipelines...")
    gen_btn = st.button("✉️ Generate Email", type="primary", use_container_width=True,
                        disabled=not (company_name and job_title and cand_summary))

if not gen_btn:
    st.info("Fill in the details in the sidebar to generate a personalised email.")
    with st.expander("What makes a good cold email?"):
        st.markdown("""
- **Specific, not generic** — reference something real about the company
- **Short** — 100-120 words maximum. Recruiters don't read walls of text.
- **One clear ask** — "15-minute call?" not "I'd love to explore opportunities"
- **No templates** — "I hope this finds you well" is immediately deleted
        """)
    st.stop()

stack_list = [s.strip() for s in tech_stack.split(",") if s.strip()]
with st.spinner("Generating personalised email..."):
    try:
        r = httpx.post(
            f"{API}/outreach/generate",
            params={
                "application_id": "00000000-0000-0000-0000-000000000001",
                "company_name":   company_name,
                "company_domain": company_domain or f"{company_name.lower()}.com",
                "job_title":      job_title,
                "candidate_summary": cand_summary,
                "recent_news":    recent_news or None,
            },
            json={"tech_stack": stack_list},
            timeout=60,
        )
        r.raise_for_status()
        email = r.json()
    except httpx.ConnectError:
        st.error("Cannot reach API.")
        st.stop()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

st.success("✅ Email generated")
st.markdown(f"**Subject:** {email['subject']}")
st.markdown("---")
st.text_area("Email body", email["body"], height=200)
st.caption(f"Word count: {email.get('word_count', '—')} · Suggested recipient: {email.get('suggested_recipient', {}).get('email', 'Unknown')}")

col1, col2 = st.columns(2)
full_email = f"Subject: {email['subject']}\n\n{email['body']}"
col1.download_button("📥 Copy as .txt", full_email, "outreach_email.txt", "text/plain")

if st.button("🔄 Regenerate"):
    st.rerun()