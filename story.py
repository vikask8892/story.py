import requests, os, smtplib, urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# CONFIG
EMAIL_SENDER = os.environ.get('EMAIL_USER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASS')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    
    # The "Master Prompt" for 500 words of rare wisdom
    prompt = """
    Write a 500-word deep, immersive, and rare story. 
    Theme: A life-changing concept (e.g., Entropy, Stoic Fortitude, or the Butterfly Effect).
    Style: Cinematic, impressive, and rare. Not a generic 'be positive' story. 
    It should appeal to smart people and feel like a high-end comic or a short film.
    
    At the very end, add the label 'VISUAL:' followed by a 1-sentence cinematic 
    description for an image generator.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload, timeout=60)
    data = response.json()
    full_text = data['candidates'][0]['content']['parts'][0]['text']
    
    # Splitting Story and Image Prompt
    if "VISUAL:" in full_text:
        story, visual = full_text.split("VISUAL:")
    else:
        story, visual = full_text, "A cosmic eye watching the birth of a star, cinematic lighting"
    
    # Generate FREE Image URL
    encoded_visual = urllib.parse.quote(visual.strip())
    image_url = f"https://image.pollinations.ai/prompt/{encoded_visual}?width=1000&height=600&nologo=true&seed={datetime.now().day}"
    
    return story.replace('\n', '<br>'), image_url

def send_story():
    story, image_url = get_wisdom_package()
    today = datetime.now().strftime("%d %b %Y")
    
    msg = MIMEMultipart()
    msg['Subject'] = f"The Midnight Scroll: {today}"
    
    # Comic-style HTML Layout
    html = f"""
    <div style="font-family: 'Courier New', Courier, monospace; background: #0a0a0a; padding: 20px; color: #eee;">
        <div style="max-width: 650px; margin: auto; background: #1a1a1a; border: 3px solid #ffd700; padding: 30px;">
            <h1 style="text-align: center; color: #ffd700; text-transform: uppercase; letter-spacing: 5px;">THE MIDNIGHT SCROLL</h1>
            <p style="text-align: center; font-size: 12px; color: #888; margin-bottom: 25px;">ENTRY NO. {datetime.now().timetuple().tm_yday}</p>
            
            <img src="{image_url}" style="width: 100%; border: 1px solid #ffd700; filter: grayscale(20%);">
            
            <div style="font-size: 18px; line-height: 1.8; margin-top: 30px; text-align: justify; color: #fff;">
                {story}
            </div>
            
            <div style="margin-top: 40px; border-top: 1px dashed #ffd700; padding-top: 20px; text-align: center;">
                <p style="font-style: italic; color: #ffd700;">Pass this scroll to someone who seeks the truth.</p>
            </div>
        </div>
    </div>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_SENDER, msg.as_string())

if __name__ == "__main__":
    send_story()
