import requests, os, smtplib, urllib.parse, re, uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from fpdf import FPDF

# --- CONFIG ---
EMAIL_SENDER = str(os.environ.get('EMAIL_USER', '')).strip()
EMAIL_PASSWORD = str(os.environ.get('EMAIL_PASS', '')).strip()
GEMINI_KEY = str(os.environ.get('GEMINI_API_KEY', '')).strip()

# Set to Feb 2nd to maintain correct day count
START_DATE = datetime(2026, 2, 2) 
GITA_CH_LENGTHS = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78]

def get_current_verse_info():
    delta = datetime.now() - START_DATE
    day_num = max(1, delta.days + 1)
    
    count = 0
    for ch_idx, length in enumerate(GITA_CH_LENGTHS):
        if day_num <= count + length:
            return day_num, ch_idx + 1, day_num - count
        count += length
    return day_num, 1, 1

def send_gita_code():
    day, ch, v = get_current_verse_info()
    unique_ref = str(uuid.uuid4())[:6].upper()
    
    msg = MIMEMultipart()
    # Unique subject prevents Gmail from collapsing new emails into old test threads
    msg['Subject'] = f"Gita Code Day {day} | Verse {ch}.{v} [REF:{unique_ref}]"
    msg['From'] = f"Gita Wisdom <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    body = f"Your daily Gita Code for Day {day} is ready.\nReference: {unique_ref}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Successfully delivered Day {day} (REF:{unique_ref})")
    except Exception as e:
        print(f"Delivery Failed: {e}")

if __name__ == "__main__":
    send_gita_code()
