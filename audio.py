from gtts import gTTS 
from datetime import datetime 
def text_to_speech(text,language='en'): 
    lang = 'ur' if language=='urdu' else 'hi' if language=='hindi' else 'en' 
    file_name=f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3" 
    tts=gTTS(text=text,lang=lang) 
    tts.save(file_name) 
    return file_name 
