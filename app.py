import uuid
import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

from scraper.scraper_manager import scrape_and_process_site
from scraper.supabase_manager import get_all_sessions, update_conversation
from scraper.rag_handler import ask_question
from fastapi.middleware.cors import CORSMiddleware

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import random

# ---------------------- INTENT / EMOTION SETS ----------------------

GREETINGS = {
    "hello", "hi", "hey", "heya", "yo", "hi there",
    "greetings", "good morning", "good afternoon", "good evening",
    "sup", "what's up", "whats up", "what's good", "howdy",
    "dude", "buddy", "pal", "mate",
    "hiya", "hey there", "hey hey",
    "how are you", "how's it going", "how are you doing", "what's up",
    "helo", "hy", "hii", "heyy", "hiii", "heyyyy",
}

NEGATIONS = {
    "no", "nope", "nah", "na", "not", "never", "none", "nothing", "nada", "nay",
    "never", "no way", "absolutely not", "not at all",
    "i don't think so", "not really", "negative", "by no means",
    "i’m afraid not", "cannot", "unfortunately not",
}

GOODBYES = {
    "bye", "goodbye", "ciao", "adieu", "thanks bye", "thank you", "thanks",
    "see you", "see ya", "later", "take care", "bye bye", "catch you later",
    "farewell", "have a good day", "all the best", "best regards",
    "talk to you later", "see you soon", "take it easy", "peace out",
}

THANKS = {
    "thanks", "thank you", "thx", "ty", "much appreciated", "cheers",
    "thanks a lot", "thanks so much", "thanks a ton", "thanks heaps",
    "grateful", "i appreciate it", "many thanks",
}

AFFIRMATIONS = {
    "yes", "yeah", "yep", "yup", "sure", "absolutely", "definitely",
    "of course", "certainly", "indeed", "you got it", "roger",
}

QUESTIONS = {
    "what", "when", "where", "who", "how", "why",
    "can you", "could you", "do you", "is it", "are you", "will you",
    "please explain", "help me", "clarify", "information",
}

EMOTIONS = {
    "happy", "glad", "joyful", "excited", "thrilled", "awesome", "great", "fantastic", "cool",
    "sad", "upset", "down", "unhappy", "depressed", "sorry", "disappointed",
    "angry", "mad", "frustrated", "annoyed", "irritated", "pissed off",
    "surprised", "shocked", "wow", "oh my", "unexpected", "unbelievable",
    "scared", "afraid", "worried", "nervous", "anxious",
    "love", "like", "fond", "care", "admire", "appreciate",
}

EMOJIS = {
    "😊", "😂", "😍", "😢", "😡", "😱", "👍", "👎", "💖", "😎", "🤔", "😴"
}

# ---------------------- RESPONSE SETS ----------------------

GREETING_RESPONSES = [
    "Hello! How can I help you with the document today? 😊",
    "Hi there! What information can I find for you?",
    "Hey! Ready to answer your questions. What's on your mind?",

]

NEGATION_RESPONSES = [
    "Alright, understood.",
    "Okay, just let me know if you need anything else.",
    "Got it!",
    "No problem, feel free to ask if you have other questions.",
    "Understood, I'm here if you need any further assistance.",
    "Got it! If you have more questions, just let me know."
]

GOODBYES_RESPONSES = [
    "Goodbye! Have a great day! 👋",
    "See you later! Feel free to come back anytime. 😊",
    "Take care! If you have more questions, I'm here to help. 👋",
    "Bye! Don't hesitate to reach out if you need anything else. 😊",
    "Farewell! Wishing you all the best. 👋"
]

THANKS_RESPONSES = [
    "You're welcome! 😊",
    "No problem, happy to help!",
    "Anytime! Let me know if you need more assistance.",
    "Glad I could assist! Feel free to ask more questions.",
    "My pleasure! If you have any other questions, just ask."
]

AFFIRMATION_RESPONSES = [
    "Great! 👍",
    "Understood.",
    "Perfect! Let's proceed.",
]

# ---------------------- FastAPI SETUP ----------------------

analyzer = SentimentIntensityAnalyzer()

app = FastAPI(title="Web Scraper & Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# --- Pydantic Models for API validation and response schemas ---
class ScrapeRequest(BaseModel): url: HttpUrl
class ChatRequest(BaseModel):
    session_id: str
    doc_id: str
    question: str
    history: List[str]
class DocumentInfo(BaseModel): website_url: Optional[str] = None
class SessionInfo(BaseModel):
    session_id: uuid.UUID
    doc_id: uuid.UUID
    created_at: datetime.datetime
    conversation: List[str]
    status: Optional[str] = 'processing'
    documents: Optional[DocumentInfo] = None
class ScrapeResponse(BaseModel):
    status: str
    message: str
class ChatResponse(BaseModel): answer: str

@app.get("/", summary="API Health Check")
async def root():
    return {"message": "API is running. Use /docs for API documentation."}

# --- API Endpoints ---
@app.get("/sessions", summary="Get all chat sessions", response_model=List[SessionInfo])
async def fetch_sessions_endpoint():
    try:
        response = get_all_sessions()
        return response.data if response and response.data is not None else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {e}")
    
@app.post("/scrape", summary="Start a full scrape and process task", response_model=ScrapeResponse)
async def scrape_endpoint(req: ScrapeRequest, background_tasks: BackgroundTasks):
    try:
        url_str = str(req.url)
        doc_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        background_tasks.add_task(scrape_and_process_site, url_str, doc_id, session_id)
        return {"status": "success", "message": f"Processing started for {url_str}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {e}")

# ==============================================================================

@app.post("/chat", summary="Ask a question and save conversation", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        question = req.question.lower().strip().rstrip("?!.")
        final_answer = ""

        # --- Check all intents ---
        if question in GREETINGS:
            final_answer = random.choice(GREETING_RESPONSES)
        elif question in NEGATIONS:
            final_answer = random.choice(NEGATION_RESPONSES)
        elif question in GOODBYES:
            final_answer = random.choice(GOODBYES_RESPONSES)
        elif question in THANKS:
            final_answer = random.choice(THANKS_RESPONSES)
        elif question in AFFIRMATIONS:
            final_answer = random.choice(AFFIRMATION_RESPONSES)
        elif any(word in question for word in EMOTIONS):
            final_answer = "I sense some emotion there! 😊 How can I assist you further?"
        elif any(word in question for word in QUESTIONS):
            # For general questions, go to RAG
            rag_answer = ask_question(doc_id=req.doc_id, question=req.question, history=req.history)
            final_answer = f"Here’s what I found: {rag_answer}"
        else:
            # --- Sentiment Analysis + RAG pipeline ---
            sentiment_scores = analyzer.polarity_scores(req.question)
            sentiment = "neutral"
            if sentiment_scores['compound'] >= 0.05:
                sentiment = "positive"
            elif sentiment_scores['compound'] <= -0.05:
                sentiment = "negative"

            rag_answer = ask_question(doc_id=req.doc_id, question=req.question, history=req.history)

            if sentiment == "positive":
                final_answer = f"Great question! ✨ {rag_answer}"
            elif sentiment == "negative":
                final_answer = f"I understand. Here is the information I found: {rag_answer}"
            else: # Neutral
                final_answer = rag_answer

        # --- Update conversation ---
        new_history = req.history + [req.question, final_answer]
        update_conversation(session_id=req.session_id, conversation_history=new_history)

        return ChatResponse(answer=final_answer)

    except Exception as e:
        print(f"An error occurred in /chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your request.")
