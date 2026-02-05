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

def safe_pdf_text(text, label="Content"):
    """
    CLEANER: Strips non-ASCII but GUARANTEES a non-empty string 
    to prevent the 'Horizontal Space' FPDF crash.
    """
    if not text or not str(text).strip():
        return f"{label}: [See Email for full text]"
    
    # Replace common symbols that break encoding
    text = text.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
    
    # Strip non-ASCII (Hindi/Sanskrit/Emojis)
    cleaned = text.encode('ascii', 'ignore').decode('ascii').strip()
    
    # FINAL GUARD: If cleaning left us with nothing, return a placeholder
    if not cleaned or len(cleaned) < 1:
        return f"{label}: [Script text available in Email body]"
    return cleaned

def get_wisdom_package():
    # Model: gemini-2.5-flash-lite
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    day, ch, v = get_current_verse_info()
    
    prompt = f"""
    Explain Bhagavad Gita CHAPTER {ch}, VERSE {v} for Day {day}.
    Provide the response in this EXACT format:
    [SHLOKA]: (Sanskrit)
    [HINDI]: (Hindi Translation)
    [VIBE]: (One sentence vibe check)
    [TITLE]: (Catchy 3-word title)
    [STORY]: (Modern-day story applying this verse, MAXIMUM 400 words)
    [CHALLENGE]: (One specific task)
    [VISUAL]: (AI image prompt)
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        res_json = response.json()
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label):
            match = re.search(rf"\[{label}\]\s*:?\s*(.*?)(?=\n\s*\[|$)", full_text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""

        story_content = extract("STORY")
        # Enforce 400-word limit
        words = story_content.split()
        if len(words) > 400:
            story_content = " ".join(words[:400]) + "..."

        return {
            "shloka": extract("SHLOKA"), "hindi": extract("HINDI"),
            "vibe": extract("VIBE"), "title": extract("TITLE"),
            "challenge": extract("CHALLENGE"), "visual": extract("VISUAL"),
            "story": story_content, "day": day, "ch": ch, "v": v
        }
    except Exception as e:
        print(f"API Error: {e}")
        return None

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Header
    pdf.set_font("helvetica", 'B', 10)
    pdf.set_text_color(166, 139, 90)
    pdf.cell(0, 10, f"THE GITA CODE | DAY {data['day']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    # 2. Title (Bold & Large)
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 22)
    pdf.set_text_color(26, 37, 47)
    pdf.multi_cell(0, 12, safe_pdf_text(data['title'], "Title").upper(), align='C')
    
    # 3. Vibe Check
    pdf.ln(5)
    pdf.set_font("helvetica", 'I', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 8, f"Vibe: {safe_pdf_text(data['vibe'], 'Vibe')}", align='C')
    
    # 4. Verse Info
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, f"Chapter {data['ch']}, Verse {data['v']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # 5. Shloka & Hindi (Handled with safe_pdf_text to prevent crashes)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 7, f"Sanskrit: {safe_pdf_text(data['shloka'], 'Sanskrit Script')}")
    pdf.ln(2)
    pdf.multi_cell(0, 7, f"Hindi: {safe_pdf_text(data['hindi'], 'Hindi Translation')}")
    
    # 6. The Story
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "THE MODERN TALE", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 7, safe_pdf_text(data['story'], "Story"))
    
    # 7. Challenge Block
    pdf.ln(10)
    pdf.set_fill_color(26, 37, 47)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", 'B', 12)
    pdf.multi_cell(0, 12, f"  MISSION: {safe_pdf_text(data['challenge'], 'Challenge')}", fill=True)
    
    filename = f"Gita_Day_{data['day']}.pdf"
    pdf.output(filename)
    return filename

def run_delivery():
    data = get_wisdom_package()
    if not data: return
        
    pdf_path = create_pdf(data)
    
    # Image URL Logic
    clean_visual = re.sub(r'[^a-zA-Z0-9 ]', '', data['visual'])
    image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_visual)}?width=1000&height=600&seed={uuid.uuid4().hex}&nologo=true"

    msg = MIMEMultipart()
    msg['Subject'] = f"Gita Day {data['day']} | {data['title']}"
    msg['From'] = f"Gita Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    # Dropcap for Email HTML
    f_letter = data['story'][0] if data['story'] else "T"
    s_body = data['story'][1:].replace('\n', '<br>')

    html = f"""
    <div style="font-family: serif; background: #fdfaf5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 30px; border-top: 10px solid #d4af37; border-radius: 10px;">
            <p style="text-align: center; color: #a68b5a; text-transform: uppercase; font-size: 11px;">Day {data['day']} • Verse {data['ch']}.{data['v']}</p>
            <h1 style="text-align: center; color: #1a252f;">{data['title']}</h1>
            <p style="text-align: center; font-style: italic; color: #7f8c8d; margin-bottom: 30px;">{data['vibe']}</p>
            
            <div style="text-align: center; margin: 25px 0; background: #fff9ed; padding: 20px; border-left: 5px solid #d4af37;">
                <p style="font-size: 19px; color: #5d4037; margin-bottom: 10px;"><b>{data['shloka']}</b></p>
                <p style="font-size: 17px; color: #8d6e63;">{data['hindi']}</p>
            </div>
            
            <img src="{image_url}" style="width: 100%; border-radius: 8px;">
            
            <div style="font-size: 19px; line-height: 1.8; text-align: justify; color: #2c3e50; margin-top: 25px;">
                <b style="font-size: 50px; color: #b8922e; float: left; line-height: 40px; padding-top: 8px; padding-right: 8px;">{f_letter}</b>{s_body}
            </div>
            
            <div style="clear: both; background: #1a252f; color: #fff; padding: 25px; text-align: center; margin-top: 40px; border-radius: 8px;">
                <p style="margin: 0; font-size: 11px; color: #d4af37; text-transform: uppercase;">Today's Mission</p>
                <p style="margin: 10px 0 0 0; font-size: 19px;">{data['challenge']}</p>
            </div>
            <p style="text-align: center; margin-top: 30px; font-size: 30px;">🪷</p>
        </div>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))

    # Safe Attachment
    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header('Content-Disposition', 'attachment', filename=pdf_path)
        msg.attach(part)

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
