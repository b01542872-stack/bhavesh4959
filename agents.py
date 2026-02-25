import json
import streamlit as st
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# Configure the LLM using Streamlit secrets/state
def configure_genai():
    api_key = ""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass # Handle missing secrets file
        
    if not api_key:
        api_key = st.session_state.get("gemini_api_key", "")
        
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def call_gemini_with_fallback(prompt: str, fallback_response: str, json_format=False) -> str:
    """Wraps Gemini API calls in a try-except block to gracefully degrade if quota is exceeded."""
    if not configure_genai():
        return fallback_response

    try:
        if json_format:
            model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
        else:
            model = genai.GenerativeModel("gemini-1.5-pro")
            
        response = model.generate_content(prompt)
        return response.text
    except ResourceExhausted:
        st.warning("Gemini API Quota Exceeded (429). Using Fallback Template Engine.")
        return fallback_response
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return fallback_response

def parse_resume_agent(resume_text: str) -> dict:
    """Parses resume text and returns structured JSON {role, skills, experience_level}"""
    prompt = f"""
    Analyze the following resume and extract the key information into a JSON format.
    The output must strictly be a JSON object with the following keys:
    - "role": The primary job title or role described (e.g., "Full-Stack Engineer", "Data Scientist").
    - "skills": A list of top 5-10 technical and soft skills.
    - "experience_level": "Entry", "Mid", "Senior", or "Executive".
    
    Resume Text:
    {resume_text}
    """
    
    fallback_json = json.dumps({
        "role": "Software Engineer", 
        "skills": ["Python", "Problem Solving", "Communication"], 
        "experience_level": "Mid"
    })
    
    response = call_gemini_with_fallback(prompt, fallback_response=fallback_json, json_format=True)
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return json.loads(fallback_json)

def job_discovery_agent(role: str, location: str) -> list:
    """Simulates job discovery and returns 3 mock opportunities."""
    prompt = f"""
    Generate exactly 3 mock job opportunities for a {role} in {location}.
    Return output as a JSON array of objects. Each object must have:
    - "company_name": Fictional tech company name.
    - "job_title": The specific role title.
    - "contact_email": <company>@example.recruiting.com
    """
    
    fallback_json = json.dumps([
        {"company_name": "TechNova Solutions", "job_title": f"Senior {role}", "contact_email": "careers@technova.example.com"},
        {"company_name": "Quantum Innovations", "job_title": f"Lead {role}", "contact_email": "hr@quantuminnovations.example.com"},
        {"company_name": "CloudNine Systems", "job_title": f"{role}", "contact_email": "jobs@cloudninesystems.example.com"}
    ])
    
    response = call_gemini_with_fallback(prompt, fallback_response=fallback_json, json_format=True)
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return json.loads(fallback_json)

def cover_letter_agent(candidate_info: dict, company_name: str, job_title: str) -> str:
    """Generates a highly personalized cover letter."""
    prompt = f"""
    Write a professional and hyper-personalized cover letter.
    Candidate Role: {candidate_info.get('role')}
    Candidate Experience Level: {candidate_info.get('experience_level')}
    Candidate Skills: {', '.join(candidate_info.get('skills', []))}
    
    Target Company: {company_name}
    Target Job Title: {job_title}
    
    Keep it concise, structured, and persuasive. Do not use placeholders like [Your Name]. Use placeholder tags like <CANDIDATE_NAME> instead if needed.
    """
    
    fallback_text = f"Dear Hiring Manager at {company_name},\n\nI am writing to express my strong interest in the {job_title} role. With my background in {candidate_info.get('role')} and experience in {', '.join(candidate_info.get('skills', [])[:3])}, I am confident I would be a valuable addition to your team.\n\nPlease find my resume attached.\n\nBest regards,\nA Dedicated Professional"
    
    return call_gemini_with_fallback(prompt, fallback_response=fallback_text)

def interview_prep_agent(role: str) -> str:
    """Generates 10 tailored interview questions based on the role."""
    prompt = f"""
    Generate exactly 10 tailored interview preparation questions for a {role} position.
    Include a mix of technical, behavioral, and architectural questions appropriate for this role.
    Format as a numbered markdown list.
    """
    
    fallback_text = "1. Tell me about yourself.\n2. What are your greatest strengths?\n3. Describe a challenging project you worked on.\n4. How do you handle tight deadlines?\n5. Where do you see yourself in 5 years?\n6. Why do you want to work here?\n7. Describe a time you disagreed with a coworker.\n8. How do you stay updated with industry trends?\n9. What is your preferred work environment?\n10. Do you have any questions for us?"
    
    return call_gemini_with_fallback(prompt, fallback_response=fallback_text)
