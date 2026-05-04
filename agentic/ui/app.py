import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import json
from agent.graph import agent

st.set_page_config(page_title="AI Team Formation Agent", page_icon="🤖", layout="centered")

st.title(" AI Team Formation Agent")
st.caption("Automated team selection ")

# ── Input ────────────────────────────────────────────────────────────────────

st.subheader("📋 Project Request")
request_text = st.text_area(
    "Describe your project requirements:",
    placeholder="Example: We need a team to build an e-commerce platform with React frontend and Python backend. Timeline is 8 weeks, team of 4 people.",
    height=150
)

if st.button(" Find Team", type="primary", disabled=not request_text.strip()):

    with st.spinner("Analyzing request..."):
        initial_state = {
            "request_text": request_text,
            "requirements": {},
            "candidates": [],
            "team_proposal": {},
            "approval_status": "pending",
            "report": ""
        }
        # Run up to form_team (before approval)
        result = agent.invoke(initial_state)
        st.session_state["agent_result"] = result

# ── Show proposal ─────────────────────────────────────────────────────────────

if "agent_result" in st.session_state:
    result = st.session_state["agent_result"]
    proposal = result.get("team_proposal", {})
    requirements = result.get("requirements", {})

    st.divider()
    st.subheader("Extracted Requirements")
    col1, col2, col3 = st.columns(3)
    col1.metric("Project Type", requirements.get("project_type", "—"))
    col2.metric("Team Size", requirements.get("team_size", "—"))
    col3.metric("Duration", f"{requirements.get('duration_weeks', '—')} weeks")

    st.write("**Required Skills:**", ", ".join(requirements.get("required_skills", [])))

    st.divider()
    st.subheader(" Proposed Team")

    if proposal.get("team"):
        for member in proposal["team"]:
            with st.expander(f" {member['name']} — {member['role']}"):
                st.write(f"**Reason:** {member['reason']}")

        st.info(f"**Team Lead:** {proposal.get('team_lead', '—')}")
        st.write(f"**Summary:** {proposal.get('summary', '—')}")

    # ── Approval ──────────────────────────────────────────────────────────────

    if result.get("approval_status") == "pending":
        st.divider()
        st.subheader(" Team Lead Approval")
        st.warning("Waiting for team lead decision...")

        col1, col2 = st.columns(2)
        if col1.button(" Approve", type="primary"):
            st.session_state["agent_result"]["approval_status"] = "approved"
            with st.spinner("Generating report..."):
                from agent.graph import generate_report
                final = generate_report(st.session_state["agent_result"])
                st.session_state["agent_result"] = final
            st.rerun()

        if col2.button(" Reject"):
            st.session_state["agent_result"]["approval_status"] = "rejected"
            with st.spinner("Generating report..."):
                from agent.graph import generate_report
                final = generate_report(st.session_state["agent_result"])
                st.session_state["agent_result"] = final
            st.rerun()

    # ── Report ────────────────────────────────────────────────────────────────

    if result.get("approval_status") in ("approved", "rejected") and result.get("report"):
        st.divider()
        st.subheader(" Final Report")
        status = result["approval_status"]
        if status == "approved":
            st.success("Team Approved ")
        else:
            st.error("Team Rejected ")
        st.code(result["report"], language="text")
        st.download_button("⬇️ Download Report", result["report"], file_name="team_report.txt")
