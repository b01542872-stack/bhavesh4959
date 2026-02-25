import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pypdf import PdfReader
import streamlit as st

def extract_text_from_pdf(pdf_file) -> str:
    """Extracts text from an uploaded PDF file."""
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            extract = page.extract_text()
            if extract:
                text += extract + "\n"
        return text
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return ""

def send_email_with_attachment(sender_email: str, app_password: str, recipient_email: str, 
                               subject: str, body: str, attachment_bytes: bytes, filename: str) -> bool:
    """
    Sends an email with an attachment using Gmail's SMTP server.
    Implements 20s rate limiting and error handling for Auth.
    """
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    if attachment_bytes:
        part = MIMEApplication(attachment_bytes, Name=filename)
        part['Content-Disposition'] = f'attachment; filename="{filename}"'
        msg.attach(part)
        
    try:
        # Rate limiting rule application: Sleep 20s before sending
        st.info(f"Rate limiting: Waiting 20 seconds before dispatching email to {recipient_email}...")
        time.sleep(20)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        st.error("SMTP Authentication Error: Please verify your Email and App Password.")
        return False
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False
