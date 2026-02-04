import requests, os, smtplib, urllib.parse, re, uuid, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- CONFIG ---
EMAIL_SENDER = str(os.environ.get('EMAIL_USER', '')).strip()
EMAIL_PASSWORD = str(os.environ.get('EMAIL_PASS', '')).strip()
GEMINI_KEY = str(os.environ.get('GEMINI_API_KEY', '')).strip()

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

def clean_for_pdf(text):
    if not text: return ""
    # Standardize quotes and dashes for PDF compatibility
    replacements = {
        '\u2018':"'", '\u2019':"'", '\u201c':'"', '\u201d':'"', 
        '\u2013':'-', '\u2014':'-', '\u2022':'-'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('ascii', 'ignore').decode('ascii')

def get_wisdom_package():
    # SWITCHED TO 2.0 FLASH: High speed, high intelligence
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    day, ch, v = get_current_verse_info()
    
    prompt = f"""
    Act as a wise modern storyteller. Today is Day {day}. 
    Explain Bhagavad Gita CHAPTER {ch}, VERSE {v}.
    
    Return the content in this EXACT format:
    [SHLOKA]: (Sanskrit text)
    [HINDI]: (Hindi translation)
    [VIBE]: (One-sentence Gen-Z vibe check)
    [TITLE]: (Catchy 3-word title)
    [STORY]: (A 500-word modern story about a character facing a challenge related to this verse)
    [CHALLENGE]: (A concrete action for the reader today)
    [VISUAL]: (Detailed cinematic AI image prompt)
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 1.0}, # Higher temp for more creative storytelling
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        res_json = response.json()
        
        if 'candidates' not in res_json:
            print(f"DEBUG ERROR: {json.dumps(res_json)}")
            return None

        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label):
            match = re.search(rf"\[{label}\]:(.*?)(?=\n\[|$)", full_text, re.S)
            return match.group(1).strip() if match else ""

        raw_story = clean_for_pdf(extract("STORY"))
        first_letter = raw_story[0] if raw_story else "T"
        story_body_text = raw_story[1:].replace('\n', '<br>')
        story_html = f'<b style="font-size:50px; color:#b8922e;">{first_letter}</b>{story_body_text}'
        
        return {
            "shloka": extract("SHLOKA"), "hindi": extract("HINDI"), "vibe": extract("VIBE"),
            "title": clean_for_pdf(extract("TITLE")), "challenge": extract("CHALLENGE"),
            "story_html": story_html, "raw_story": raw_story, 
            "day": day, "ch": ch, "v": v, "visual": extract("VISUAL")
        }
    except Exception as e:
        print(f"Network/Parse Error: {e}")
        return None

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    # Simple setup to ensure no font-related crashes
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(166, 139, 90)
    pdf.cell(0, 10, f"THE GITA CODE | DAY {data['day']} | CHAPTER {data['ch']} VERSE {data['v']}", align='C', ln=True)
    
    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 24); pdf.set_text_color(26, 37, 47)
    pdf.multi_cell(0, 15, data['title'].upper(), align='C')
    
    pdf.ln(10)
    pdf.set_font('helvetica', '', 12); pdf.set_text_color(44, 62, 80)
    pdf.multi_cell(0, 8, data['raw_story'], align='J')
    
    try:
        lotus = "https://cdn-icons-png.flaticon.com/512/2913/2913459.png"
        pdf.image(lotus, x=95, y=pdf.h - 25, w=15)
    except: pass
    
    filename = f"Gita_Day_{data['day']}.pdf"
    pdf.output(filename)
    return filename

def run_delivery():
    data = get_wisdom_package()
    if not data: return
        
    pdf_name = create_pdf(data)
    unique_ref = str(uuid.uuid4())[:6].upper()
    image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(data['visual'])}?width=1000&height=600&nologo=true"

    msg = MIMEMultipart()
    msg['Subject'] = f"Gita Day {data['day']} | {data['title']} [Ref:{unique_ref}]"
    msg['From'] = f"The Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    html_content = f"""
    <div style="font-family: 'Georgia', serif; color: #2c3e50; background: #fdfaf5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 40px; border-top: 10px solid #d4af37; border-radius: 10px;">
            <p style="text-align: center; color: #a68b5a; letter-spacing: 2px; text-transform: uppercase; font-size: 11px;">Day {data['day']} • Verse {data['ch']}.{data['v']}</p>
            <h1 style="text-align: center; color: #1a252f; font-size: 30px;">{data['title']}</h1>
            <div style="text-align: center; font-style: italic; margin: 30px 0; color: #5d4037; border-left: 3px solid #d4af37; padding-left: 15px;">
                <p style="font-size: 18px;">{data['shloka']}</p>
                <p style="font-size: 16px; color: #8d6e63;">{data['hindi']}</p>
            </div>
            <img src="{image_url}" style="width: 100%; border-radius: 8px; margin-bottom: 25px;">
            <div style="font-size: 19px; line-height: 1.8; text-align: justify;">{data['story_html']}</div>
            <div style="background: #1a252f; color: #fff; padding: 30px; text-align: center; margin-top: 40px; border-radius: 8px;">
                <p style="margin: 0; font-size: 11px; color: #d4af37; text-transform: uppercase;">Your Mission</p>
                <p style="margin: 10px 0 0 0; font-size: 18px; font-weight: bold;">{data['challenge']}</p>
            </div>
            <p style="text-align: center; margin-top: 40px; font-size: 30px;">🪷</p>
        </div>
    </div>
    """
    msg.attach(MIMEText(html_content, 'html'))

    with open(pdf_name, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header('Content-Disposition', 'attachment', filename=pdf_name)
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Success! Day {data['day']} delivered via Gemini 2.0 Flash.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    run_delivery()
