import requests, os, smtplib, urllib.parse, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# CONFIG
EMAIL_SENDER = str(os.environ.get('EMAIL_USER', '')).strip()
EMAIL_PASSWORD = str(os.environ.get('EMAIL_PASS', '')).strip()
GEMINI_KEY = str(os.environ.get('GEMINI_API_KEY', '')).strip()

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    
    # Calculate a sequence number based on days passed since Jan 1st
    day_of_year = datetime.now().timetuple().tm_yday
    
    prompt = f"""
    Today is Day {day_of_year} of the journey. 
    Act as a wise philosopher who speaks to Gen Z. 
    
    TASK:
    1. Identify the verse from Bhagvad Gita corresponding to this sequence (start from Chapter 1, Verse 1 and move forward daily).
    2. Provide:
       - SANSKRIT: The Shloka.
       - HINDI: The meaning written in Hindi Devanagari script.
       - VIBE CHECK: A 1-sentence Gen Z summary (Hinglish allowed).
       - STORY: A 500-word gripping, modern-day story (English/Hinglish) illustrating this specific verse. 
       - CHALLENGE: A practical 24-hour mission.
       - VISUAL: A prompt for an oil painting of this scene.

    Format EXACTLY:
    VERSE: [Sanskrit]
    HINDI: [Hindi Meaning]
    VIBE: [Summary]
    STORY: [Narrative]
    CHALLENGE: [Mission]
    VISUAL: [Image Prompt]
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
        raw_story = extract("STORY", full_text)

        # Drop Cap for Storybook Feel
        first_letter = raw_story[0]
        remaining_story = raw_story[1:].replace('\n', '<br>')
        story_html = f"""<span style="float: left; color: #b8922e; font-size: 70px; line-height: 60px; padding-top: 4px; padding-right: 8px; font-weight: bold; font-family: serif;">{first_letter}</span>{remaining_story}"""

        image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(visual)}?width=1000&height=600&nologo=true"
        
        return shloka, hindi, vibe, story_html, challenge, image_url
    except Exception as e:
        print(f"Error: {e}")
        return "Shloka loading...", "Bhavarth loading...", "Vibe check failing.", "Story loading...", "", ""

def send_story():
    if not EMAIL_SENDER: return
    shloka, hindi, vibe, story, challenge, image_url = get_wisdom_package()
    
    msg = MIMEMultipart()
    msg['Subject'] = f"The Gita Code | Day {datetime.now().timetuple().tm_yday}"
    msg['From'] = f"The Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    html = f"""
    <div style="background-color: #fdfaf5; padding: 30px 10px; font-family: 'Georgia', serif; color: #2c3e50;">
        <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 40px; border-radius: 4px; border: 1px solid #e0dcd0; box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
            
            <div style="text-align: center; border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 30px;">
                <p style="text-transform: uppercase; letter-spacing: 3px; font-size: 11px; color: #a68b5a;">The Eternal Song • Series I</p>
                <div style="font-size: 20px; color: #1a252f; margin: 20px 0; font-weight: bold; line-height: 1.6;">{shloka}</div>
                <div style="font-size: 18px; color: #5d4037; font-style: italic;">{hindi}</div>
            </div>

            <div style="background: #fffcf0; border-left: 4px solid #b8922e; padding: 15px; margin-bottom: 30px; font-size: 16px;">
                <strong>VIBE CHECK:</strong> {vibe}
            </div>

            <img src="{image_url}" style="width: 100%; border-radius: 2px; margin-bottom: 30px;">
            
            <div style="font-size: 19px; line-height: 1.8; text-align: justify; color: #34495e;">
                {story}
            </div>
            
            <div style="margin-top: 40px; padding: 25px; background-color: #f9f7f2; border: 1px dashed #b8922e; border-radius: 10px; text-align: center;">
                <p style="font-size: 12px; text-transform: uppercase; letter-spacing: 2px; color: #a68b5a;">Daily Dharma Mission</p>
                <p style="font-size: 19px; font-weight: bold; color: #1a252f; margin: 10px 0;">{challenge}</p>
            </div>

            <div style="text-align: center; margin-top: 40px; font-size: 20px;">🪷</div>
        </div>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))
    with smtplib.SMTP('smtp.gmail.com', 587) as s:
        s.starttls()
        s.login(EMAIL_SENDER, EMAIL_PASSWORD)
        s.sendmail(EMAIL_SENDER, [EMAIL_SENDER], msg.as_string())

if __name__ == "__main__":
    send_story()
