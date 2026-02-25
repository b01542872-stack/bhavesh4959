import streamlit as st
import time
import os
import pandas as pd
from datetime import datetime

# Local imports
from utils import extract_text_from_pdf, send_email_with_attachment
from agents import parse_resume_agent, job_discovery_agent, cover_letter_agent, interview_prep_agent

# Constants
COMPANY_NAME = "TOPS Technologies"

def inject_custom_css():
    """Injects custom CSS for styling and animations."""
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("style.css not found, using default styles.")

def init_session_state():
    """Initializes necessary variables in session state."""
    defaults = {
        "logs": [],
        "jobs_identified": 0,
        "successful_dispatches": 0,
        "api_fallbacks": 0,
        "parsed_resume": None,
        "mock_jobs": None,
        "interview_questions": None,
        "pdf_bytes": None,
        "pdf_filename": None,
        "workflow_started": False,
        "workflow_completed": False
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def append_log(message: str, error=False, fallback=False):
    """Appends a new line to the terminal logs and updates stats."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = "red" if error else "#0288d1"
    if fallback:
        st.session_state.api_fallbacks += 1
        color = "orange"
        
    log_html = f"<div class='terminal-line'><span class='terminal-time'>[{timestamp}]</span> <span style='color: {color}'>{message}</span></div>"
    st.session_state.logs.append(log_html)

def render_logs():
    """Renders the execution logs widget."""
    logs_html = "".join(st.session_state.logs[-50:]) # keep last 50
    if not st.session_state.logs:
        return # Do not render the large white box if there are no logs
        
    st.markdown(f"""
        <div class="terminal-container">
            <div class="terminal-body" id="terminal-body">
                {logs_html}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Execute JS via Streamlit Components to handle auto-scroll in the parent DOM
    import streamlit.components.v1 as components
    components.html("""
        <script>
            try {
                var d = window.parent.document.getElementById("terminal-body");
                if (d) {
                    d.scrollTop = d.scrollHeight;
                }
            } catch (e) {}
        </script>
    """, height=0)

def main():
    st.set_page_config(page_title=f"{COMPANY_NAME} Agent AI", page_icon="🤖", layout="wide")
    inject_custom_css()
    init_session_state()

    # --- Header ---
    st.markdown(f"<h1 style='text-align: center; margin-bottom: 2rem;'>{COMPANY_NAME} | Agentic AI Job App Ecosystem</h1>", unsafe_allow_html=True)

    # --- Dashboard Metrics ---
    st.markdown("### Live Analytics Suite")
    col1, col2, col3 = st.columns(3)
    col1.metric("Jobs Identified", st.session_state.jobs_identified)
    col2.metric("Successful Dispatches", st.session_state.successful_dispatches)
    col3.metric("API Fallbacks/Skips", st.session_state.api_fallbacks)
    st.markdown("<hr>", unsafe_allow_html=True)

    # --- Sidebar Configuration ---
    st.sidebar.markdown("### ⚙️ System Configuration")
    
    # Secrets management via sidebar if not in st.secrets
    gemini_key = ""
    try:
        gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass # Handle StreamlitSecretNotFoundError if secrets.toml doesn't exist
        
    if not gemini_key:
        api_key_input = st.sidebar.text_input("Gemini API Key", type="password")
        if api_key_input:
            st.session_state["gemini_api_key"] = api_key_input
            
    # Email configuration
    sender_email = st.sidebar.text_input("Sender Email Address", value="user@example.com")
    app_password = st.sidebar.text_input("Email App Password", type="password")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 Workflow Preferences")
    manual_role_input = st.sidebar.text_input("Override Role (Leave blank for AI)", placeholder="e.g. Senior Frontend Engineer")
    preferred_loc = st.sidebar.text_input("Preferred Location", value="Remote")

    # --- Main Workflow UI ---
    st.markdown("### 📄 1. Intelligent Parsing")
    uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])

    if uploaded_file is not None:
        if st.session_state.pdf_filename != uploaded_file.name:
            st.session_state.pdf_bytes = uploaded_file.getvalue()
            st.session_state.pdf_filename = uploaded_file.name
            st.session_state.parsed_resume = None
            st.session_state.workflow_started = False
            
    if st.button("Start Agentic Workflow", disabled=(not uploaded_file)):
        if not sender_email or not app_password:
            st.error("Please configure your Sender Email and App Password in the sidebar.")
            append_log("Workflow aborted: Missing SMTP credentials", error=True)
            return
            
        st.session_state.workflow_started = True
        st.session_state.workflow_completed = False
        st.session_state.logs = [] # Clear previous logs
        append_log("Initializing Agentic AI Workflow...")

        # Step 1: Intelligent Parsing
        with st.spinner("Extracting text and parsing with Gemini..."):
            append_log("Reading PDF Resume...")
            resume_text = extract_text_from_pdf(uploaded_file)
            
            if not resume_text:
                append_log("Failed to extract text from PDF.", error=True)
                st.error("Could not extract text. Check the PDF format.")
                return
                
            append_log("Analyzing resume content via LLM Agent...")
            candidate_info = parse_resume_agent(resume_text)
            
            # Apply Override Logic
            if manual_role_input:
                append_log(f"Applying manual role override: {manual_role_input}")
                candidate_info["role"] = manual_role_input
                
            st.session_state.parsed_resume = candidate_info
            append_log(f"Analysis Complete -> Role: {candidate_info.get('role')} | Level: {candidate_info.get('experience_level')}")
            
            st.markdown("#### Parsed Candidate Profile")
            st.json(candidate_info)

        # Step 2: Simulated Discovery
        with st.spinner("Simulating Job Discovery..."):
            append_log(f"Initiating Discovery Agent for {candidate_info.get('role')} positions in {preferred_loc}...")
            mock_jobs = job_discovery_agent(candidate_info.get('role'), preferred_loc)
            st.session_state.mock_jobs = mock_jobs
            st.session_state.jobs_identified = len(mock_jobs)
            append_log(f"Discovered {len(mock_jobs)} targeted opportunities.")
            
            st.markdown("#### Discovered Opportunities")
            st.dataframe(pd.DataFrame(mock_jobs))

        # Step 3: The Dispatch Loop
        st.markdown("#### Dispatching Applications")
        dispatch_container = st.empty()
        
        for index, job in enumerate(mock_jobs):
            company = job.get("company_name", f"Company {index+1}")
            title = job.get("job_title", "Software Engineer")
            recipient = job.get("contact_email", "hr@example.com")
            
            with st.spinner(f"Processing Application for {company}..."):
                append_log(f"--- Processing {index+1}/{len(mock_jobs)}: {company} ---")
                
                # 3.1: Generate Cover Letter
                append_log(f"Generating hyper-personalized cover letter targeting {title} at {company}...")
                cover_letter = cover_letter_agent(candidate_info, company, title)
                if cover_letter.startswith("Dear") and "A Dedicated Professional" in cover_letter:
                    append_log("Notice: Used fallback template for cover letter.", fallback=True)
                
                st.markdown(f"**Generated Letter for {company}:**")
                st.text_area("Cover Letter Preview", value=cover_letter, height=150, key=f"cl_{index}", disabled=True)
                
                # 3.2 & 3.3: Attach PDF and Dispatch (with rate limiting / logs inside smtplib handler)
                append_log(f"Preparing dispatch to {recipient} (Includes 20s rate limit buffer)...")
                st.toast(f"Waiting 20 seconds before dispatching to {company}...")
                
                subject = f"Application for {title} - {candidate_info.get('role')}"
                
                # We simulate sending if it's an example.com to avoid actually bothering real servers unless real email is provided.
                if "example" in recipient:
                    append_log(f"Mocking sent email to {recipient} (Simulated 3s delay)...")
                    time.sleep(3)
                    success = True
                else:
                    success = send_email_with_attachment(
                        sender_email=sender_email,
                        app_password=app_password,
                        recipient_email=recipient,
                        subject=subject,
                        body=cover_letter,
                        attachment_bytes=st.session_state.pdf_bytes,
                        filename=st.session_state.pdf_filename
                    )
                
                if success:
                    st.session_state.successful_dispatches += 1
                    append_log(f"Successfully dispatched application to {company} ✅")
                else:
                    append_log(f"Failed to dispatch to {company} ❌", error=True)

        # Step 4: Post-Process Value
        with st.spinner("Generating Interview Prep Guide..."):
            append_log("Initializing Post-Process Action: Interview Prep Agent...")
            prep_guide = interview_prep_agent(candidate_info.get("role"))
            st.session_state.interview_questions = prep_guide
            append_log("Interview Guide ready.")
        
        st.session_state.workflow_completed = True
        st.balloons()
        append_log("🎉 ALL TASKS COMPLETED. Agent going to sleep.")

    # Show results if completed
    if st.session_state.workflow_completed:
        st.markdown("### 💡 Interview Preparation Guide")
        st.markdown("Based on your targeted roles, here are 10 tailored interview questions:")
        st.info(st.session_state.interview_questions)

    # Always render logs at the end so it stays at the bottom
    render_logs()

if __name__ == "__main__":
    main()
