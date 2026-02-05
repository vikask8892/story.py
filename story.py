import requests, os, smtplib, urllib.parse, re, uuid, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIG ---
EMAIL_SENDER = str(os.environ.get('EMAIL_USER', '')).strip()
EMAIL_PASSWORD = str(os.environ.get('EMAIL_PASS', '')).strip()
GEMINI_KEY = str(os.environ.get('GEMINI_API_KEY', '')).strip()

# RESTART: Day 1 is now Feb 5, 2026
START_DATE = datetime(2026, 2, 5) 
GITA_CH_LENGTHS = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78]

def get_current_verse_info():
    delta = datetime.now() - START_DATE
    day_num = max(1, delta.days + 1)
    count = 0
    for ch_idx, length in enumerate(GITA_CH_LENGTHS):
        if day_num <= count + length:
            return day_num, ch_idx + 1, day_num - count
        count += length
    return day_num, 1, 1

def get_wisdom_package():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}"
    day, ch, v = get_current_verse_info()
    
    prompt = f"""
    You are a master storyteller writing a serial saga called 'Geeta: Echoes of Kurukshetra'. 
    
    STYLE & TONE:
    - Language: Very simple, everyday English. Raw and emotional.
    - Setting: A rustic, small-town or village in modern India.
    - Characters: Use common Hindi names.
    - Story Arc: This is Day {day}. Start a new serial saga today. 
    
    TASK:
    1. Provide the FULL Sanskrit Shloka for Ch {ch}, V {v}.
    2. Provide the full Hindi translation.
    3. Write Part {day} of the story (Approx 400 words).
    4. Provide a [VIBE]: Exactly two lines of Gen-Z slang/style commentary on the verse.

    STRICT FORMAT:
    [SHLOKA]: (Full Sanskrit)
    [HINDI]: (Full Hindi)
    [VIBE]: (Two lines for Gen-Z)
    [TITLE]: (Catchy 3-word title)
    [STORY]: (Part {day} of the serial saga)
    [CHALLENGE]: (One simple daily action)
    [VISUAL]: (AI image prompt: Cinematic, raw, rustic Indian scene, 8k, highly detailed)
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        res_json = response.json()
        full_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        def extract(label):
            match = re.search(rf"\[{label}\]\s*:?\s*(.*?)(?=\n\s*\[|$)", full_text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""

        return {
            "shloka": extract("SHLOKA"), 
            "hindi": extract("HINDI"),
            "vibe": extract("VIBE"), 
            "title": extract("TITLE"),
            "challenge": extract("CHALLENGE"), 
            "visual": extract("VISUAL"),
            "story": extract("STORY"), 
            "day": day, "ch": ch, "v": v
        }
    except Exception as e:
        print(f"API Error: {e}")
        return None

def run_delivery():
    data = get_wisdom_package()
    if not data: return
        
    # Reinforced Image URL Logic
    clean_visual = re.sub(r'[^a-zA-Z0-9 ]', '', data['visual'])
    seed_val = random.randint(1000, 9999)
    encoded_prompt = urllib.parse.quote(clean_visual)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=600&seed={seed_val}&model=flux&nologo=true"

    msg = MIMEMultipart()
    msg['Subject'] = f"Geeta: Echoes of Kurukshetra | Day {data['day']}"
    msg['From'] = f"Geeta: Echoes <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    first_letter = data['story'][0] if data['story'] else "I"
    story_body = data['story'][1:].replace('\n', '<br>')
    # Ensure vibe is 2 lines for HTML
    vibe_check = data['vibe'].replace('\n', '<br>')

    html = f"""
    <div style="font-family: 'Trebuchet MS', sans-serif; background: #faf7f2; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 30px; border-top: 10px solid #5d4037; border-radius: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <p style="text-align: center; color: #8d6e63; text-transform: uppercase; font-size: 11px; letter-spacing: 2px; margin-bottom: 5px;">
                Day {data['day']} • Chapter {data['ch']}, Verse {data['v']}
            </p>
            <h1 style="text-align: center; color: #3e2723; margin-top: 0; font-size: 26px;">{data['title']}</h1>
            
            <div style="text-align: center; font-style: italic; color: #6d4c41; margin-bottom: 25px; font-weight: bold; font-size: 15px;">
                {vibe_check}
            </div>
            
            <div style="text-align: center; margin: 20px 0; background: #efebe9; padding: 25px; border-radius: 8px;">
                <p style="font-size: 22px; color: #2e150b; line-height: 1.4; margin-bottom: 12px;"><b>{data['shloka']}</b></p>
                <p style="font-size: 18px; color: #4e342e; line-height: 1.5;">{data['hindi']}</p>
            </div>
            
            <img src="{image_url}" alt="Daily Wisdom Image" style="width: 100%; border-radius: 4px; margin: 15px 0; display: block;">
            
            <div style="font-size: 18px; line-height: 1.8; text-align: justify; color: #212121; margin-top: 25px;">
                <span style="font-size: 55px; color: #5d4037; float: left; line-height: 45px; padding-top: 8px; padding-right: 12px; font-family: serif; font-weight: bold;">{first_letter}</span>{story_body}
            </div>
            
            <div style="clear: both; background: #3e2723; color: #d7ccc8; padding: 20px; text-align: center; margin-top: 40px; border-radius: 4px;">
                <p style="margin: 0; font-size: 10px; color: #a1887f; text-transform: uppercase; letter-spacing: 1px;">The Daily Step</p>
                <p style="margin: 8px 0 0 0; font-size: 19px; color: #ffffff;">{data['challenge']}</p>
            </div>
            
            <p style="text-align: center; margin-top: 35px; font-size: 22px; color: #8d6e63; letter-spacing: 3px;">🕉️</p>
        </div>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"SUCCESS: 'Echoes of Kurukshetra' Day {data['day']} delivered with image and vibe check.")
    except Exception as e:
        print(f"SMTP Error: {e}")

if __name__ == "__main__":
    run_delivery()
