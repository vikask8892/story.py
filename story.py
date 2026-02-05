import requests, os, smtplib, urllib.parse, re, uuid
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
    
    # Updated Prompt for a Raw, Rustic, Serial Story with Hindi Names
    prompt = f"""
    You are a master storyteller writing a serial saga called 'The Earthy Gita'. 
    
    STYLE:
    - Language: Very simple, easy English.
    - Tone: Rustic, raw, and emotional. Not corporate. 
    - Characters: Use Hindi names (e.g., Arjun becomes 'Arjun', but set in a modern rural/small-town struggle).
    - Story Continuity: This is Day {day}. Start a brand new serial saga today. 
      Every day's story must be a direct continuation of the previous day. 
      The plot must mirror the theme of Bhagavad Gita CHAPTER {ch}, VERSE {v}.

    TASK:
    1. Provide the FULL Sanskrit Shloka for Ch {ch}, V {v}.
    2. Provide the Hindi translation.
    3. Write Part {day} of the story (Approx 400 words). 
       Focus on a relatable struggle that makes the reader feel the emotion.

    STRICT FORMAT:
    [SHLOKA]: (Full Sanskrit)
    [HINDI]: (Full Hindi)
    [VIBE]: (Simple, one-sentence vibe check)
    [TITLE]: (3-word earthy title)
    [STORY]: (The serial story - Part {day})
    [CHALLENGE]: (One simple life task)
    [VISUAL]: (AI image prompt: Cinematic, raw, rustic Indian setting)
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
        
    clean_visual = re.sub(r'[^a-zA-Z0-9 ]', '', data['visual'])
    image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_visual)}?width=1000&height=600&seed={uuid.uuid4().hex}&nologo=true"

    msg = MIMEMultipart()
    msg['Subject'] = f"Gita Saga Day {data['day']} | {data['title']}"
    msg['From'] = f"The Earthy Gita <{EMAIL_SENDER}>"
    msg['To'] = EMAIL_SENDER
    
    first_letter = data['story'][0] if data['story'] else "O"
    story_body = data['story'][1:].replace('\n', '<br>')

    html = f"""
    <div style="font-family: 'Verdana', sans-serif; background: #f4eee1; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 30px; border-top: 8px solid #8e44ad; border-radius: 4px;">
            <p style="text-align: center; color: #7f8c8d; text-transform: uppercase; font-size: 12px; letter-spacing: 1px;">
                Part {data['day']} • Verse {data['ch']}.{data['v']}
            </p>
            <h1 style="text-align: center; color: #2c3e50; margin-top: 5px;">{data['title']}</h1>
            <p style="text-align: center; font-style: italic; color: #34495e;">"{data['vibe']}"</p>
            
            <div style="text-align: center; margin: 25px 0; background: #fdf2ff; padding: 25px; border-radius: 5px; border-bottom: 3px solid #8e44ad;">
                <p style="font-size: 22px; color: #4a235a; line-height: 1.4; margin-bottom: 10px;"><b>{data['shloka']}</b></p>
                <p style="font-size: 18px; color: #5b2c6f;">{data['hindi']}</p>
            </div>
            
            <img src="{image_url}" style="width: 100%; border-radius: 4px; filter: sepia(20%);">
            
            <div style="font-size: 18px; line-height: 1.7; text-align: left; color: #212121; margin-top: 25px;">
                <span style="font-size: 60px; color: #8e44ad; float: left; line-height: 50px; padding-top: 10px; padding-right: 12px; font-family: serif;">{first_letter}</span>{story_body}
            </div>
            
            <div style="background: #2c3e50; color: #ecf0f1; padding: 20px; text-align: center; margin-top: 40px; border-radius: 2px;">
                <p style="margin: 0; font-size: 11px; color: #aeb6bf; text-transform: uppercase;">Today's Act</p>
                <p style="margin: 8px 0 0 0; font-size: 18px;">{data['challenge']}</p>
            </div>
            
            <p style="text-align: center; margin-top: 30px; font-size: 20px;">🌿</p>
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
        print(f"SUCCESS: Restarted Day 1 delivered.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_delivery()
