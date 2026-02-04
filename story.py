import requests, os, smtplib, urllib.parse, re, uuid
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
    text = re.sub(r'\*+', '', text)
    replacements = {'\u2018':"'", '\u2019':"'", '\u201c':'"', '\u201d':'"', '\u2013':'-', '\u2014':'-'}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('ascii', 'ignore').decode('ascii')

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    day, ch, v = get_current_verse_info()
    
    prompt = f"""
    Today is Day {day}. Explain Bhagavad Gita CHAPTER {ch}, VERSE {v}.
    Format EXACTLY like this:
    [SHLOKA]: (Sanskrit)
    [HINDI]: (Hindi translation)
    [VIBE]: (One sentence Gen Z summary)
    [TITLE]: (Catchy title)
    [STORY]: (500-word modern story)
    [CHALLENGE]: (One sentence mission)
    [VISUAL]: (Image prompt)
    """
    
    try:
        response = requests.post(url, json=payload := {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.0}}, timeout=90)
        full_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label):
            match = re.search(rf"\[{label}\]:(.*?)(?=\n\[|$)", full_text, re.S)
            return match.group(1).strip() if match else ""

        raw_story = clean_for_pdf(extract("STORY"))
        first_letter = raw_story[0] if raw_story else "T"
        story_body_html = raw_story[1:].replace('\n', '<br>')
        
        return {
            "shloka": extract("SHLOKA"), "hindi": extract("HINDI"), "vibe": extract("VIBE"),
            "title": clean_for_pdf(extract("TITLE")), "challenge": extract("CHALLENGE"),
            "story_html": f'<b style="font-size:50px; color:#b8922e;">{first_letter}</b>{story_body_html}',
            "raw_story": raw_story, "day": day, "ch": ch, "v": v, 
            "visual": extract("VISUAL")
        }
    except: return None

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    font_path = 'NotoSansDevanagari-Regular.ttf'
    if os.path.exists(font_path):
        pdf.add_font('GitaFont', '', font_path); pdf.add_font('GitaFont', 'B', font_path)
        pdf.set_font('GitaFont', '', 12)
    else: pdf.set_font('helvetica', '', 12)

    pdf.set_text_color(166, 139, 90)
    pdf.cell(0, 10, f"DAY {data['day']} | CHAPTER {data['ch']} VERSE {data['v']}", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(pdf.font_family, 'B', 22); pdf.set_text_color(26, 37, 47)
    pdf.multi_cell(0, 15, data['title'].upper(), align='C')
    pdf.ln(5)
    pdf.set_font(pdf.font_family, '', 12); pdf.multi_cell(0, 8, data['raw_story'], align='J')
    
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
    msg['Subject'] = f"Gita Code Day {data['day']} | {data['title']} [REF:{unique_ref}]"
    msg['From'] = f"Gita Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    html_content = f"""
    <div style="font-family: serif; color: #2c3e50; background: #fdfaf5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 30px; border-top: 5px solid #d4af37;">
            <p style="text-align: center; color: #a68b5a;">DAY {data['day']} • VERSE {data['ch']}.{data['v']}</p>
            <h1 style="text-align: center;">{data['title']}</h1>
            <div style="text-align: center; font-style: italic; margin: 20px;">{data['shloka']}<br>{data['hindi']}</div>
            <img src="{image_url}" style="width: 100%; border-radius: 5px;">
            <div style="font-size: 18px; line-height: 1.6; margin-top: 20px;">{data['story_html']}</div>
            <div style="background: #1a252f; color: #fff; padding: 20px; text-align: center; margin-top: 30px;">
                <b>MISSION:</b> {data['challenge']}
            </div>
        </div>
    </div>
    """
    msg.attach(MIMEText(html_content, 'html'))

    with open(pdf_name, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment', filename=pdf_name)
        msg.attach(attach)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Success! Day {data['day']} delivered with full content.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_delivery()
