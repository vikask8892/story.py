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

# Set this to Feb 2nd so today is Day 1
START_DATE = datetime(2026, 2, 2) 

# Gita Chapter Lengths
GITA_CH_LENGTHS = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78]

def get_current_day_number():
    """Calculates days passed since START_DATE."""
    delta = datetime.now() - START_DATE
    return delta.days + 1  # 1 today, 2 tomorrow

def get_current_verse_ref(day_num):
    """Maps day number to specific Ch and Verse."""
    count = 0
    for ch_idx, length in enumerate(GITA_CH_LENGTHS):
        if day_num <= count + length:
            return ch_idx + 1, day_num - count
        count += length
    return 1, 1

def clean_for_pdf(text):
    """Removes problematic characters that crash the PDF generator."""
    if not text: return ""
    text = re.sub(r'\*+', '', text)
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2022': '-', '\u2026': '...',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()

def get_wisdom_package():
    # Using gemini-2.0-flash for high-speed consistent responses
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    
    day_num = get_current_day_number()
    chapter, verse = get_current_verse_ref(day_num)
    
    prompt = f"""
    Today is Day {day_num} of the Gita journey. 
    TASK: Explain Bhagavad Gita CHAPTER {chapter}, VERSE {verse}.
    
    Format EXACTLY like this:
    [SHLOKA]: (Sanskrit of Ch {chapter}.{verse})
    [HINDI]: (Hindi translation)
    [VIBE]: (One sentence Gen Z summary)
    [TITLE]: (Catchy 3-4 word title)
    [STORY]: (500-word modern story reflecting Ch {chapter}.{verse})
    [CHALLENGE]: (One sentence mission)
    [VISUAL]: (Cinematic image prompt)
    """
    
    # temperature: 0.0 makes the AI response deterministic (identical every run today)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        data = response.json()
        full_text = data['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label, text):
            pattern = rf"\[{label}\]:(.*?)(?=\n\[|$)"
            match = re.search(pattern, text, re.S | re.I)
            return match.group(1).strip() if match else ""

        shloka = extract("SHLOKA", full_text)
        hindi = extract("HINDI", full_text)
        vibe = clean_for_pdf(extract("VIBE", full_text))
        title = clean_for_pdf(extract("TITLE", full_text))
        challenge = clean_for_pdf(extract("CHALLENGE", full_text))
        visual = extract("VISUAL", full_text)
        raw_story = clean_for_pdf(extract("STORY", full_text))

        # --- FIX: Move string processing outside the f-string to avoid backslash error ---
        first_letter = raw_story[0] if raw_story else "T"
        story_body_html = raw_story[1:].replace('\n', '<br>')
        story_html = f"""<span style="float: left; color: #b8922e; font-size: 70px; line-height: 60px; padding-top: 4px; padding-right: 8px; font-weight: bold;">{first_letter}</span>{story_body_html}"""
        
        image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(visual)}?width=1000&height=600&nologo=true"
        
        return shloka, hindi, vibe, story_html, raw_story, challenge, image_url, title, day_num, chapter, verse
    except Exception as e:
        print(f"Extraction Error: {e}")
        return None

def create_pdf(title, shloka, hindi, vibe, raw_story, challenge, day, ch, v):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()
    
    font_path = 'NotoSansDevanagari-Regular.ttf'
    has_font = os.path.exists(font_path)
    if has_font:
        pdf.add_font('GitaFont', '', font_path)
        pdf.add_font('GitaFont', 'B', font_path)
        main_font = 'GitaFont'
    else:
        main_font = 'helvetica'

    # 1. Header (Includes Day Number)
    pdf.set_font(main_font, 'B', 10)
    pdf.set_text_color(166, 139, 90)
    pdf.cell(0, 10, text=f"THE GITA CODE - DAY {day} | CHAPTER {ch}, VERSE {v}", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # 2. Title
    pdf.set_font(main_font, 'B', 24)
    pdf.set_text_color(26, 37, 47)
    pdf.multi_cell(0, 15, text=title.upper(), align='C')
    pdf.ln(10)

    # 3. Verse
    pdf.set_font(main_font, '', 14)
    pdf.set_text_color(93, 64, 55)
    pdf.multi_cell(0, 10, text=shloka, align='C')
    pdf.ln(5)
    pdf.set_font(main_font, '', 12)
    pdf.multi_cell(0, 8, text=hindi, align='C')
    pdf.ln(10)

    # 4. Vibe Check
    pdf.set_fill_color(252, 251, 247)
    pdf.set_font(main_font, 'B', 11)
    pdf.set_text_color(184, 146, 46)
    pdf.cell(0, 10, text="VIBE CHECK", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(main_font, '', 11)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 7, text=vibe)
    pdf.ln(10)

    # 5. Story
    pdf.set_font(main_font, '', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.multi_cell(0, 8, text=raw_story, align='J')
    pdf.ln(20)

    # 6. Mission Footer
    pdf.set_fill_color(26, 37, 47)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(main_font, 'B', 12)
    pdf.multi_cell(0, 15, text=f"MISSION: {challenge}", align='C', fill=True)
    
    # 7. Lotus Image (Centered Bottom)
    try:
        # High-resolution golden lotus icon
        lotus_url = "https://cdn-icons-png.flaticon.com/512/2913/2913459.png"
        pdf.image(lotus_url, x=95, y=pdf.h - 25, w=15)
    except:
        # Text fallback if URL fails
        pdf.set_y(pdf.h - 25)
        pdf.set_font(main_font, '', 20)
        pdf.set_text_color(184, 146, 46)
        pdf.cell(0, 10, text="~ * ~", align='C')

    filename = f"Gita_Code_Day_{day}.pdf"
    pdf.output(filename)
    return filename

def send_story():
    package = get_wisdom_package()
    if not package: return
    shloka, hindi, vibe, story_html, raw_story, challenge, image_url, title, day, ch, v = package
    
    pdf_file = create
