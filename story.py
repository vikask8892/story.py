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
    Write a 500-word gripping narrative based on a TRUE, rare historical event or a hidden biography.
    Goal: Provide a life-changing strategy through a real story.
    
    Format EXACTLY like this:
    TITLE: [Name of Strategy]
    STORY: [The 500-word narrative]
    CHALLENGE: [One sentence action step]
    VISUAL: [Cinematic, realistic image description]
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        data = response.json()
        full_text = data['candidates'][0]['content']['parts'][0]['text']
        
        # Robust Extraction Logic
        def extract(label, text):
            pattern = rf"{label}:(.*?)(?=\n[A-Z]+:|$)"
            match = re.search(pattern, text, re.S | re.I)
            return match.group(1).strip() if match else ""

        title = extract("TITLE", full_text) or "The Midnight Scroll"
        challenge = extract("CHALLENGE", full_text) or "Apply this lesson today."
        visual = extract("VISUAL", full_text) or "Cinematic historical setting"
        
        # Story is usually the largest block, we'll grab it specifically
        try:
            story = full_text.split("STORY:")[1].split("CHALLENGE:")[0].strip()
        except:
            story = "The archives are being updated. Reflection is the key."

        encoded_visual = urllib.parse.quote(visual)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_visual}?width=1000&height=600&nologo=true"
        
        return title, story.replace('\n', '<br>'), challenge, image_url
    except Exception as e:
        print(f"Content Generation Error: {e}")
        return "The Silent Protocol", "The archives are sealed.", "Breathe deeply for 1 minute.", ""

def send_story():
    # Validation
    if not EMAIL_SENDER or "@" not in EMAIL_SENDER:
        print("ERROR: Invalid or missing EMAIL_USER secret.")
        return

    title, story, challenge, image_url = get_wisdom_package()
    print(f"PROCESSED: {title}")
    print(f"CHALLENGE: {challenge}")
    
    msg = MIMEMultipart()
    msg['Subject'] = f"The Midnight Scroll: {title}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_SENDER  # Explicitly setting the recipient
    
    html = f"""
    <div style="font-family: 'Georgia', serif; background: #0a0a0a; padding: 20px; color: #fff;">
        <div style="max-width: 650px; margin: auto; background: #111; border: 1px solid #ffd700; padding: 30px;">
            <h1 style="text-align: center; color: #ffd700; text-transform: uppercase; letter-spacing: 2px;">{title}</h1>
            <img src="{image_url}" style="width: 100%; border: 1px solid #222; margin: 20px 0;">
            <div style="font-size: 17px; line-height: 1.8; text-align: justify; color: #ccc;">
                {story}
            </div>
            <div style="margin-top: 40px; background: #ffd700; color: #000; padding: 20px;">
                <h3 style="margin: 0; font-size: 14px; text-transform: uppercase;">⚡ The 24-Hour Challenge</h3>
                <p style="margin: 5px 0 0 0; font-size: 16px; font-weight: bold;">{challenge}</p>
            </div>
        </div>
    </div>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            # Using sendmail for maximum compatibility with all Python versions
            server.sendmail(EMAIL_SENDER, [EMAIL_SENDER], msg.as_string())
        print("Success: Midnight Scroll dispatched.")
    except Exception as e:
        print(f"SMTP Delivery Error: {e}")

if __name__ == "__main__":
    send_story()
