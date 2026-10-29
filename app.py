
import os
import sqlite3
import time
import uuid
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from google import genai
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io import BytesIO

def create_pdf_report(topic, research, analysis, summary, report):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("AI Research Report", styles["Title"]))
    content.append(Spacer(1, 0.2 * inch))

    sections = [
        ("Research Topic", topic),
        ("Research Overview", research),
        ("Analysis", analysis),
        ("Summary", summary),
        ("Final Report", report),
    ]

    for heading, text in sections:
        content.append(Paragraph(heading, styles["Heading2"]))
        content.append(Spacer(1, 0.1 * inch))

        safe_text = (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

        content.append(Paragraph(safe_text, styles["BodyText"]))
        content.append(Spacer(1, 0.2 * inch))

    doc.build(content)
    buffer.seek(0)

    return buffer.getvalue()
# ---------------- Configuration ----------------

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.6-flash"
DB_NAME = "research_history.db"

st.set_page_config(
    page_title="Multi-Agent AI Research System",
    page_icon="🤖",
    layout="wide"
)


# ---------------- Database ----------------

def init_database():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                research TEXT NOT NULL,
                analysis TEXT NOT NULL,
                summary TEXT NOT NULL,
                report TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Migrate a database created by the earlier app version.
        columns = {
            row[1] for row in
            conn.execute("PRAGMA table_info(research)").fetchall()
        }

        for name in ("research", "analysis"):
            if name not in columns:
                conn.execute(
                    f"ALTER TABLE research ADD COLUMN {name} TEXT DEFAULT ''"
                )
        if "session_id" not in columns:
            conn.execute(
                "ALTER TABLE research ADD COLUMN session_id TEXT"
            )

        rows = conn.execute(
            "SELECT id FROM research WHERE session_id IS NULL"
        ).fetchall()

        for row in rows:
            conn.execute(
                "UPDATE research SET session_id = ? WHERE id = ?",
                (f"legacy-{row[0]}", row[0])
            )

init_database()


# ---------------- Gemini Client ----------------

def ask_gemini(prompt, retries=3):
    if not API_KEY:
        raise ValueError(
            "Gemini API key missing. Check the GEMINI_API_KEY "
            "entry in your .env file."
        )

    client = genai.Client(api_key=API_KEY)
    last_error = None

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            if response.text:
                return response.text

            raise RuntimeError("Gemini returned an empty response.")

        except Exception as error:
            last_error = error
            message = str(error).lower()

            # Retry temporary service errors and rate limits.
            temporary = any(
                term in message
                for term in (
                    "503", "unavailable", "overloaded",
                    "429", "resource_exhausted", "500",
                    "internal server error"
                )
            )

            if not temporary or attempt == retries - 1:
                break

            time.sleep(2 ** (attempt + 1))

    raise RuntimeError(
        f"Gemini request failed. Check model availability, API "
        f"quota and connection. Details: {last_error}"
    )


# ---------------- Specialized Agents ----------------

def research_agent(topic):
    prompt = f"""
    ROLE: Research Agent

    Prepare a detailed research overview about: {topic}

    Include:
    1. Introduction and background
    2. Core concepts
    3. Current applications
    4. Benefits
    5. Limitations and challenges
    6. Future opportunities

    Use clear headings. Do not invent statistics, references,
    or claim that you searched the live web.
    Identify claims that need independent verification.
    """
    return ask_gemini(prompt)


def analysis_agent(topic, research):
    prompt = f"""
    ROLE: Analysis Agent

    Topic: {topic}

    Research overview:
    {research}

    Analyse the overview and provide:
    1. Key findings
    2. Advantages and disadvantages
    3. Technical or practical challenges
    4. Risks and limitations
    5. Opportunities and implications
    6. Three useful recommendations

    Base your analysis on the supplied overview.
    Clearly distinguish supported findings from assumptions.
    Do not invent data or references.
    """
    return ask_gemini(prompt)


def summarizer_agent(topic, research, analysis):
    prompt = f"""
    ROLE: Summarization Agent

    Topic: {topic}

    Research overview:
    {research}

    Analysis:
    {analysis}

    Write an easy-to-understand summary of the topic.
    Highlight the main findings, benefits, challenges,
    and conclusion. Avoid unnecessary repetition.
    """
    return ask_gemini(prompt)


def report_agent(topic, research, analysis, summary):
    prompt = f"""
    ROLE: Report Generation Agent

    Topic: {topic}

    Research overview:
    {research}

    Analysis:
    {analysis}

    Summary:
    {summary}

    Create a professional report containing:
    1. Title
    2. Abstract
    3. Introduction
    4. Research overview
    5. Analysis and key findings
    6. Benefits and challenges
    7. Recommendations
    8. Conclusion
    9. Areas for further research

    Do not invent references, statistics, or source links.
    State that this is an AI-generated report.
    """
    return ask_gemini(prompt)


# ---------------- Workflow Coordinator ----------------

def run_research_workflow(topic):
    """Coordinates the agents and passes results between them."""
    progress = st.progress(0)
    status = st.empty()

    status.write("1/4 — Research Agent is gathering an overview...")
    research = research_agent(topic)
    progress.progress(25)

    status.write("2/4 — Analysis Agent is evaluating findings...")
    analysis = analysis_agent(topic, research)
    progress.progress(50)

    status.write("3/4 — Summarization Agent is preparing a summary...")
    summary = summarizer_agent(topic, research, analysis)
    progress.progress(75)

    status.write("4/4 — Report Agent is preparing the final report...")
    report = report_agent(topic, research, analysis, summary)
    progress.progress(100)

    status.success("All four agents completed their tasks.")
    return research, analysis, summary, report


# ---------------- User Interface ----------------
# Initialize the current chat session
if "current_session_id" not in st.session_state:
    st.session_state["current_session_id"] = str(uuid.uuid4())

if "topic_input" not in st.session_state:
    st.session_state["topic_input"] = ""
st.title("🤖 Enterprise Multi-Agent AI Research Automation System")

st.write(
    "An AI-assisted research workflow using specialized agents "
    "for research, analysis, summarization, and report generation."
)

st.caption(
    "Research is generated from model knowledge and supplied context. "
    "Live web research and source verification are not implemented."
)

with st.sidebar:
    st.header("AI Agents")
    st.write("🔎 Research Agent")
    st.write("🧠 Analysis Agent")
    st.write("📝 Summarization Agent")
    st.write("📄 Report Generation Agent")
    st.divider()
    st.subheader("💬 Chat Sessions")

    if st.button("➕ New Chat", use_container_width=True):
        st.session_state["current_session_id"] = str(uuid.uuid4())
        st.session_state.pop("latest_result", None)
        st.session_state["topic_input"] = ""
        st.rerun()
    
    st.divider()
    st.subheader("💬 Previous Chats")

    # Fetch saved research sessions
    with sqlite3.connect(DB_NAME) as conn:
        saved_chats = conn.execute("""
            SELECT session_id, topic, MAX(created_at)
            FROM research
            WHERE session_id IS NOT NULL
            GROUP BY session_id
            ORDER BY MAX(created_at) DESC
        """).fetchall()

    if saved_chats:
        chat_options = {
            f"{row[1]} — {row[2]}": row[0]
            for row in saved_chats
        }

        selected_chat = st.selectbox(
            "Select a previous chat",
            options=list(chat_options.keys()),
            key="previous_chat_selector"
        )

        if st.button("📂 Open Chat", use_container_width=True):
            selected_id = chat_options[selected_chat]

            with sqlite3.connect(DB_NAME) as conn:
                saved = conn.execute("""
                    SELECT topic, research, analysis,
                           summary, report, created_at
                    FROM research
                    WHERE session_id = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                """, (selected_id,)).fetchone()

            if saved:
                st.session_state["current_session_id"] = selected_id
                st.session_state["topic_input"] = saved[0]

                st.session_state["latest_result"] = {
                    "topic": saved[0],
                    "research": saved[1] or "",
                    "analysis": saved[2] or "",
                    "summary": saved[3] or "",
                    "report": saved[4] or "",
                    "created_at": saved[5]
                }

                st.rerun()
    else:
        st.caption("No previous chats yet. Generate your first research!")

    
topic = st.text_input(
    "Enter your research topic",
    placeholder="Example: AI applications in healthcare",
    key="topic_input"
)

if st.button("Generate Research", type="primary"):
    if not topic.strip():
        st.warning("Please enter a research topic.")
    else:
        try:
            results = run_research_workflow(topic.strip())
            research, analysis, summary, report = results

            created_at = datetime.now().isoformat(timespec="seconds")

            
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("""
                    INSERT INTO research
                    (session_id, topic, research, analysis, summary, report, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    st.session_state["current_session_id"],
                    topic.strip(),
                    research,
                    analysis,
                    summary,
                    report,
                    created_at
                ))


            st.session_state["latest_result"] = {
                "topic": topic.strip(),
                "research": research,
                "analysis": analysis,
                "summary": summary,
                "report": report,
                "created_at": created_at
            }

        except Exception as error:
            st.error(str(error))
            st.info(
                "Check your .env API key, internet connection, "
                "model access, and Gemini usage limits."
            )

# Display most recently generated results.
result = st.session_state.get("latest_result")

if result:
    st.subheader(f"Results: {result['topic']}")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Research Overview",
        "Analysis",
        "Summary",
        "Final Report"
    ])

    with tab1:
        st.markdown(result["research"])

    with tab2:
        st.markdown(result["analysis"])

    with tab3:
        st.markdown(result["summary"])

    with tab4:
        st.markdown(result["report"])

    st.download_button(
        "Download Final Report",
        data=result["report"],
        file_name="research_report.txt",
        mime="text/plain"
    )
    pdf_data = create_pdf_report(
        topic=result["topic"],
        research=result["research"],
        analysis=result["analysis"],
        summary=result["summary"],
        report=result["report"]
    )

    st.download_button(
        label="Download PDF Report",
        data=pdf_data,
        file_name="AI_Research_Report.pdf",
        mime="application/pdf"
    )
    st.download_button(
        "Download Complete Research",
        data=(
            f"TOPIC: {result['topic']}\n\n"
            f"RESEARCH OVERVIEW\n{result['research']}\n\n"
            f"ANALYSIS\n{result['analysis']}\n\n"
            f"SUMMARY\n{result['summary']}\n\n"
            f"FINAL REPORT\n{result['report']}"
        ),
        file_name="complete_research.txt",
        mime="text/plain"
    )

# ---------------- Research History ----------------

st.divider()
st.subheader("📚 Previous Research")

with sqlite3.connect(DB_NAME) as conn:
    history = conn.execute("""
        SELECT id, topic, summary, report, created_at
        FROM research
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

if history:
    for row_id, old_topic, old_summary, old_report, created_at in history:
        with st.expander(f"{old_topic} — {created_at}"):
            st.markdown("**Summary**")
            st.write(old_summary)

            st.download_button(
                "Download this report",
                data=old_report,
                file_name=f"research_report_{row_id}.txt",
                mime="text/plain",
                key=f"history_download_{row_id}"
            )
else:
    st.info("No research history yet. Generate your first report!")
