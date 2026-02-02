import requests, os, smtplib, urllib.parse, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# CONFIG
EMAIL_SENDER = os.environ.get('EMAIL_USER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASS')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

def get_wisdom_package():
    # Using 2.5-flash-lite as we discussed
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    
    prompt = """
    Write a 500-word deep, immersive story for a group of smart readers. 
    Theme: A rare, life-changing concept (like 'Antifragility', 'The Lindy Effect', or 'Sunk Cost Fallacy').
    Style: Narrative, cinematic, and impressive. Build a world and explain the deep insight within the story.
    
    Format EXACTLY like this:
    TITLE: [Name]
    STORY: [The 500-word content]
    VISUAL: [1-sentence cinematic prompt]
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    response = requests.post(url, json=payload, timeout=90)
    data = response.json()
    
    # DEBUG: This will show in your GitHub logs if it fails again
    if 'candidates' not in data:
        print(f"API Error Response: {data}")
        return "The Silent Scroll", "The archives are temporarily sealed. Please check back at midnight.", "A mysterious sealed stone door"

    full_text = data['candidates'][0]['content']['parts'][0]['text']
    
    # Safer extraction logic
    title_match = re.search(r"TITLE:(.*)", full_text)
    visual_match = re.search(r"VISUAL:(.*)", full_text)
    
    title = title_match.group(1).strip() if title_match else "The Midnight Scroll"
    visual = visual_match.group(1).strip() if visual_match else "Cinematic mystery lighting"
    
    try:
        # Extract story between STORY: and VISUAL:
        story = full_text.split("STORY:")[1].split("VISUAL:")[0].strip()
    except:
        story = full_text # Fallback to full text if split fails

    # Generate Image
    encoded_visual = urllib.parse.quote(visual)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_visual}?width=1000&height=600&nologo=true"
    
    return title, story.replace('\n', '<br>'), image_url

def send_story():
    title, story, image_url = get_wisdom_package()
    
    msg = MIMEMultipart()
    msg['Subject'] = f"The Midnight Scroll: {title}"
    
    html = f"""
    <div style="font-family: 'Georgia', serif; background: #050505; padding: 20px; color: #fff;">
        <div style="max-width: 650px; margin: auto; background: #111; border: 2px solid #ffd700; padding: 30px; box-shadow: 0 0 20px #000;">
            <h1 style="text-align: center; color: #ffd700; text-transform: uppercase; letter-spacing: 3px;">{title}</h1>
            <hr style="border: 0; border-top: 1px solid #333; margin: 20px 0;">
            
            <img src="{image_url}" style="width: 100%; border: 1px solid #ffd700;">
            
            <div style="font-size: 17px; line-height: 1.8; text-align: justify; color: #ddd; margin-top: 25px;">
                {story}
            </div>
            
            <p style="text-align: center; margin-top: 40px; font-size: 12px; color: #555;">&copy; 2026 The Midnight Scroll</p>
        </div>
    </div>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_SENDER, msg.as_string())
    print("Scroll delivered successfully.")

if __name__ == "__main__":
    send_story()
