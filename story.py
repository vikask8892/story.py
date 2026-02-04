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

# Day calculation logic
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
    replacements = {'\u2018':"'", '\u2019':"'", '\u201c':'"', '\u201d':'"', '\u2013':'-', '\u2014':'-'}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('ascii', 'ignore').decode('ascii')

def get_wisdom_package():
    # UPDATED: Using 2.0-flash-lite for peak free-tier performance
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={GEMINI_KEY}"
    day, ch, v = get_current_verse_info()
    
    prompt = f"""
    Explain Bhagavad Gita CHAPTER {ch}, VERSE {v} for Day {day} of a 365-day journey.
    Provide content in this EXACT format:
    [SHLOKA]: (Sanskrit)
    [HINDI]: (Hindi)
    [VIBE]: (Gen-Z summary)
    [TITLE]: (Catchy title)
    [STORY]: (500-word modern-day story)
    [CHALLENGE]: (Daily task)
    [VISUAL]: (AI image prompt)
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_json = response.json()
        
        if 'candidates' not in res_json:
            print(f"API Error: {json.dumps(res_json)}")
            return None

        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label):
            match = re.search(rf"\[{label}\]:(.*?)(?=\n\[|$)", full_text, re.S)
            return match.group(1).strip() if match else ""

        raw_story = clean_for_pdf(extract("STORY"))
        first_letter = raw_story[0] if raw_story else "O"
        story_html = f'<b style="font-size:50px; color:#b8922e;">{first_letter}</b>{raw_story[1:].replace("\n", "<br>")}'
        
        return {
            "shloka": extract("SHLOKA"), "hindi": extract("HINDI"),
            "title": clean_for_pdf(extract("TITLE")), "challenge": extract("CHALLENGE"),
            "story_html": story_html, "raw_story": raw_story, 
            "day": day, "ch": ch, "v": v, "visual": extract("VISUAL")
        }
    except Exception as e:
        print(f"Fetch Error: {e}")
        return None

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(166, 139, 90)
    pdf.cell(0, 10, f"THE GITA CODE | DAY {data['day']} | CHAPTER {data['ch']} VERSE {data['v']}", align='C', ln=True)
    pdf.set_font('helvetica', 'B', 24); pdf.set_text_color(26, 37, 47)
    pdf.multi_cell(0, 15, data['title'].upper(), align='C')
    pdf.ln(10)
    pdf.set_font('helvetica', '', 12); pdf.set_text_color(44, 62, 80)
    pdf.multi_cell(0, 8, data['raw_story'], align='J')
    
    # Tiny Lotus footer
    try:
        pdf.image("https://cdn-icons-png.flaticon.com/512/2913/2913459.png", x=95, y=pdf.h - 25, w=15)
    except: pass
    
    filename = f"Gita_Day_{data['day']}.pdf"
    pdf.output(filename)
    return filename

def run_delivery():
    data = get_wisdom_package()
    if not data: return
        
    pdf_name = create_pdf(data)
    image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(data['visual'])}?width=1000&height=600&nologo=true"

    msg = MIMEMultipart()
    msg['Subject'] = f"Gita Code Day {data['day']} | {data['title']}"
    msg['From'] = f"The Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    html_content = f"""
    <div style="font-family: serif; background: #fdfaf5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 40px; border-top: 10px solid #d4af37; border-radius: 10px;">
            <p style="text-align: center; color: #a68b5a; text-transform: uppercase; font-size: 11px;">Day {data['day']} • Verse {data['ch']}.{data['v']}</p>
            <h1 style="text-align: center; color: #1a252f; font-size: 30px;">{data['title']}</h1>
            <div style="text-align: center; font-style: italic; margin: 30px 0; color: #5d4037; border-left: 3px solid #d4af37; padding-left: 15px;">
                <p>{data['shloka']}</p><p>{data['hindi']}</p>
            </div>
            <img src="{image_url}" style="width: 100%; border-radius: 8px;">
            <div style="font-size: 19px; line-height: 1.8; text-align: justify; margin-top: 25px;">{data['story_html']}</div>
            <div style="background: #1a252f; color: #fff; padding: 30px; text-align: center; margin-top: 40px; border-radius: 8px;">
                <p style="margin: 0; font-size: 18px; font-weight: bold;">{data['challenge']}</p>
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
        print(f"Delivered Day {data['day']} successfully!")
    except Exception as e:
        print(f"Email Error: {e}")

if __name__ == "__main__":
    run_delivery()
