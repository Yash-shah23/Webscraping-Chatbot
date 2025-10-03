import uuid
import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

from scraper.scraper_manager import scrape_and_process_site
from scraper.supabase_manager import get_all_sessions, update_conversation
from scraper.rag_handler import ask_question
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Web Scraper & Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
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

@app.post("/chat", summary="Ask a question and save conversation", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        answer = ask_question(doc_id=req.doc_id, question=req.question)
        new_history = req.history + [req.question, answer]
        update_conversation(session_id=req.session_id, conversation_history=new_history)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

