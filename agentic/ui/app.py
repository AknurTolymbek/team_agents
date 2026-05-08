import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from agent.graph import agent, generate_report

st.set_page_config(page_title="Agentic AI Assistant", page_icon="🤖", layout="centered")

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background-color: #f7f8fc; }

div.stButton > button[kind="primary"] {
    background-color: #2D2D2D !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.55rem 2rem !important;
    font-size: 15px !important;
    font-weight: 500 !important;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #444 !important;
}
div.stButton > button[kind="primary"]:disabled {
    background-color: #BDBDBD !important;
    color: #f0f0f0 !important;
}

div[data-testid="stColumn"]:first-child div[data-testid="stButton"] > button {
    background-color: #66BB6A !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    width: 100% !important;
}
div[data-testid="stColumn"]:first-child div[data-testid="stButton"] > button:hover {
    background-color: #43A047 !important;
}

div[data-testid="stColumn"]:last-child div[data-testid="stButton"] > button {
    background-color: #d15c5c !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    width: 100% !important;
}
div[data-testid="stColumn"]:last-child div[data-testid="stButton"] > button:hover {
    background-color: #bf3f3f !important;
}

div[data-testid="metric-container"] {
    background: white;
    border-radius: 12px;
    padding: 0.8rem 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

textarea {
    border-radius: 10px !important;
    border: 1.5px solid #e0e0e0 !important;
    background: white !important;
}

details {
    background: white !important;
    border-radius: 10px !important;
    border: 1px solid #ececec !important;
    margin-bottom: 6px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; padding: 1.5rem 0 1rem 0;">
    <div style="font-size:2rem; font-weight:700; color:#1a1a2e;">Agentic AI Assistant</div>
    <div style="font-size:1rem; color:#666; margin: 0.3rem 0 0.6rem 0;">Intelligent automation for business workflows</div>
    <span style="display:inline-block; background:#e8f5e9; color:#2e7d32; border-radius:20px;
                 padding:3px 16px; font-size:13px; font-weight:500;">Team Formation Module</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── File text extractor ───────────────────────────────────────────────────────

def extract_text_from_file(uploaded_file) -> str:
    name = uploaded_file.name.lower()

    if name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")

    elif name.endswith(".pdf"):
        try:
            import pdfplumber
            import io
            with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
        except ImportError:
            st.error("Run: pip install pdfplumber")
            return ""

    elif name.endswith(".docx"):
        try:
            import docx
            import io
            doc = docx.Document(io.BytesIO(uploaded_file.read()))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            st.error("Run: pip install python-docx")
            return ""

    else:
        st.error("Unsupported format. Use TXT, PDF, or DOCX.")
        return ""

# ── Input ─────────────────────────────────────────────────────────────────────

st.subheader("Project Request")

tab1, tab2 = st.tabs(["Type manually", "Upload file"])

request_text = ""

with tab1:
    typed = st.text_area(
        "Describe your project requirements:",
        placeholder="Example: We need a team to build an e-commerce platform with React frontend and Python backend. Timeline is 8 weeks, team of 4 people.",
        height=150,
        key="manual_input"
    )
    request_text = typed

with tab2:
    uploaded_file = st.file_uploader(
        "Upload a project brief (TXT, PDF, DOCX):",
        type=["txt", "pdf", "docx"],
        key="file_input"
    )
    if uploaded_file is not None:
        extracted = extract_text_from_file(uploaded_file)
        if extracted:
            st.success(f"File read: {uploaded_file.name}")
            with st.expander("Preview extracted text"):
                st.write(extracted[:1000] + ("..." if len(extracted) > 1000 else ""))
            request_text = extracted

if st.button("Find Team", type="primary", disabled=not request_text.strip()):
    st.session_state.pop("agent_result", None)
    st.session_state.pop("manual_mode", None)

    with st.spinner("Analyzing request and forming team..."):
        initial_state = {
            "request_text": request_text,
            "requirements": {},
            "candidates": [],
            "team_proposal": {},
            "approval_status": "pending",
            "rejection_count": 0,
            "previous_teams": [],
            "report": ""
        }
        result = agent.invoke(initial_state)
        st.session_state["agent_result"] = result

# ── Results ───────────────────────────────────────────────────────────────────

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
    st.markdown(f"**Required Skills:** {', '.join(requirements.get('required_skills', []))}")

    # ── Manual selection after reject ─────────────────────────────────────────

    if st.session_state.get("manual_mode"):
        st.divider()
        st.subheader("Manual Team Selection")
        st.info("The AI proposal was rejected. Please select the team manually from the list below.")

        csv_path = os.path.join(os.path.dirname(__file__), "../data/employees.csv")
        df = pd.read_csv(csv_path)
        available = df[df["available"] == True].copy()

        st.write("**Select team members:**")
        selected_members = []
        for _, row in available.iterrows():
            checked = st.checkbox(
                f"**{row['name']}** — {row['role']}  |  {row['skills']}  |  {row['experience_years']} yrs exp",
                key=f"emp_{row['id']}"
            )
            if checked:
                selected_members.append(row)

        team_lead_name = st.selectbox(
            "Select Team Lead:",
            options=["—"] + available["name"].tolist()
        )

        if st.button("Confirm Manual Team", type="primary", disabled=len(selected_members) == 0):
            if team_lead_name == "—":
                st.warning("Please select a team lead.")
            else:
                manual_team = [
                    {"id": int(m["id"]), "name": m["name"], "role": m["role"],
                     "reason": "Manually selected by team lead"}
                    for m in selected_members
                ]
                manual_proposal = {
                    "team": manual_team,
                    "team_lead": team_lead_name,
                    "summary": "Team was manually selected by the team lead after rejecting the AI proposal."
                }
                st.session_state["agent_result"]["team_proposal"] = manual_proposal
                st.session_state["agent_result"]["approval_status"] = "approved"
                with st.spinner("Generating report..."):
                    final = generate_report(st.session_state["agent_result"])
                    st.session_state["agent_result"] = final
                    st.session_state["manual_mode"] = False
                st.rerun()

    # ── AI Proposal ───────────────────────────────────────────────────────────

    elif result.get("approval_status") == "pending" and proposal.get("team"):
        st.divider()
        st.subheader("Proposed Team")

        for member in proposal["team"]:
            with st.expander(f"{member['name']} — {member['role']}"):
                st.write(f"**Reason:** {member['reason']}")

        st.info(f"Team Lead: {proposal.get('team_lead', '—')}")
        st.markdown(f"**Summary:** {proposal.get('summary', '—')}")

        st.divider()
        st.subheader("Team Lead Approval")
        st.warning("Please review the proposed team and make a decision.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve", type="primary", use_container_width=True):
                st.session_state["agent_result"]["approval_status"] = "approved"
                with st.spinner("Generating report..."):
                    final = generate_report(st.session_state["agent_result"])
                    st.session_state["agent_result"] = final
                st.rerun()
        with col2:
            if st.button("Reject", type="primary", use_container_width=True):
                st.session_state["manual_mode"] = True
                st.rerun()

    # ── Final Report ──────────────────────────────────────────────────────────

    if result.get("approval_status") in ("approved", "rejected") and result.get("report"):
        st.divider()
        st.subheader("Final Report")
        if result["approval_status"] == "approved":
            st.success("Team Approved")
        else:
            st.error("Team Rejected")
        st.code(result["report"], language="text")
        st.download_button("Download Report", result["report"], file_name="team_report.txt")
