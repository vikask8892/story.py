import requests, os, smtplib, urllib.parse, re
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

# Forced Start Date for Day 1
START_DATE = datetime(2026, 2, 2) 
GITA_CH_LENGTHS = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78]

def get_current_day_number():
    delta = datetime.now() - START_DATE
    return max(1, delta.days + 1)

def get_current_verse_ref(day_num):
    count = 0
    for ch_idx, length in enumerate(GITA_CH_LENGTHS):
        if day_num <= count + length:
            return ch_idx + 1, day_num - count
        count += length
    return 1, 1

def clean_for_pdf(text):
    if not text: return ""
    text = re.sub(r'\*+', '', text)
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2022': '-', '\u2026': '...',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('ascii', 'ignore').decode('ascii') # Strict cleaning

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    day_num = get_current_day_number()
    chapter, verse = get_current_verse_ref(day_num)
    
    prompt = f"Bhagavad Gita Chapter {chapter} Verse {verse}. Format: [SHLOKA], [HINDI], [VIBE], [TITLE], [STORY], [CHALLENGE], [VISUAL]."
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        res_data = response.json()
        full_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label, text):
            pattern = rf"\[{label}\]:(.*?)(?=\n\[|$)"
            match = re.search(pattern, text, re.S | re.I)
            return match.group(1).strip() if match else ""

        raw_story = clean_for_pdf(extract("STORY", full_text))
        first_letter = raw_story[0] if raw_story else "O"
        story_body_html = raw_story[1:].replace('\n', '<br>')
        
        return {
            "shloka": extract("SHLOKA", full_text),
            "hindi": extract("HINDI", full_text),
            "vibe": clean_for_pdf(extract("VIBE", full_text)),
            "title": clean_for_pdf(extract("TITLE", full_text)),
            "challenge": clean_for_pdf(extract("CHALLENGE", full_text)),
            "visual": extract("VISUAL", full_text),
            "raw_story": raw_story,
            "story_html": f'<b style="font-size:50px; color:#b8922e;">{first_letter}</b>{story_body_html}',
            "day": day_num, "ch": chapter, "v": verse
        }
    except Exception as e:
        print(f"AI/Extraction Error: {e}")
        return None

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    font_path = 'NotoSansDevanagari-Regular.ttf'
    if os.path.exists(font_path):
        pdf.add_font('GitaFont', '', font_path)
        pdf.add_font('GitaFont', 'B', font_path)
        pdf.set_font('GitaFont', '', 12)
    else:
        pdf.set_font('helvetica', '', 12)

    # Content
    pdf.set_text_color(166, 139, 90)
    pdf.cell(0, 10, f"DAY {data['day']} | CHAPTER {data['ch']} VERSE {data['v']}", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(pdf.font_family, 'B', 20)
    pdf.set_text_color(26, 37, 47)
    pdf.multi_cell(0, 15, data['title'].upper(), align='C')
    pdf.ln(10)
    pdf.set_font(pdf.font_family, '', 12)
    pdf.multi_cell(0, 8, data['raw_story'], align='J')
    
    # Lotus
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
    
    msg = MIMEMultipart()
    # Adding a timestamp to the subject to bypass Gmail "Duplicate" filtering
    msg['Subject'] = f"Gita Code: Day {data['day']} ({datetime.now().strftime('%H:%M')})"
    msg['From'] = f"Gita Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    msg.attach(MIMEText(f"Day {data['day']} is here. See attached PDF for the full experience.", 'plain'))

    with open(pdf_name, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment', filename=pdf_name)
        msg.attach(attach)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_SENDER, msg.as_string())
        server.quit()
        print(f"Delivered Day {data['day']} successfully.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    run_delivery()
