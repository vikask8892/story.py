import requests, os, smtplib, urllib.parse, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# CONFIG
EMAIL_SENDER = str(os.environ.get('EMAIL_USER', ''))
EMAIL_PASSWORD = str(os.environ.get('EMAIL_PASS', ''))
GEMINI_KEY = str(os.environ.get('GEMINI_API_KEY', ''))

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    
    prompt = """
    Write a 500-word gripping narrative based on a TRUE, rare historical event or a hidden biography of a real person.
    
    The goal: Provide a life-changing mental model or strategy through a real story.
    
    Structure:
    1. THE HOOK: A high-stakes moment in a real person's life.
    2. THE STRUGGLE: A problem relevant to modern life (ego, fear, focus).
    3. THE RARE INSIGHT: The non-obvious way they solved it.
    4. THE MODERN APPLICATION: How the reader uses this 'tool' tomorrow.
    5. THE CHALLENGE: A one-sentence '24-hour mission' for the reader.

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
        
        # Advanced extraction
        title = re.search(r"TITLE:(.*)", full_text, re.I).group(1).strip()
        challenge = re.search(r"CHALLENGE:(.*)", full_text, re.I).group(1).strip()
        visual = re.search(r"VISUAL:(.*)", full_text, re.I).group(1).strip()
        story = full_text.split("STORY:")[1].split("CHALLENGE:")[0].strip()

        encoded_visual = urllib.parse.quote(visual)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_visual}?width=1000&height=600&nologo=true"
        
        return title, story.replace('\n', '<br>'), challenge, image_url
    except Exception as e:
        print(f"Error: {e}")
        return "The Silent Protocol", "The archives are being updated.", "Observe one moment of silence.", ""

def send_story():
    title, story, challenge, image_url = get_wisdom_package()
    
    msg = MIMEMultipart()
    msg['Subject'] = f"The Midnight Scroll: {title}"
    
    html = f"""
    <div style="font-family: 'Georgia', serif; background: #0a0a0a; padding: 20px; color: #fff;">
        <div style="max-width: 650px; margin: auto; background: #111; border: 1px solid #ffd700; padding: 30px;">
            <h1 style="text-align: center; color: #ffd700; text-transform: uppercase; letter-spacing: 2px; font-size: 28px;">{title}</h1>
            <div style="text-align: center; font-size: 10px; color: #555; margin-bottom: 20px;">EST. 2026 | SCROLL NO. {datetime.now().timetuple().tm_yday}</div>
            
            <img src="{image_url}" style="width: 100%; border: 1px solid #222;">
            
            <div style="font-size: 17px; line-height: 1.8; text-align: justify; color: #ccc; margin-top: 25px;">
                {story}
            </div>
            
            <div style="margin-top: 40px; background: #ffd700; color: #000; padding: 20px; border-radius: 5px;">
                <h3 style="margin: 0; font-size: 14px; text-transform: uppercase;">⚡ The 24-Hour Challenge</h3>
                <p style="margin: 5px 0 0 0; font-size: 16px; font-weight: bold;">{challenge}</p>
            </div>
            
            <p style="text-align: center; margin-top: 30px; font-size: 11px; color: #444;">You are receiving this because you seek the rare. <br> Tomorrow, the scroll continues.</p>
        </div>
    </div>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
    print("Midnight Scroll sent with Action Challenge.")

if __name__ == "__main__":
    send_story()
