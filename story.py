import requests, os, smtplib, urllib.parse, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# CONFIG - Using str() to force string type and avoid the 'bytes' error
EMAIL_SENDER = str(os.environ.get('EMAIL_USER', ''))
EMAIL_PASSWORD = str(os.environ.get('EMAIL_PASS', ''))
GEMINI_KEY = str(os.environ.get('GEMINI_API_KEY', ''))

def get_wisdom_package():
    # Validation check
    if not GEMINI_KEY or GEMINI_KEY == "None":
        return "Key Missing", "The API Key is not being read from GitHub Secrets.", "Error icon"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    
    prompt = """
    Write a 500-word deep story for smart readers. 
    Theme: A rare life-changing concept. Style: Cinematic.
    Format:
    TITLE: [Name]
    STORY: [The 500-word content]
    VISUAL: [1-sentence cinematic prompt]
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        data = response.json()
        
        if 'candidates' not in data:
            print(f"DEBUG API RESPONSE: {data}")
            return "Archive Locked", f"Google API Error: {data.get('error', {}).get('message', 'Unknown')}", "Locked door"

        full_text = data['candidates'][0]['content']['parts'][0]['text']
        
        title_match = re.search(r"TITLE:(.*)", full_text)
        visual_match = re.search(r"VISUAL:(.*)", full_text)
        
        title = title_match.group(1).strip() if title_match else "The Midnight Scroll"
        visual = visual_match.group(1).strip() if visual_match else "Cinematic mystery"
        
        try:
            story = full_text.split("STORY:")[1].split("VISUAL:")[0].strip()
        except:
            story = full_text 

        encoded_visual = urllib.parse.quote(visual)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_visual}?width=1000&height=600&nologo=true"
        
        return title, story.replace('\n', '<br>'), image_url
    except Exception as e:
        return "Connection Error", str(e), "Static noise"

def send_story():
    # Final check before attempting SMTP
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("CRITICAL: Email credentials missing!")
        return

    title, story, image_url = get_wisdom_package()
    
    msg = MIMEMultipart()
    msg['Subject'] = f"The Midnight Scroll: {title}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_SENDER
    
    html = f"""
    <div style="font-family: 'Georgia', serif; background: #050505; padding: 20px; color: #fff;">
        <div style="max-width: 650px; margin: auto; background: #111; border: 2px solid #ffd700; padding: 30px;">
            <h1 style="text-align: center; color: #ffd700; text-transform: uppercase;">{title}</h1>
            <hr style="border: 0; border-top: 1px solid #333; margin: 20px 0;">
            <img src="{image_url}" style="width: 100%; border: 1px solid #ffd700;">
            <div style="font-size: 17px; line-height: 1.8; text-align: justify; color: #ddd; margin-top: 25px;">
                {story}
            </div>
        </div>
    </div>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    try:
        # SMTP logic with explicit string conversion for credentials
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Success: Scroll delivered.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    send_story()
