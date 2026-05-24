"""
src/ui/pages/4_Applications.py  —  Application lifecycle tracking + funnel analytics.
"""
import httpx
import streamlit as st

API = "http://localhost:8000/api/v1"

st.title("📊 Application Tracker")
st.caption("Track every application, reply, and interview")

# ── Candidate selector (MVP: hardcoded email lookup) ─────────────────────────
with st.sidebar:
    st.header("Candidate")
    cand_id = st.text_input("Candidate ID (UUID)", placeholder="paste your candidate UUID here")
    load_btn = st.button("Load Applications", use_container_width=True)

STATUS_COLORS = {
    "discovered":   "🔵",
    "applied":      "🟡",
    "replied":      "🟠",
    "interviewing": "🟢",
    "offered":      "⭐",
    "rejected":     "🔴",
    "ghosted":      "⚫",
}

VALID_NEXT = {
    "discovered":   ["applied", "rejected"],
    "applied":      ["replied", "rejected", "ghosted"],
    "replied":      ["interviewing", "rejected"],
    "interviewing": ["offered", "rejected"],
    "offered":      [],
    "rejected":     [],
    "ghosted":      ["replied"],
}

if not load_btn or not cand_id.strip():
    st.info("Enter your Candidate ID in the sidebar to load applications.")
    st.stop()

# ── Load applications ─────────────────────────────────────────────────────────
try:
    r = httpx.get(f"{API}/applications/candidate/{cand_id.strip()}", timeout=10)
    r.raise_for_status()
    apps = r.json()
except httpx.ConnectError:
    st.error("Cannot reach API.")
    st.stop()
except Exception as e:
    st.error(f"Failed to load: {e}")
    st.stop()

if not apps:
    st.info("No applications found for this candidate.")
    st.stop()

# ── Funnel metrics ────────────────────────────────────────────────────────────
total = len(apps)
replied = sum(1 for a in apps if a["status"] in ("replied", "interviewing", "offered"))
interviewing = sum(1 for a in apps if a["status"] in ("interviewing", "offered"))
offered = sum(1 for a in apps if a["status"] == "offered")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Applications", total)
c2.metric("Reply Rate",         f"{replied/total*100:.0f}%" if total else "—")
c3.metric("Interview Rate",     f"{interviewing/total*100:.0f}%" if total else "—")
c4.metric("Offers",             offered)

# ── Status distribution bar ───────────────────────────────────────────────────
status_counts: dict[str, int] = {}
for a in apps:
    status_counts[a["status"]] = status_counts.get(a["status"], 0) + 1

st.markdown("**Status breakdown**")
for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
    icon = STATUS_COLORS.get(status, "⚪")
    pct = count / total * 100
    st.progress(pct / 100, text=f"{icon} {status.capitalize()}: {count} ({pct:.0f}%)")

st.markdown("---")

# ── Application list ──────────────────────────────────────────────────────────
st.subheader(f"All Applications ({total})")

for app in apps:
    icon = STATUS_COLORS.get(app["status"], "⚪")
    score = app.get("interview_probability")
    score_str = f"| IP: {score:.0f}%" if score else ""
    label = f"{icon} Job {app['job_id'][:8]}... — **{app['status'].upper()}** {score_str}"

    with st.expander(label):
        col1, col2, col3 = st.columns(3)
        col1.caption(f"ATS Score: {app.get('ats_score', '—')}")
        col2.caption(f"Applied: {app.get('applied_at', '—')}")
        col3.caption(f"Created: {app.get('created_at', '—')[:10]}")

        # Status update
        next_states = VALID_NEXT.get(app["status"], [])
        if next_states:
            new_status = st.selectbox(
                "Update status →",
                options=["— keep current —"] + next_states,
                key=f"status_{app['id']}",
            )
            notes = st.text_input("Notes (optional)", key=f"notes_{app['id']}")
            if st.button("Update", key=f"update_{app['id']}"):
                if new_status != "— keep current —":
                    try:
                        upd = httpx.patch(
                            f"{API}/applications/{app['id']}/status",
                            json={"status": new_status, "notes": notes},
                            timeout=10,
                        )
                        upd.raise_for_status()
                        st.success(f"Updated to {new_status}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")
        else:
            st.caption("No further status transitions available.")