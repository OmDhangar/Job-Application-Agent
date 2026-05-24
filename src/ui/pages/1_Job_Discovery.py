"""
src/ui/pages/1_Job_Discovery.py
Semantic job search + ranked results display.
"""
import streamlit as st
import httpx

API = "http://localhost:8000/api/v1"

st.title("🔍 Job Discovery")
st.caption("Semantic search powered by local BGE embeddings + pgvector")

with st.sidebar:
    st.header("Search Filters")
    query       = st.text_area("Describe your ideal role", height=100,
                               placeholder="Senior backend engineer, Python, distributed systems...")
    seniority   = st.selectbox("Seniority", ["", "intern", "junior", "mid", "senior", "staff", "principal"])
    remote_only = st.checkbox("Remote only")
    top_k       = st.slider("Results to show", 5, 50, 10)
    search_btn  = st.button("🔍 Search", type="primary", use_container_width=True)

    st.markdown("---")
    st.subheader("Quick Browse")
    browse_btn = st.button("Browse latest jobs", use_container_width=True)

# ── Browse latest ─────────────────────────────────────────────────────────────
if browse_btn:
    try:
        r = httpx.get(f"{API}/jobs/", params={"limit": 20, "remote_only": remote_only}, timeout=10)
        jobs = r.json()
        st.subheader(f"Latest {len(jobs)} Jobs")
        for job in jobs:
            with st.expander(f"**{job['title']}** — {job.get('location', 'Unknown')}"):
                c1, c2, c3 = st.columns(3)
                c1.caption(f"Source: {job['source']}")
                c2.caption(f"Seniority: {job.get('seniority', '—')}")
                c3.caption(f"Remote: {job.get('remote_type', '—')}")
                if job.get("tech_stack"):
                    st.write("**Stack:** " + ", ".join(job["tech_stack"][:8]))
                if job.get("opportunity_score"):
                    st.progress(min(job["opportunity_score"] / 10, 1.0),
                                text=f"Opportunity score: {job['opportunity_score']:.1f}/10")
    except httpx.ConnectError:
        st.error("Cannot reach API — is `uvicorn src.api.main:app` running?")

# ── Semantic search ───────────────────────────────────────────────────────────
if search_btn:
    if not query.strip():
        st.warning("Enter a description to search.")
        st.stop()
    with st.spinner("Embedding query → pgvector search → ranking..."):
        try:
            r = httpx.post(
                f"{API}/jobs/search",
                json={
                    "query": query,
                    "seniority": seniority or None,
                    "remote_only": remote_only,
                    "top_k": top_k,
                },
                timeout=30,
            )
            r.raise_for_status()
            results = r.json()
        except httpx.ConnectError:
            st.error("Cannot reach API.")
            st.stop()
        except Exception as e:
            st.error(f"Search failed: {e}")
            st.stop()

    st.success(f"Found {len(results)} matching jobs")
    for job in results:
        score_pct = job.get("composite_score", 0) * 100
        with st.expander(
            f"**{job['title']}** — {job.get('location','?')} "
            f"| Match: {score_pct:.0f}%"
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("Semantic",  f"{job.get('semantic_score', 0):.2f}")
            c2.metric("Skill Overlap", f"{job.get('skill_overlap', 0):.2f}")
            c3.metric("Composite", f"{score_pct:.0f}%")
            if job.get("tech_stack"):
                st.write("**Stack:** " + ", ".join(job["tech_stack"][:8]))
            if job.get("source_url"):
                st.link_button("View posting →", job["source_url"])