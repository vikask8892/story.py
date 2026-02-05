import requests, os, smtplib, urllib.parse, re, uuid, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from fpdf import FPDF

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
    """Standardizes text for PDF. Note: Sanskrit/Hindi requires custom .ttf fonts 
    which aren't standard in FPDF; this cleans them to prevent PDF corruption."""
    if not text: return ""
    # Strip asterisks and non-ASCII characters to prevent PDF crashes
    text = text.replace('*', '').replace('\n', ' ')
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    day, ch, v = get_current_verse_info()
    
    # Prompt explicitly limits story and demands all tags
    prompt = f"""
    Explain Bhagavad Gita CHAPTER {ch}, VERSE {v} for Day {day}. 
    STRICTLY follow this format and include ALL tags:
    
    [SHLOKA]: (The Sanskrit Verse)
    [HINDI]: (A clear Hindi translation)
    [VIBE]: (A cool Gen-Z summary)
    [TITLE]: (A catchy 3-word title)
    [STORY]: (A modern-day story applying this verse, MAXIMUM 400 words)
    [CHALLENGE]: (A specific task for the reader today)
    [VISUAL]: (A detailed description for a cinematic AI image)
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}}
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_json = response.json()
        
        if 'candidates' not in res_json:
            return None
            
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label):
            # Improved regex to handle various spacing styles from Gemini
            match = re.search(rf"\[{label}\]\s*:?\s*(.*?)(?=\n\s*\[|$)", full_text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""

        raw_story = extract("STORY") or full_text[:800]
        # Clean the story for the PDF but keep the original for HTML
        clean_story = clean_for_pdf(raw_story)
        
        # Formatting for HTML email
        first_letter = raw_story[0] if raw_story else "T"
        story_body_html = raw_story[1:].replace('\n', '<br>')

        return {
            "shloka": extract("SHLOKA") or "Verse text unavailable",
            "hindi": extract("HINDI") or "Hindi translation unavailable",
            "vibe": extract("VIBE") or "Daily vibe check",
            "title": extract("TITLE") or "Daily Wisdom",
            "challenge": extract("CHALLENGE") or "Reflect on this verse today.",
            "story_html": f'<b style="font-size:50px; color:#b8922e;">{first_letter}</b>{story_body_html}',
            "raw_story": clean_story,
            "day": day, "ch": ch, "v": v,
            "visual": extract("VISUAL") or "Peaceful spiritual landscape"
        }
    except Exception as e:
        print(f"Extraction Error: {e}")
        return None

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(166, 139, 90)
    pdf.cell(0, 10, f"DAY {data['day']} | CHAPTER {data['ch']} VERSE {data['v']}", ln=True, align='C')
    
    # Title
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(26, 37, 47)
    pdf.multi_cell(0, 12, clean_for_pdf(data['title']).upper(), align='C')
    
    # Vibe Check
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 7, f"Vibe Check: {clean_for_pdf(data['vibe'])}", align='C')
    
    # Shloka & Hindi (Cleaned labels for PDF compatibility)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "THE VERSE & TRANSLATION", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 7, f"Original: {clean_for_pdf(data['shloka'])}")
    pdf.multi_cell(0, 7, f"Hindi: {clean_for_pdf(data['hindi'])}")
    
    # The Story
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "THE MODERN TALE", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, data['raw_story'])
    
    # The Challenge
    pdf.ln(10)
    pdf.set_fill_color(26, 37, 47)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 12, f"  DAILY CHALLENGE: {clean_for_pdf(data['challenge'])}", fill=True)
    
    filename = f"Gita_Code_Day_{data['day']}.pdf"
    pdf.output(filename)
    return filename

def run_delivery():
    data = get_wisdom_package()
    if not data: return
        
    pdf_name = create_pdf(data)
    
    # Pollinations image URL Fix: Ensure the prompt is cleaned and unique
    safe_visual = re.sub(r'[^a-zA-Z0-9 ]', '', data['visual'])
    image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(safe_visual)}?width=1000&height=600&seed={uuid.uuid4().hex}"

    msg = MIMEMultipart()
    msg['Subject'] = f"Gita Day {data['day']} | {data['title']}"
    msg['From'] = f"Gita Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    html = f"""
    <div style="font-family: 'Georgia', serif; background: #fdfaf5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 30px; border-top: 10px solid #d4af37; border-radius: 10px;">
            <p style="text-align: center; color: #a68b5a; text-transform: uppercase; font-size: 12px;">Day {data['day']} • Verse {data['ch']}.{data['v']}</p>
            <h1 style="text-align: center; color: #1a252f; margin-bottom: 5px;">{data['title']}</h1>
            <p style="text-align: center; font-style: italic; color: #7f8c8d; margin-bottom: 25px;">{data['vibe']}</p>
            
            <div style="text-align: center; margin: 25px 0; color: #5d4037; background: #fff9ed; padding: 20px; border-radius: 5px; border-left: 4px solid #d4af37;">
                <p style="font-size: 18px; margin-bottom: 10px;">{data['shloka']}</p>
                <p style="font-size: 16px; color: #8d6e63;">{data['hindi']}</p>
            </div>
            
            <img src="{image_url}" style="width: 100%; border-radius: 8px; margin-bottom: 25px;">
            
            <div style="font-size: 18px; line-height: 1.8; text-align: justify; color: #2c3e50;">
                {data['story_html']}
            </div>
            
            <div style="background: #1a252f; color: #fff; padding: 25px; text-align: center; margin-top: 30px; border-radius: 8px;">
                <p style="margin: 0; font-size: 12px; color: #d4af37; text-transform: uppercase;">Daily Mission</p>
                <p style="margin: 10px 0 0 0; font-size: 18px;"><b>{data['challenge']}</b></p>
            </div>
            <p style="text-align: center; margin-top: 30px; font-size: 30px;">🪷</p>
        </div>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))

    with open(pdf_name, "rb") as f:
        msg.attach(MIMEApplication(f.read(), _subtype="pdf", Name=pdf_name))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"SUCCESS: Day {data['day']} delivered via 2.5-Flash-Lite.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    run_delivery()
