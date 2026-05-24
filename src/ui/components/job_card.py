"""
src/ui/components/job_card.py

Streamlit visual component to display job cards with premium styling, 
opportunity scores, tech stack tags, and quick-action buttons.
"""
from __future__ import annotations

import streamlit as st
from typing import Any, Dict


def render_job_card(job: dict[str, Any], on_action_click: Any = None) -> None:
    """
    Renders a premium job listing card in Streamlit.
    """
    title = job.get("title", "Software Engineer")
    company_name = job.get("company_name", "Unknown Company")
    location = job.get("location", "Remote")
    source = job.get("source", "Direct")
    opp_score = job.get("composite_score") or job.get("opportunity_score") or 0.0
    tech_stack = job.get("tech_stack") or []
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    currency = job.get("salary_currency", "USD")

    # Score coloring
    if opp_score >= 8.0 or opp_score >= 80.0:
        score_color = "green"
        score_emoji = "🔥 Excellent Match"
    elif opp_score >= 6.0 or opp_score >= 60.0:
        score_color = "orange"
        score_emoji = "👍 Good Match"
    else:
        score_color = "blue"
        score_emoji = "⚖️ Neutral"

    # Display clean card border using markdown + html container
    st.markdown(
        f"""
        <div style="
            border: 1px solid #e6ebf5; 
            border-radius: 8px; 
            padding: 16px; 
            margin-bottom: 12px; 
            background-color: #fcfcfd;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h3 style="margin: 0; color: #1f2937;">{title}</h3>
                    <span style="font-weight: 600; color: #4b5563;">🏢 {company_name}</span> &nbsp;&middot;&nbsp; 
                    <span style="color: #6b7280;">📍 {location}</span>
                </div>
                <div style="
                    background-color: {score_color}; 
                    color: white; 
                    padding: 4px 8px; 
                    border-radius: 4px; 
                    font-size: 0.85em; 
                    font-weight: bold;
                ">
                    Score: {opp_score:.1f}
                </div>
            </div>
            
            <div style="margin-top: 8px; font-size: 0.9em; color: #6b7280;">
                <span>🔌 Source: <b>{source}</b></span>
                {f' &nbsp;&middot;&nbsp; 💵 Salary: <b>{currency} {salary_min:,} - {salary_max:,}</b>' if salary_min and salary_max else ''}
            </div>
            
            <div style="margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px;">
                {' '.join([f'<span style="background-color: #e5e7eb; color: #374151; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">{t}</span>' for t in tech_stack[:6]])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
