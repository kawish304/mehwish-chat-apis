# main.py - FastAPI application with Mehwish Chat API
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import json
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import asyncio
from gtts import gTTS
import PyPDF2
import io
import requests
import logging
import re
import random
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT settings
SECRET_KEY = "mehwish-chat-api-secret-key-2023"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(
    title="Mehwish Chat API", 
    description="Advanced Chat API with AI, PDF, TTS, Weather, News, Sports and more",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
def init_db():
    conn = sqlite3.connect('mehwish.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  email TEXT UNIQUE,
                  hashed_password TEXT,
                  plan TEXT DEFAULT 'free',
                  api_key TEXT UNIQUE,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # User activity table
    c.execute('''CREATE TABLE IF NOT EXISTS user_activity
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  endpoint TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # API usage table
    c.execute('''CREATE TABLE IF NOT EXISTS api_usage
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  endpoint TEXT,
                  count INTEGER DEFAULT 0,
                  last_used DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Chat conversations table
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  conversation_id TEXT,
                  message TEXT,
                  response TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Knowledge base table
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge_base
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic TEXT,
                  content TEXT,
                  language TEXT DEFAULT 'english')''')
    
    # Initialize with some knowledge
    initial_knowledge = [
        ("greeting", "Hello! How can I assist you today?", "english"),
        ("greeting", "Hi there! What can I help you with?", "english"),
        ("greeting", "Assalam-o-Alaikum! Aap kaise hain?", "urdu"),
        ("greeting", "नमस्ते! मैं आपकी क्या मदद कर सकता हूं?", "hindi"),
        ("weather", "I can provide weather information for any city. Just ask me about weather in your city.", "english"),
        ("news", "I can fetch the latest news for you. What category are you interested in?", "english"),
        ("sports", "I can get sports scores and updates. Which sport are you interested in?", "english")
    ]
    
    c.execute("SELECT COUNT(*) FROM knowledge_base")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO knowledge_base (topic, content, language) VALUES (?, ?, ?)", 
                     initial_knowledge)
    
    conn.commit()
    conn.close()

init_db()

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class User(BaseModel):
    username: str
    email: str
    plan: str

class Token(BaseModel):
    access_token: str
    token_type: str

class AIRequest(BaseModel):
    prompt: str
    language: str = "english"
    conversation_id: Optional[str] = None

class TTSRequest(BaseModel):
    text: str
    language: str = "en"

class WeatherRequest(BaseModel):
    city: str

class NewsRequest(BaseModel):
    category: str = "general"

class SportsRequest(BaseModel):
    league: str = "cricket"

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    conn = sqlite3.connect('mehwish.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user is None:
        raise credentials_exception
    return {"id": user[0], "username": user[1], "email": user[2], "plan": user[4]}

def track_api_usage(user_id: int, endpoint: str):
    conn = sqlite3.connect('mehwish.db')
    c = conn.cursor()
    c.execute("INSERT INTO user_activity (user_id, endpoint) VALUES (?, ?)", 
              (user_id, endpoint))
    
    # Update usage count
    c.execute('''INSERT OR IGNORE INTO api_usage (user_id, endpoint, count) 
                 VALUES (?, ?, 1)''', (user_id, endpoint))
    c.execute('''UPDATE api_usage SET count = count + 1, last_used = CURRENT_TIMESTAMP 
                 WHERE user_id = ? AND endpoint = ?''', (user_id, endpoint))
    
    conn.commit()
    conn.close()

# Mehwish Chat AI Engine
class MehwishChatEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.knowledge_base = self.load_knowledge_base()
        self.train_model()
    
    def load_knowledge_base(self):
        conn = sqlite3.connect('mehwish.db')
        c = conn.cursor()
        c.execute("SELECT topic, content, language FROM knowledge_base")
        knowledge = c.fetchall()
        conn.close()
        
        return knowledge
    
    def train_model(self):
        # Extract content for training
        documents = [content for _, content, _ in self.knowledge_base]
        
        if documents:
            self.tfidf_matrix = self.vectorizer.fit_transform(documents)
        else:
            # Default fallback if no knowledge base
            self.tfidf_matrix = self.vectorizer.fit_transform(["hello", "hi", "help"])
    
    def get_response(self, query: str, language: str = "english") -> str:
        # Preprocess query
        processed_query = self.preprocess_text(query)
        
        # Vectorize query
        query_vec = self.vectorizer.transform([processed_query])
        
        # Calculate similarity
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get best match
        best_match_idx = similarities.argmax()
        best_similarity = similarities[best_match_idx]
        
        # Filter by language
        lang_knowledge = [kb for kb in self.knowledge_base if kb[2] == language]
        
        if best_similarity > 0.3 and lang_knowledge:
            # Return the best matching response in the requested language
            lang_documents = [content for _, content, lang in lang_knowledge]
            lang_vec = self.vectorizer.transform(lang_documents)
            lang_similarities = cosine_similarity(query_vec, lang_vec).flatten()
            best_lang_idx = lang_similarities.argmax()
            
            if lang_similarities[best_lang_idx] > 0.2:
                return lang_knowledge[best_lang_idx][1]
        
        # Fallback responses based on language
        fallbacks = {
            "english": [
                "I'm not sure I understand. Could you please rephrase your question?",
                "That's an interesting question. Let me think about how best to help you.",
                "I'm still learning about that topic. Could you ask me something else?",
                "I don't have enough information about that yet. Is there something else I can help with?"
            ],
            "urdu": [
                "میں سمجھ نہیں پایا۔ براہ کرم اپنا سوال دوبارہ بیان کریں۔",
                "یہ ایک دلچسپ سوال ہے۔ مجھے اس کے بارے میں سوچنے دیں۔",
                "میں ابھی اس موضوع کے بارے میں سیکھ رہا ہوں۔ کیا آپ مجھ سے کچھ اور پوچھ سکتے ہیں؟",
                "میرے پاس اس بارے میں ابھی enough معلومات نہیں ہیں۔ کیا میں آپ کی کسی اور چیز میں مدد کر سکتا ہوں؟"
            ],
            "hindi": [
                "मैं समझ नहीं पाया। कृपया अपना प्रश्न फिर से बताएं।",
                "यह एक दिलचस्प सवाल है। मुझे इसके बारे में सोचने दो।",
                "मैं अभी भी उस विषय के बारे में सीख रहा हूं। क्या आप मुझसे कुछ और पूछ सकते हैं?",
                "मेरे पास अभी उस बारे में पर्याप्त जानकारी नहीं है। क्या मैं आपकी किसी और चीज़ में मदद कर सकता हूँ?"
            ]
        }
        
        return random.choice(fallbacks.get(language, fallbacks["english"]))
    
    def preprocess_text(self, text: str) -> str:
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        
        # Tokenize and remove stopwords
        try:
            words = word_tokenize(text)
            stop_words = set(stopwords.words('english'))
            words = [word for word in words if word not in stop_words]
            return ' '.join(words)
        except:
            return text
    
    def add_to_knowledge_base(self, topic: str, content: str, language: str = "english"):
        conn = sqlite3.connect('mehwish.db')
        c = conn.cursor()
        c.execute("INSERT INTO knowledge_base (topic, content, language) VALUES (?, ?, ?)",
                 (topic, content, language))
        conn.commit()
        conn.close()
        
        # Retrain model with new knowledge
        self.knowledge_base = self.load_knowledge_base()
        self.train_model()

# Initialize chat engine
chat_engine = MehwishChatEngine()

# Text-to-speech function
def text_to_speech(text: str, language: str = "en") -> str:
    try:
        if language == 'urdu':
            lang_code = 'ur'
        elif language == 'hindi':
            lang_code = 'hi'
        else:
            lang_code = 'en'
            
        tts = gTTS(text=text, lang=lang_code, slow=False)
        audio_file = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        tts.save(audio_file)
        return audio_file
    except Exception as e:
        logger.error(f"Error in text-to-speech: {e}")
        return None

# PDF processing function
async def process_pdf(file: UploadFile) -> str:
    try:
        # Read file content directly without aiofiles
        contents = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return None

# Weather API function
def get_weather(city: str) -> Dict[str, Any]:
    # Mock weather data - replace with actual API call
    weather_data = {
        "city": city,
        "temperature": f"{random.randint(15, 35)}°C",
        "conditions": random.choice(["Sunny", "Partly Cloudy", "Cloudy", "Rainy"]),
        "humidity": f"{random.randint(30, 90)}%",
        "wind": f"{random.randint(5, 25)} km/h",
        "forecast": [
            {"day": "Today", "high": random.randint(20, 35), "low": random.randint(10, 20), "condition": random.choice(["Sunny", "Partly Cloudy"])},
            {"day": "Tomorrow", "high": random.randint(18, 32), "low": random.randint(12, 22), "condition": random.choice(["Cloudy", "Rainy"])},
            {"day": "Next Day", "high": random.randint(22, 34), "low": random.randint(15, 24), "condition": random.choice(["Sunny", "Clear"])}
        ]
    }
    return weather_data

# News API function
def get_news(category: str = "general") -> List[Dict[str, Any]]:
    # Mock news data - replace with actual API call
    news_data = [
        {"title": "Breaking News: AI Revolution Continues", "source": "AI News Network", "url": "#", "category": "technology"},
        {"title": "Sports Team Wins Championship", "source": "Sports Daily", "url": "#", "category": "sports"},
        {"title": "New Technology Breakthrough Announced", "source": "Tech Review", "url": "#", "category": "technology"},
        {"title": "Economic Growth Exceeds Expectations", "source": "Business Times", "url": "#", "category": "business"},
        {"title": "Health Organization Releases New Guidelines", "source": "Health Journal", "url": "#", "category": "health"}
    ]
    
    # Filter by category if not general
    if category != "general":
        news_data = [news for news in news_data if news["category"] == category]
    
    return news_data[:3]  # Return only 3 news items

# Sports API function
def get_sports_scores(league: str = "cricket") -> List[Dict[str, Any]]:
    # Mock sports data - replace with actual API call
    if league == "cricket":
        sports_data = [
            {"teams": "Pakistan vs India", "score": "285/6 (50) vs 289/4 (48.2)", "status": "India won by 6 wickets"},
            {"teams": "Australia vs England", "score": "320/8 (50) vs 250/9 (50)", "status": "Australia won by 70 runs"},
            {"teams": "South Africa vs New Zealand", "score": "195/10 (40) vs 196/5 (38.2)", "status": "New Zealand won by 5 wickets"}
        ]
    elif league == "football":
        sports_data = [
            {"teams": "Manchester United vs Liverpool", "score": "2-1", "status": "Final"},
            {"teams": "Barcelona vs Real Madrid", "score": "3-2", "status": "Final"},
            {"teams": "Bayern Munich vs Dortmund", "score": "1-1", "status": "Half Time"}
        ]
    else:
        sports_data = [
            {"teams": "Lakers vs Celtics", "score": "105-98", "status": "Final"},
            {"teams": "Warriors vs Bulls", "score": "112-107", "status": "Final"},
            {"teams": "Heat vs Knicks", "score": "75-70", "status": "3rd Quarter"}
        ]
    
    return sports_data

# API Routes
@app.get("/")
async def root():
    return {"message": "Welcome to Mehwish Chat API", "version": "2.0.0"}

@app.post("/api/register")
async def register(user: UserCreate):
    conn = sqlite3.connect('mehwish.db')
    c = conn.cursor()
    
    # Check if user already exists
    c.execute("SELECT id FROM users WHERE username = ? OR email = ?", (user.username, user.email))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    api_key = f"mehwish_{user.username}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    c.execute("INSERT INTO users (username, email, hashed_password, api_key) VALUES (?, ?, ?, ?)",
             (user.username, user.email, hashed_password, api_key))
    conn.commit()
    conn.close()
    
    return {"message": "User created successfully", "api_key": api_key}

@app.post("/api/token")
async def login(username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect('mehwish.db')
    c = conn.cursor()
    c.execute("SELECT id, username, hashed_password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if not user or not verify_password(password, user[2]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user[1]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/ai/chat")
async def ai_chat(request: AIRequest, current_user: dict = Depends(get_current_user)):
    track_api_usage(current_user["id"], "/api/ai/chat")
    
    # Get response from Mehwish Chat Engine
    response = chat_engine.get_response(request.prompt, request.language)
    
    # Store conversation if conversation_id is provided
    if request.conversation_id:
        conn = sqlite3.connect('mehwish.db')
        c = conn.cursor()
        c.execute("INSERT INTO conversations (user_id, conversation_id, message, response) VALUES (?, ?, ?, ?)",
                 (current_user["id"], request.conversation_id, request.prompt, response))
        conn.commit()
        conn.close()
    
    return {"response": response, "language": request.language}

@app.post("/api/audio/generate")
async def generate_audio(request: TTSRequest, current_user: dict = Depends(get_current_user)):
    track_api_usage(current_user["id"], "/api/audio/generate")
    
    audio_file = text_to_speech(request.text, request.language)
    if audio_file:
        return FileResponse(audio_file, media_type="audio/mpeg", filename="audio.mp3")
    else:
        raise HTTPException(status_code=500, detail="Audio generation failed")

@app.post("/api/pdf/process")
async def process_pdf_endpoint(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    track_api_usage(current_user["id"], "/api/pdf/process")
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    text = await process_pdf(file)
    if text:
        return {"text": text}
    else:
        raise HTTPException(status_code=500, detail="PDF processing failed")

@app.get("/api/weather")
async def weather(city: str, current_user: dict = Depends(get_current_user)):
    track_api_usage(current_user["id"], "/api/weather")
    
    weather_data = get_weather(city)
    return weather_data

@app.get("/api/news")
async def news(category: str = "general", current_user: dict = Depends(get_current_user)):
    track_api_usage(current_user["id"], "/api/news")
    
    news_data = get_news(category)
    return {"news": news_data}

@app.get("/api/sports")
async def sports(league: str = "cricket", current_user: dict = Depends(get_current_user)):
    track_api_usage(current_user["id"], "/api/sports")
    
    sports_data = get_sports_scores(league)
    return {"sports": sports_data}

@app.get("/api/conversations")
async def get_conversations(conversation_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    track_api_usage(current_user["id"], "/api/conversations")
    
    conn = sqlite3.connect('mehwish.db')
    c = conn.cursor()
    
    if conversation_id:
        c.execute("SELECT message, response, timestamp FROM conversations WHERE user_id = ? AND conversation_id = ? ORDER BY timestamp",
                 (current_user["id"], conversation_id))
    else:
        c.execute("SELECT DISTINCT conversation_id FROM conversations WHERE user_id = ? ORDER BY timestamp DESC",
                 (current_user["id"],))
        conversations = c.fetchall()
        conn.close()
        return {"conversations": [conv[0] for conv in conversations]}
    
    messages = c.fetchall()
    conn.close()
    
    return {"conversation_id": conversation_id, "messages": messages}

@app.post("/api/knowledge/add")
async def add_knowledge(topic: str, content: str, language: str = "english", current_user: dict = Depends(get_current_user)):
    track_api_usage(current_user["id"], "/api/knowledge/add")
    
    chat_engine.add_to_knowledge_base(topic, content, language)
    return {"message": "Knowledge added successfully"}

@app.get("/api/usage")
async def get_usage(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect('mehwish.db')
    c = conn.cursor()
    
    c.execute("SELECT endpoint, count, last_used FROM api_usage WHERE user_id = ?", (current_user["id"],))
    usage_data = c.fetchall()
    
    conn.close()
    
    return {"usage": [{"endpoint": row[0], "count": row[1], "last_used": row[2]} for row in usage_data]}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
