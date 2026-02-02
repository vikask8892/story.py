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
    
    prompt = """
    Write a 500-word gripping, true story about a rare historical event or person.
    Focus on: Human emotion, vivid descriptions, and a life-changing lesson.
    
    Format:
    TITLE: [Beautiful Title]
    STORY: [The 500-word narrative]
    CHALLENGE: [One sentence 24-hour mission]
    VISUAL: [A bright, cinematic, storybook-style illustration description]
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        data = response.json()
        full_text = data['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label, text):
            pattern = rf"{label}:(.*?)(?=\n[A-Z]+:|$)"
            match = re.search(pattern, text, re.S | re.I)
            return match.group(1).strip() if match else ""

        title = extract("TITLE", full_text) or "A Tale for Today"
        challenge = extract("CHALLENGE", full_text) or "Reflect on this story today."
        visual = extract("VISUAL", full_text) or "Soft watercolor painting, cinematic sunlight"
        
        try:
            story = full_text.split("STORY:")[1].split("CHALLENGE:")[0].strip()
        except:
            story = "The pages are being turned. Please wait."

        encoded_visual = urllib.parse.quote(visual)
        # Using a slight artistic filter in the prompt for the storybook look
        image_url = f"https://image.pollinations.ai/prompt/{encoded_visual}%20style%20of%20oil%20painting%20highly%20detailed?width=1000&height=600&nologo=true"
        
        return title, story.replace('\n', '<br>'), challenge, image_url
    except Exception as e:
        return "The Unwritten Chapter", "Error loading story.", "Stay curious.", ""

def send_story():
    if not EMAIL_SENDER or "@" not in EMAIL_SENDER: return

    title, story, challenge, image_url = get_wisdom_package()
    
    msg = MIMEMultipart()
    msg['Subject'] = f"The Daily Tale: {title}"
    msg['From'] = f"The Storyteller <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    # STORYBOOK DESIGN: Cream background (#FFFDF5), Dark Slate text (#2C3E50), and Gold accents
    html = f"""
    <div style="background-color: #f4f1ea; padding: 40px 10px; font-family: 'Georgia', serif;">
        <div style="max-width: 600px; margin: auto; background-color: #fffdf5; padding: 50px; border-radius: 2px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid #e0dcd0;">
            
            <div style="text-align: center; margin-bottom: 40px;">
                <p style="text-transform: uppercase; letter-spacing: 3px; font-size: 12px; color: #a68b5a; margin-bottom: 10px;">Chapter {datetime.now().timetuple().tm_yday}</p>
                <h1 style="font-size: 36px; font-weight: normal; color: #2c3e50; margin: 0; line-height: 1.2;">{title}</h1>
                <div style="width: 50px; height: 2px; background-color: #a68b5a; margin: 20px auto;"></div>
            </div>

            <img src="{image_url}" style="width: 100%; height: auto; border-radius: 4px; margin-bottom: 35px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            
            <div style="font-size: 19px; line-height: 1.8; color: #34495e; text-align: left; orphans: 3; widows: 3;">
                {story}
            </div>
            
            <div style="margin-top: 50px; padding: 30px; border-top: 1px double #e0dcd0; border-bottom: 1px double #e0dcd0; text-align: center; background-color: #fcfbf7;">
                <p style="font-size: 14px; text-transform: uppercase; letter-spacing: 2px; color: #a68b5a; margin-bottom: 10px;">The 24-Hour Mission</p>
                <p style="font-size: 20px; font-style: italic; color: #2c3e50; margin: 0;">"{challenge}"</p>
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <p style="font-size: 12px; color: #95a5a6; font-style: italic;">The End of Today's Lesson. <br> Tomorrow, the ink flows again.</p>
            </div>
        </div>
    </div>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, [EMAIL_SENDER], msg.as_string())
        print("Success: The Storybook edition has been delivered.")
    except Exception as e:
        print(f"Delivery Error: {e}")

if __name__ == "__main__":
    send_story()
