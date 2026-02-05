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

# Day 1 was Feb 2, 2026
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

def safe_encode(text):
    """Prevents PDF crashes by removing non-Latin-1 characters."""
    if not text: return "N/A"
    # Replace common smart quotes/dashes that break FPDF
    text = text.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    # Remove Hindi/Sanskrit/Emojis for PDF compatibility (Latin-1 only)
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def get_wisdom_package():
    # Using the 2.5-flash-lite model as requested
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    day, ch, v = get_current_verse_info()
    
    prompt = f"""
    Explain Bhagavad Gita CHAPTER {ch}, VERSE {v} for Day {day}.
    Provide the response in this EXACT format with these tags:
    [SHLOKA]: (Sanskrit)
    [HINDI]: (Hindi Translation)
    [VIBE]: (One sentence vibe check)
    [TITLE]: (Catchy 3-word title)
    [STORY]: (Modern-day story, exactly 400 words)
    [CHALLENGE]: (Actionable task)
    [VISUAL]: (AI image prompt)
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        res_json = response.json()
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label):
            match = re.search(rf"\[{label}\]\s*:?\s*(.*?)(?=\n\s*\[|$)", full_text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""

        # Enforce the 400-word limit manually if AI over-generates
        story = extract("STORY")
        story_words = story.split()
        if len(story_words) > 400:
            story = " ".join(story_words[:400]) + "..."

        return {
            "shloka": extract("SHLOKA"), "hindi": extract("HINDI"),
            "vibe": extract("VIBE"), "title": extract("TITLE"),
            "challenge": extract("CHALLENGE"), "visual": extract("VISUAL"),
            "story": story, "day": day, "ch": ch, "v": v
        }
    except Exception as e:
        print(f"API Error: {e}")
        return None

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # Header - Modern syntax
    pdf.set_font("helvetica", 'B', 10)
    pdf.set_text_color(166, 139, 90)
    pdf.cell(0, 10, f"THE GITA CODE | DAY {data['day']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    # Title
    pdf.set_font("helvetica", 'B', 22)
    pdf.set_text_color(26, 37, 47)
    pdf.multi_cell(0, 12, safe_encode(data['title']).upper(), align='C')
    
    # Vibe
    pdf.ln(5)
    pdf.set_font("helvetica", 'I', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 8, f"Vibe: {safe_encode(data['vibe'])}", align='C')
    
    # Verse Info
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, f"Chapter {data['ch']}, Verse {data['v']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Content (Safe Encodings for PDF)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 7, f"Sanskrit: {safe_encode(data['shloka'])}")
    pdf.ln(2)
    pdf.multi_cell(0, 7, f"Hindi: {safe_encode(data['hindi'])}")
    
    # Story
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "THE MODERN TALE", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 7, safe_encode(data['story']))
    
    # Challenge
    pdf.ln(10)
    pdf.set_fill_color(26, 37, 47)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", 'B', 12)
    pdf.multi_cell(0, 12, f"  DAILY CHALLENGE: {safe_encode(data['challenge'])}", fill=True)
    
    filename = f"Gita_Day_{data['day']}.pdf"
    pdf.output(filename)
    return filename

def run_delivery():
    data = get_wisdom_package()
    if not data: return
        
    pdf_path = create_pdf(data)
    
    # Clean visual prompt for URL
    clean_visual = re.sub(r'[^a-zA-Z0-9 ]', '', data['visual'])
    image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_visual)}?width=1000&height=600&seed={uuid.uuid4().hex}&nologo=true"

    msg = MIMEMultipart()
    msg['Subject'] = f"Gita Day {data['day']} | {data['title']}"
    msg['From'] = f"Gita Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    # Handle the "drop cap" first letter for HTML
    first_letter = data['story'][0] if data['story'] else "T"
    story_body = data['story'][1:].replace('\n', '<br>')

    html = f"""
    <div style="font-family: 'Georgia', serif; background: #fdfaf5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 30px; border-top: 10px solid #d4af37; border-radius: 10px;">
            <p style="text-align: center; color: #a68b5a; text-transform: uppercase; font-size: 12px; letter-spacing: 2px;">Day {data['day']} • Verse {data['ch']}.{data['v']}</p>
            <h1 style="text-align: center; color: #1a252f; margin-top: 10px;">{data['title']}</h1>
            <p style="text-align: center; font-style: italic; color: #7f8c8d; margin-bottom: 30px;">"{data['vibe']}"</p>
            
            <div style="text-align: center; margin: 25px 0; background: #fff9ed; padding: 20px; border-radius: 5px; border-left: 5px solid #d4af37;">
                <p style="font-size: 20px; color: #5d4037; margin-bottom: 10px;"><b>{data['shloka']}</b></p>
                <p style="font-size: 17px; color: #8d6e63;">{data['hindi']}</p>
            </div>
            
            <img src="{image_url}" style="width: 100%; border-radius: 8px; margin: 20px 0;">
            
            <div style="font-size: 19px; line-height: 1.8; text-align: justify; color: #2c3e50;">
                <b style="font-size: 50px; color: #b8922e; float: left; line-height: 40px; padding-top: 10px; padding-right: 10px;">{first_letter}</b>{story_body}
            </div>
            
            <div style="clear: both; background: #1a252f; color: #fff; padding: 25px; text-align: center; margin-top: 40px; border-radius: 8px;">
                <p style="margin: 0; font-size: 12px; color: #d4af37; text-transform: uppercase; letter-spacing: 1px;">Today's Mission</p>
                <p style="margin: 10px 0 0 0; font-size: 20px;">{data['challenge']}</p>
            </div>
            <p style="text-align: center; margin-top: 30px; font-size: 30px;">🪷</p>
        </div>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))

    with open(pdf_path, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="
