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
    if not text: return "Wisdom Loading..."
    # FPDF (basic) only likes Latin-1/ASCII. This prevents "nil" PDFs.
    text = text.replace('\n', '  ').replace('*', '')
    return text.encode('ascii', 'ignore').decode('ascii')

def get_wisdom_package():
    # Using the exact model version you specified
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    day, ch, v = get_current_verse_info()
    
    prompt = f"""
    Explain Bhagavad Gita CHAPTER {ch}, VERSE {v} for Day {day}.
    Provide exactly these sections:
    [SHLOKA]: (Sanskrit)
    [HINDI]: (Hindi)
    [VIBE]: (Short summary)
    [TITLE]: (3-word title)
    [STORY]: (500-word modern story)
    [CHALLENGE]: (Daily task)
    [VISUAL]: (AI image prompt)
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}}
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_json = response.json()
        
        # Guard against empty response
        if 'candidates' not in res_json:
            print(f"API Error: {res_json}")
            return None
            
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label):
            match = re.search(rf"\[{label}\]\s*:(.*?)(?=\n\s*\[|$)", full_text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""

        # Robust extraction: if the tag fails, we take a slice of the full text so it's never empty
        raw_story = extract("STORY") or full_text[:1000]
        clean_story = clean_for_pdf(raw_story)
        
        # Fixing the f-string backslash error by processing here
        first_letter = clean_story[0] if clean_story else "G"
        story_body = clean_story[1:].replace('  ', '<br><br>')
        
        return {
            "shloka": extract("SHLOKA") or "Sanskrit Verse",
            "hindi": extract("HINDI") or "Hindi Translation",
            "title": clean_for_pdf(extract("TITLE") or "Daily Wisdom"),
            "challenge": extract("CHALLENGE") or "Reflect on today's lesson.",
            "story_html": f'<b style="font-size:50px; color:#b8922e;">{first_letter}</b>{story_body}',
            "raw_story": clean_story,
            "day": day, "ch": ch, "v": v,
            "visual": extract("VISUAL") or "Cinematic spiritual sunrise"
        }
    except Exception as e:
        print(f"System Error: {e}")
        return None

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Day {data['day']} - Chapter {data['ch']}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 20)
    pdf.multi_cell(0, 10, data['title'].upper(), align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    # This writes the story safely into the PDF
    pdf.multi_cell(0, 8, data['raw_story'])
    
    filename = f"Gita_Day_{data['day']}.pdf"
    pdf.output(filename)
    return filename

def run_delivery():
    data = get_wisdom_package()
    if not data:
        print("Failed to fetch data. Check API key and model name.")
        return
        
    pdf_name = create_pdf(data)
    # Proper URL encoding for the image prompt
    img_prompt = urllib.parse.quote(data['visual'])
    image_url = f"https://image.pollinations.ai/prompt/{img_prompt}?width=1000&height=600&nologo=true"

    msg = MIMEMultipart()
    msg['Subject'] = f"Gita Day {data['day']} | {data['title']}"
    msg['From'] = f"Gita Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    html = f"""
    <div style="font-family: 'Georgia', serif; background: #fdfaf5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 30px; border-top: 10px solid #d4af37; border-radius: 10px;">
            <p style="text-align: center; color: #a68b5a; text-transform: uppercase;">Day {data['day']} • Verse {data['ch']}.{data['v']}</p>
            <h1 style="text-align: center; color: #1a252f;">{data['title']}</h1>
            <div style="text-align: center; font-style: italic; margin: 25px; color: #5d4037; background: #fff9ed; padding: 15px;">
                {data['shloka']}<br><br>{data['hindi']}
            </div>
            <img src="{image_url}" style="width: 100%; border-radius: 8px; margin-bottom: 20px;">
            <div style="font-size: 18px; line-height: 1.8; text-align: justify;">{data['story_html']}</div>
            <div style="background: #1a252f; color: #fff; padding: 25px; text-align: center; margin-top: 30px; border-radius: 8px;">
                <p style="margin: 0; font-size: 18px;"><b>TODAY'S TASK:</b> {data['challenge']}</p>
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
