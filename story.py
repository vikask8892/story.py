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

def clean_for_pdf(text):
    """Replaces smart quotes/dashes and removes markdown to prevent PDF crashes."""
    if not text: return ""
    # Remove markdown stars
    text = re.sub(r'\*+', '', text)
    # Replace smart/unicode characters with ASCII equivalents
    replacements = {
        '\u2018': "'", '\u2019': "'",  # Smart single quotes
        '\u201c': '"', '\u201d': '"',  # Smart double quotes
        '\u2013': '-', '\u2014': '-',  # En and Em dashes
        '\u2022': '-',                # Bullet points
        '\u2026': '...',              # Ellipsis
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    day_of_year = datetime.now().timetuple().tm_yday
    
    prompt = f"""
    Today is Day {day_of_year} of the Gita journey. 
    Identify the verse from Bhagvad Gita (Sequence: Chapter 1, Verse 1 onwards).
    
    Format EXACTLY like this:
    [SHLOKA]: (Sanskrit only)
    [HINDI]: (Hindi translation only)
    [VIBE]: (One sentence Gen Z summary)
    [TITLE]: (Catchy 3-4 word title)
    [STORY]: (500-word modern story)
    [CHALLENGE]: (One sentence mission)
    [VISUAL]: (Image prompt description)
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        data = response.json()
        full_text = data['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label, text):
            pattern = rf"\[{label}\]:(.*?)(?=\n\[|$)"
            match = re.search(pattern, text, re.S | re.I)
            return match.group(1).strip() if match else ""

        # Clean all extracted fields for PDF safety
        shloka = extract("SHLOKA", full_text)
        hindi = extract("HINDI", full_text)
        vibe = clean_for_pdf(extract("VIBE", full_text))
        title = clean_for_pdf(extract("TITLE", full_text)) or f"Day {day_of_year}"
        challenge = clean_for_pdf(extract("CHALLENGE", full_text))
        visual = extract("VISUAL", full_text)
        raw_story = clean_for_pdf(extract("STORY", full_text))

        # Drop Cap for Email
        first_letter = raw_story[0] if raw_story else "T"
        remaining_story = raw_story[1:].replace('\n', '<br>') if raw_story else ""
        story_html = f"""<span style="float: left; color: #b8922e; font-size: 70px; line-height: 60px; padding-top: 4px; padding-right: 8px; font-weight: bold; font-family: serif;">{first_letter}</span>{remaining_story}"""

        image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(visual)}?width=1000&height=600&nologo=true"
        
        return shloka, hindi, vibe, story_html, raw_story, challenge, image_url, title
    except Exception as e:
        print(f"Extraction Error: {e}")
        return None

def create_pdf(title, shloka, hindi, vibe, raw_story, challenge):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    font_path = 'NotoSansDevanagari-Regular.ttf'
    has_unicode_font = os.path.exists(font_path)
    
    if has_unicode_font: 
        pdf.add_font('GitaFont', '', font_path)
        main_font = 'GitaFont'
    else:
        main_font = 'helvetica'

    # 1. Header
    pdf.set_font(main_font if has_unicode_font else "helvetica", 'B', 10)
    pdf.set_text_color(166, 139, 90)
    pdf.cell(0, 10, text="THE GITA CODE - SERIES I", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # 2. Title
    pdf.set_font(main_font if has_unicode_font else "times", 'B', 24)
    pdf.set_text_color(26, 37, 47)
    pdf.multi_cell(0, 15, text=title.upper(), align='C')
    pdf.ln(10)

    # 3. Verse (Sanskrit & Hindi)
    pdf.set_font(main_font, '', 14)
    pdf.set_text_color(93, 64, 55)
    pdf.multi_cell(0, 10, text=shloka, align='C')
    pdf.ln(5)
    pdf.set_font(main_font, '', 12)
    pdf.multi_cell(0, 8, text=hindi, align='C')
    pdf.ln(10)

    # 4. Vibe Check
    pdf.set_fill_color(252, 251, 247)
    pdf.set_font(main_font if has_unicode_font else "helvetica", 'B', 11)
    pdf.set_text_color(184, 146, 46)
    pdf.cell(0, 10, text="VIBE CHECK", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(main_font if has_unicode_font else "helvetica", '', 11)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 7, text=vibe)
    pdf.ln(10)

    # 5. The Story
    pdf.set_font(main_font if has_unicode_font else "times", '', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.multi_cell(0, 8, text=raw_story, align='J')
    pdf.ln(15)

    # 6. Challenge Footer
    pdf.set_fill_color(26, 37, 47)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(main_font if has_unicode_font else "helvetica", 'B', 12)
    pdf.multi_cell(0, 15, text=f"MISSION: {challenge}", align='C', fill=True)

    filename = f"Gita_Code_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf.output(filename)
    return filename

def send_story():
    package = get_wisdom_package()
    if not package: return
    shloka, hindi, vibe, story_html, raw_story, challenge, image_url, title = package
    
    pdf_file = create_pdf(title, shloka, hindi, vibe, raw_story, challenge)
    
    msg = MIMEMultipart()
    msg['Subject'] = f"📜 The Gita Code | {title}"
    msg['From'] = f"The Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    html_body = f"""
    <div style="background-color: #fdfaf5; padding: 30px 10px; font-family: 'Georgia', serif; color: #2c3e50;">
        <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 40px; border-top: 8px solid #d4af37; border: 1px solid #e0dcd0;">
            <div style="text-align: center;">
                <p style="text-transform: uppercase; letter-spacing: 3px; font-size: 11px; color: #a68b5a;">The Eternal Song</p>
                <h1 style="color: #1a252f; font-size: 32px;">{title}</h1>
                <div style="font-size: 18px; font-style: italic; color: #5d4037; margin: 20px 0;">{shloka}<br><br>{hindi}</div>
            </div>
            <img src="{image_url}" style="width: 100%; border-radius: 4px; margin: 20px 0;">
            <div style="font-size: 19px; line-height: 1.8; text-align: justify;">{story_html}</div>
            <div style="margin-top: 30px; padding: 25px; background: #1a252f; color: #fff; text-align: center; border-radius: 8px;">
                <p style="font-size: 11px; text-transform: uppercase; color: #d4af37;">24-Hour Mission</p>
                <p style="font-size: 18px; font-weight: bold; margin: 5px 0;">{challenge}</p>
            </div>
        </div>
    </div>
    """
    msg.attach(MIMEText(html_body, 'html'))
    
    if os.path.exists(pdf_file):
        with open(pdf_file, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header('Content-Disposition', 'attachment', filename=pdf_file)
            msg.attach(part)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_SENDER, [EMAIL_SENDER], msg.as_string())
        print("Success: Story & Unicode-Safe PDF delivered.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    send_story()
