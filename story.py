import requests, os, smtplib, urllib.parse, re, uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIG ---
EMAIL_SENDER = str(os.environ.get('EMAIL_USER', '')).strip()
EMAIL_PASSWORD = str(os.environ.get('EMAIL_PASS', '')).strip()
GEMINI_KEY = str(os.environ.get('GEMINI_API_KEY', '')).strip()

START_DATE = datetime(2026, 2, 5)
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

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    day, ch, v = get_current_verse_info()
    
    prompt = f"""
    Write Part {day} of 'Geeta: Echoes of Kurukshetra'. 
    Theme: Chapter {ch}, Verse {v}. 
    
    Format EXACTLY:
    [SHLOKA]: Full Sanskrit
    [HINDI]: Speaker's name + Hindi translation
    [VIBE]: 2 lines of Gen-Z slang vibe check
    [TITLE]: 3-word title
    [STORY]: Part {day} of a rustic Indian serial saga. Simple English. 400 words.
    [CHALLENGE]: One daily action task
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        res_json = response.json()
        
        # ERROR HANDLING FOR 'CANDIDATES'
        if 'candidates' not in res_json:
            print(f"AI Model Error: {res_json}")
            return None
            
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label):
            match = re.search(rf"\[{label}\]\s*:?\s*(.*?)(?=\n\s*\[|$)", full_text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else "Content missing"

        return {
            "shloka": extract("SHLOKA"), 
            "hindi": extract("HINDI"),
            "vibe": extract("VIBE"), 
            "title": extract("TITLE"),
            "challenge": extract("CHALLENGE"), 
            "story": extract("STORY"), 
            "day": day, "ch": ch, "v": v
        }
    except Exception as e:
        print(f"Network/Script Error: {e}")
        return None

def run_delivery():
    data = get_wisdom_package()
    if not data: 
        print("Delivery failed: No data received from AI.")
        return
        
    msg = MIMEMultipart()
    msg['Subject'] = f"Geeta: Echoes of Kurukshetra | Day {data['day']}"
    msg['From'] = f"Geeta: Echoes <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    story_text = data['story']
    first_letter = story_text[0] if story_text else "I"
    story_body = story_text[1:].replace('\n', '<br>')

    html = f"""
    <div style="font-family: 'Helvetica', sans-serif; background: #faf7f2; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 30px; border-top: 10px solid #5d4037; border-radius: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <p style="text-align: center; color: #8d6e63; text-transform: uppercase; font-size: 11px; letter-spacing: 2px; margin-bottom: 5px;">
                Day {data['day']} • Ch {data['ch']}, Verse {data['v']}
            </p>
            <h1 style="text-align: center; color: #3e2723; margin-top: 0; font-size: 26px;">{data['title']}</h1>
            
            <div style="text-align: center; font-style: italic; color: #6d4c41; margin-bottom: 25px; font-weight: bold; font-size: 16px;">
                {data['vibe']}
            </div>
            
            <div style="text-align: center; margin: 20px 0; background: #efebe9; padding: 25px; border-radius: 8px;">
                <p style="font-size: 20px; color: #2e150b; line-height: 1.4; margin-bottom: 12px;"><b>{data['shloka']}</b></p>
                <p style="font-size: 18px; color: #4e342e; line-height: 1.5;">{data['hindi']}</p>
            </div>
            
            <div style="text-align: center; margin: 40px 0;">
                <hr style="border: 0; border-top: 2px solid #efebe9; margin-bottom: 10px;">
                <span style="background: #fff; padding: 0 15px; color: #d7ccc8; font-size: 20px;">✧ ⚜ ✧</span>
                <hr style="border: 0; border-top: 2px solid #efebe9; margin-top: -12px;">
            </div>
            
            <div style="font-size: 18px; line-height: 1.8; text-align: justify; color: #212121;">
                <span style="font-size: 55px; color: #5d4037; float: left; line-height: 45px; padding-top: 8px; padding-right: 12px; font-family: serif; font-weight: bold;">{first_letter}</span>{story_body}
            </div>
            
            <div style="clear: both; background: #3e2723; color: #d7ccc8; padding: 25px; text-align: center; margin-top: 40px; border-radius: 4px;">
                <p style="margin: 0; font-size: 10px; color: #a1887f; text-transform: uppercase; letter-spacing: 1px;">The Daily Step</p>
                <p style="margin: 8px 0 0 0; font-size: 19px; color: #ffffff;">{data['challenge']}</p>
            </div>
            
            <p style="text-align: center; margin-top: 35px; font-size: 24px; color: #8d6e63;">🕉️</p>
        </div>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"SUCCESS: Day {data['day']} delivered.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    run_delivery()
