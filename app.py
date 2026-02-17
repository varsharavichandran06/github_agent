import asyncio
import os
import streamlit as st
from textwrap import dedent
from agno.agent import Agent
from agno.tools.mcp import MCPTools
from agno.models.openai import OpenAIChat
import nest_asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
import traceback

load_dotenv()
nest_asyncio.apply()

st.set_page_config(page_title="gh·lens", page_icon="⬡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;700;800&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'Space Mono', monospace;
    background-color: #0a0a0f;
    color: #e2e8f0;
}

/* ── Scanline overlay ── */
body::before {
    content: "";
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,255,136,0.015) 2px,
        rgba(0,255,136,0.015) 4px
    );
    pointer-events: none;
    z-index: 9999;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1100px; }

/* ── Hero header ── */
.gh-hero {
    border-left: 3px solid #00ff88;
    padding: 1.2rem 0 1.2rem 1.5rem;
    margin-bottom: 2.5rem;
}
.gh-hero h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2.6rem;
    color: #00ff88;
    letter-spacing: -0.02em;
    margin: 0 0 0.3rem;
    text-shadow: 0 0 30px rgba(0,255,136,0.4);
}
.gh-hero p {
    font-size: 0.78rem;
    color: #64748b;
    margin: 0;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* ── Section labels ── */
.field-label {
    font-size: 0.68rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #00ff88;
    margin-bottom: 0.35rem;
    display: block;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: #0f1117 !important;
    border: 1px solid #1e2d3d !important;
    border-radius: 4px !important;
    color: #e2e8f0 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.85rem !important;
    transition: border-color 0.2s;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #00ff88 !important;
    box-shadow: 0 0 0 1px #00ff8844 !important;
}

/* ── Button ── */
.stButton > button {
    background: transparent !important;
    border: 1px solid #00ff88 !important;
    color: #00ff88 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    padding: 0.65rem 1.5rem !important;
    border-radius: 3px !important;
    transition: all 0.2s !important;
    width: 100%;
}
.stButton > button:hover {
    background: #00ff8815 !important;
    box-shadow: 0 0 16px rgba(0,255,136,0.25) !important;
}

/* ── Result card ── */
.result-card {
    background: #0f1117;
    border: 1px solid #1e2d3d;
    border-top: 2px solid #00ff88;
    border-radius: 4px;
    padding: 1.8rem 2rem;
    margin-top: 1.5rem;
    font-size: 0.88rem;
    line-height: 1.7;
}
.result-card h3 {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #00ff88;
    margin: 0 0 1.2rem;
}

/* ── Query badge ── */
.query-badge {
    display: inline-block;
    background: #00ff8812;
    border: 1px solid #00ff8833;
    color: #00ff88;
    font-size: 0.75rem;
    padding: 0.3rem 0.8rem;
    border-radius: 2px;
    margin-bottom: 1.2rem;
    word-break: break-all;
}

/* ── Info box ── */
.info-box {
    background: #0f1117;
    border: 1px solid #1e2d3d;
    border-radius: 4px;
    padding: 1.6rem 2rem;
    margin-top: 2rem;
    font-size: 0.82rem;
    line-height: 1.8;
    color: #64748b;
}
.info-box h4 {
    font-family: 'Syne', sans-serif;
    color: #94a3b8;
    font-size: 0.75rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin: 0 0 1rem;
}
.info-box li { margin-bottom: 0.3rem; }
.info-box strong { color: #cbd5e1; }

/* ── Divider ── */
.gh-divider {
    border: none;
    border-top: 1px solid #1e2d3d;
    margin: 1.8rem 0;
}

/* ── Spinner override ── */
.stSpinner > div { border-top-color: #00ff88 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="gh-hero">
    <h1>⬡ gh·lens</h1>
    <p>natural language interface for GitHub repositories via MCP</p>
</div>
""", unsafe_allow_html=True)

github_token  = os.getenv("GITHUB_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")

col_repo, col_type = st.columns([3, 1])

with col_repo:
    st.markdown('<span class="field-label">Repository</span>', unsafe_allow_html=True)
    repo = st.text_input("repo", label_visibility="collapsed",
                         placeholder="owner/repo  e.g. torvalds/linux")

with col_type:
    st.markdown('<span class="field-label">Query preset</span>', unsafe_allow_html=True)
    query_type = st.selectbox(
        "type", ["Issues", "Pull Requests", "Repository Activity", "Custom"],
        label_visibility="collapsed"
    )

preset_map = {
    "Issues":              f"Find all open issues labeled as bugs in {repo}",
    "Pull Requests":       f"Show me recently merged pull requests in {repo}",
    "Repository Activity": f"Summarise recent commit activity and code quality trends in {repo}",
    "Custom":              "",
}
query_template = preset_map.get(query_type, "")

st.markdown('<span class="field-label">Query</span>', unsafe_allow_html=True)
query = st.text_area(
    "query", value=query_template, label_visibility="collapsed",
    placeholder="Ask anything about the repository…",
    height=100,
)

st.markdown("<hr class='gh-divider'>", unsafe_allow_html=True)

async def run_github_agent(message: str) -> str:
    """
    Initialize the Model Context Protocol GitHub server and execute an agent query.
    
    Args:
        message: The user's query about the GitHub repository
        
    Returns:
        The agent's response with GitHub insights, or an error message
    """
    if not github_token:
        return "GITHUB_TOKEN is not set in your environment."

    try:
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": github_token},
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                mcp_tools = MCPTools(session=session)
                await mcp_tools.initialize()

                agent = Agent(
                    model=OpenAIChat(id="gpt-4o"),
                    tools=[mcp_tools],
                    instructions=dedent("""\
                        You are a precise GitHub intelligence assistant.
                        - Deliver clear, structured insights drawn directly from the GitHub API
                        - Use markdown tables for numerical or comparative data
                        - Include direct links to relevant GitHub pages where useful
                        - Keep prose concise; let data speak for itself
                    """),
                    markdown=True,
                )

                response = await agent.arun(message)
                return response.content

    except Exception as e:
        if isinstance(e, ExceptionGroup):
            msgs = []
            for sub in e.exceptions:
                msgs.append(f"{type(sub).__name__}: {sub}")
                traceback.print_exception(type(sub), sub, sub.__traceback__)
            return "Errors encountered:\n" + "\n".join(msgs)

        traceback.print_exc()
        return f"Error — {type(e).__name__}: {e}"

run_clicked = st.button("▶  Run Query", type="primary", use_container_width=True)

if run_clicked:
    if not github_token:
        st.error("GITHUB_TOKEN not found. Add it to your .env file.")
    elif not query.strip():
        st.error("Please enter a query before running.")
    else:
        full_query = f"{query} (repository: {repo})" if repo and repo not in query else query

        with st.spinner("Querying GitHub via MCP…"):
            result = asyncio.run(run_github_agent(full_query))

        st.markdown(f"""
        <div class="result-card">
            <h3>⬡ result</h3>
            <div class="query-badge">▸ {full_query}</div>
            <div>{result}</div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="info-box">
        <h4>// getting started</h4>
        <ol>
            <li>Set <strong>GITHUB_TOKEN</strong> and <strong>OPENAI_API_KEY</strong> in your <code>.env</code> file</li>
            <li>Enter a repository in <strong>owner/repo</strong> format</li>
            <li>Pick a query preset or write your own</li>
            <li>Hit <strong>Run Query</strong></li>
        </ol>
        <hr style="border-color:#1e2d3d; margin: 1rem 0;">
        <p><strong>// notes</strong></p>
        <ul>
            <li>MCP provides live, real-time access — no cached data</li>
            <li>Specific queries return sharper results than broad ones</li>
            <li>Node.js must be installed for the <code>npx</code> command to work</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)