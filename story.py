import requests, os, smtplib, urllib.parse, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURATION ---
EMAIL_SENDER = str(os.environ.get('EMAIL_USER', '')).strip()
EMAIL_PASSWORD = str(os.environ.get('EMAIL_PASS', '')).strip()
GEMINI_KEY = str(os.environ.get('GEMINI_API_KEY', '')).strip()

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    day_of_year = datetime.now().timetuple().tm_yday
    
    prompt = f"""
    Today is Day {day_of_year} of the Gita journey. 
    TASK:
    1. Identify the verse from Bhagvad Gita starting from Chapter 1, Verse 1.
    2. Provide:
       - VERSE: The Sanskrit Shloka.
       - HINDI: The meaning in Hindi Devanagari.
       - VIBE: A 1-sentence Gen Z summary (Hinglish).
       - STORY: A 500-word modern-day story (English/Hinglish) based on this verse. 
       - CHALLENGE: A practical 24-hour mission.
       - VISUAL: A prompt for a cinematic oil painting.
       - TITLE: A short, catchy title for this story.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        data = response.json()
        full_text = data['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label, text):
            pattern = rf"{label}:(.*?)(?=\n[A-Z ]+:|$)"
            match = re.search(pattern, text, re.S | re.I)
            return match.group(1).strip() if match else ""

        shloka = extract("VERSE", full_text)
        hindi = extract("HINDI", full_text)
        vibe = extract("VIBE", full_text)
        challenge = extract("CHALLENGE", full_text)
        visual = extract("VISUAL", full_text)
        title = extract("TITLE", full_text) or f"Day {day_of_year}"
        raw_story = extract("STORY", full_text)

        # HTML Drop Cap Logic
        first_letter = raw_story[0]
        remaining_story = raw_story[1:].replace('\n', '<br>')
        story_html = f"""<span style="float: left; color: #b8922e; font-size: 70px; line-height: 60px; padding-top: 4px; padding-right: 8px; font-weight: bold; font-family: serif;">{first_letter}</span>{remaining_story}"""

        image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(visual)}?width=1000&height=600&nologo=true"
        
        return shloka, hindi, vibe, story_html, raw_story, challenge, image_url, title
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None

def create_pdf(title, shloka, hindi, vibe, raw_story, challenge):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Hindi Font Support (Requires NotoSansDevanagari-Regular.ttf in repo)
    font_path = 'NotoSansDevanagari-Regular.ttf'
    if os.path.exists(font_path):
        pdf.add_font('HindiFont', '', font_path)
        pdf.set_font('HindiFont', '', 14)
    else:
        pdf.set_font('Arial', '', 12)
        print("Warning: Font file not found. Hindi may not render correctly.")

    # PDF Layout
    pdf.set_text_color(184, 146, 46) 
    pdf.cell(0, 20, txt=f"THE GITA CODE: {title}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_text_color(44, 62, 80)
    pdf.multi_cell(0, 10, txt=f"{shloka}\n\n{hindi}", align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, txt="VIBE CHECK:", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 8, txt=vibe)
    pdf.ln(10)
    
    pdf.set_font("Times", '', 12)
    pdf.multi_cell(0, 8, txt=raw_story)
    pdf.ln(10)
    
    pdf.set_fill_color(249, 247, 242)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 15, txt=f"MISSION: {challenge}", ln=True, align='C', fill=True, border=1)
    
    filename = f"Gita_Code_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf.output(filename)
    return filename

def send_story():
    package = get_wisdom_package()
    if not package: return
    shloka, hindi, vibe, story_html, raw_story, challenge, image_url, title = package
    
    # Generate PDF
    pdf_file = create_pdf(title, shloka, hindi, vibe, raw_story, challenge)
    
    # Prepare Email
    msg = MIMEMultipart()
    msg['Subject'] = f"📜 The Gita Code | {title}"
    msg['From'] = f"The Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    html_body = f"""
    <div style="background-color: #fdfaf5; padding: 30px 10px; font-family: 'Georgia', serif; color: #2c3e50;">
        <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 40px; border-top: 8px solid #d4af37; border: 1px solid #e0dcd0;">
            <div style="text-align: center; margin-bottom: 20px;">
                <p style="text-transform: uppercase; letter-spacing: 3px; font-size: 11px; color: #a68b5a;">The Eternal Song</p>
                <h1 style="color: #1a252f;">{title}</h1>
                <div style="font-size: 18px; font-style: italic; color: #5d4037;">{shloka}<br><br>{hindi}</div>
            </div>
            <div style="background: #fffcf0; border-left: 4px solid #b8922e; padding: 15px; margin: 20px 0;">
                <strong>VIBE CHECK:</strong> {vibe}
            </div>
            <img src="{image_url}" style="width: 100%; border-radius: 4px; margin-bottom: 30px;">
            <div style="font-size: 19px; line-height: 1.8; text-align: justify;">{story_html}</div>
            <div style="margin-top: 40px; padding: 25px; background: #f9f7f2; border: 1px dashed #b8922e; text-align: center; border-radius: 10px;">
                <p style="font-size: 19px; font-weight: bold;">{challenge}</p>
            </div>
        </div>
    </div>
    """
    msg.attach(MIMEText(html_body, 'html'))
    
    # Attach PDF
    if os.path.exists(pdf_file):
        with open(pdf_file, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header('Content-Disposition', 'attachment', filename=pdf_file)
            msg.attach(part)

    # Dispatch
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_SENDER, [EMAIL_SENDER], msg.as_string())
        print("Storybook & PDF delivered successfully.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    send_story()
