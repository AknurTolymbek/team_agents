import os
import json
import pandas as pd
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

# ── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    request_text: str
    requirements: dict
    candidates: list
    team_proposal: dict
    approval_status: str       # "pending" | "approved" | "rejected"
    rejection_count: int       # сколько раз отклоняли
    previous_teams: list       # предыдущие отклонённые команды
    report: str

# ── LLM ─────────────────────────────────────────────────────────────────────

from dotenv import load_dotenv
load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), max_tokens=2000)
# ── Helpers ──────────────────────────────────────────────────────────────────

def load_employees() -> pd.DataFrame:
    path = os.path.join(os.path.dirname(__file__), "../data/employees.csv")
    return pd.read_csv(path)

# ── Node 1: Parse request ────────────────────────────────────────────────────

def parse_request(state: AgentState) -> AgentState:
    prompt = f"""You are an AI that extracts project requirements from a request.

Request:
{state["request_text"]}

Extract and return ONLY valid JSON with this structure:
{{
  "project_type": "string",
  "required_skills": ["skill1", "skill2"],
  "team_size": number,
  "duration_weeks": number,
  "description": "string"
}}
Return only JSON, no explanation."""

    response = llm.invoke(prompt)
    text = response.content.strip().replace("```json", "").replace("```", "").strip()
    requirements = json.loads(text)
    return {**state, "requirements": requirements}

# ── Node 2: Match employees ──────────────────────────────────────────────────

def match_employees(state: AgentState) -> AgentState:
    df = load_employees()
    available = df[df["available"] == True].copy()
    employees_list = available.to_dict(orient="records")
    return {**state, "candidates": employees_list}

# ── Node 3: Form team ────────────────────────────────────────────────────────

def form_team(state: AgentState) -> AgentState:
    candidates_text = json.dumps(state["candidates"], ensure_ascii=False, indent=2)
    requirements_text = json.dumps(state["requirements"], ensure_ascii=False, indent=2)

    # Только те у кого is_team_lead = true
    leads = [e for e in state["candidates"] if e.get("is_team_lead") == True]
    leads_text = json.dumps([e["name"] for e in leads], ensure_ascii=False)

    previous_text = ""
    if state.get("previous_teams"):
        previous_text = f"""
Previously rejected teams (DO NOT select the same combination):
{json.dumps(state["previous_teams"], ensure_ascii=False, indent=2)}
"""

    prompt = f"""You are an AI team formation assistant. Select the BEST team for the project.

Rules:
- Do NOT duplicate roles (if you pick a Full Stack Developer, do not add separate Frontend + Backend)
- Each team member must have a DISTINCT role that adds unique value
- Team size should match the requirements
- Pick people whose skills actually match what is needed
- If previous teams were rejected, propose a DIFFERENT combination
- Team lead MUST be selected ONLY from this list: {leads_text}

Project requirements:
{requirements_text}

Available candidates (all available=true):
{candidates_text}
{previous_text}

Return ONLY valid JSON:
{{
  "team": [
    {{"id": number, "name": "string", "role": "string", "reason": "string"}}
  ],
  "team_lead": "string (name)",
  "summary": "string (why this team fits the project)"
}}
Return only JSON, no explanation."""

    response = llm.invoke(prompt)
    text = response.content.strip().replace("```json", "").replace("```", "").strip()
    proposal = json.loads(text)
    return {**state, "team_proposal": proposal, "approval_status": "pending"}

# ── Node 4: Approval (human-in-the-loop) ────────────────────────────────────

def request_approval(state: AgentState) -> AgentState:
    return state

# ── Node 5: Re-form team after rejection ─────────────────────────────────────

def handle_rejection(state: AgentState) -> AgentState:
    previous_teams = state.get("previous_teams", [])
    if state.get("team_proposal"):
        previous_teams = previous_teams + [state["team_proposal"]]

    rejection_count = state.get("rejection_count", 0) + 1

    return {
        **state,
        "previous_teams": previous_teams,
        "rejection_count": rejection_count,
        "approval_status": "pending",
        "team_proposal": {},
    }

# ── Node 6: Generate report ──────────────────────────────────────────────────

def generate_report(state: AgentState) -> AgentState:
    proposal = state["team_proposal"]
    requirements = state["requirements"]
    status = state["approval_status"]

    team_lines = "\n".join(
        f"  - {m['name']} ({m['role']}): {m['reason']}"
        for m in proposal.get("team", [])
    )

    prompt = f"""Generate a professional team formation report based on the data below.
IMPORTANT: Write the report in the SAME language as the project description.
Do NOT use any markdown symbols like **, *, =, #, or --. Use plain text only.

Project description: {requirements.get("description", "")}
Project type: {requirements.get("project_type", "")}
Duration: {requirements.get("duration_weeks", "")} weeks
Approval status: {status.upper()}
Team lead: {proposal.get("team_lead", "")}
Selected team:
{team_lines}
Summary: {proposal.get("summary", "")}

Format the report clearly with sections using plain text."""

    response = llm.invoke(prompt)
    report = response.content.strip()
    return {**state, "report": report}

# ── Routing ──────────────────────────────────────────────────────────────────

def route_approval(state: AgentState) -> str:
    if state["approval_status"] == "approved":
        return "generate_report"
    elif state["approval_status"] == "rejected":
        if state.get("rejection_count", 0) >= 3:
            return "generate_report"
        return "handle_rejection"
    else:
        return END

# ── Build graph ──────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("parse_request",    parse_request)
    graph.add_node("match_employees",  match_employees)
    graph.add_node("form_team",        form_team)
    graph.add_node("request_approval", request_approval)
    graph.add_node("handle_rejection", handle_rejection)
    graph.add_node("generate_report",  generate_report)

    graph.set_entry_point("parse_request")
    graph.add_edge("parse_request",    "match_employees")
    graph.add_edge("match_employees",  "form_team")
    graph.add_edge("form_team",        "request_approval")
    graph.add_conditional_edges("request_approval", route_approval)
    graph.add_edge("handle_rejection", "form_team")
    graph.add_edge("generate_report",  END)

    return graph.compile()

agent = build_graph()
