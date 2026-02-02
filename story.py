import requests, os, smtplib, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIG ---
EMAIL_SENDER = str(os.environ.get('EMAIL_USER', '')).strip()
EMAIL_PASSWORD = str(os.environ.get('EMAIL_PASS', '')).strip()
GEMINI_KEY = str(os.environ.get('GEMINI_API_KEY', '')).strip()

START_DATE = datetime(2026, 2, 2) 
GITA_CH_LENGTHS = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78]

def get_current_day_number():
    delta = datetime.now() - START_DATE
    return delta.days + 1 

def get_current_verse_ref(day_num):
    count = 0
    for ch_idx, length in enumerate(GITA_CH_LENGTHS):
        if day_num <= count + length:
            return ch_idx + 1, day_num - count
        count += length
    return 1, 1

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    day_num = get_current_day_number()
    chapter, verse = get_current_verse_ref(day_num)
    
    prompt = f"Explain Bhagavad Gita CHAPTER {chapter}, VERSE {verse}. Provide Shloka, Hindi, Vibe, Title, Story, and Challenge."
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text'], day_num, chapter, verse
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def send_test_email():
    package = get_wisdom_package()
    if not package: return
    content, day, ch, v = package
    
    msg = MIMEMultipart()
    msg['Subject'] = f"DEBUG: Day {day} | Ch {ch} V {v}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_SENDER
    
    # plain text body only
    body = f"GITA JOURNEY - DAY {day}\n\n{content}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        print(f"Attempting to send Day {day} to {EMAIL_SENDER}...")
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_SENDER, [EMAIL_SENDER], msg.as_string())
        print("Success: Text email sent. Check Inbox and SPAM.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    send_test_email()
