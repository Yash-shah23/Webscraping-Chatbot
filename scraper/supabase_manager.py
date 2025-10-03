from config import supabase
from typing import List, Dict

def get_all_sessions():
    """Fetches all sessions from the database, including their status."""
    try:
        response = supabase.table('sessions').select(
            'session_id, doc_id, created_at, conversation, status, documents(website_url)'
        ).order('created_at', desc=True).execute()
        return response
    except Exception as e:
        print(f"[DB_ERROR] Failed to fetch sessions: {e}")
        return None

def update_session_status(session_id: str, status: str):
    """Updates the status of a session (e.g., 'ready' or 'failed')."""
    try:
        supabase.table('sessions').update({'status': status}).eq('session_id', session_id).execute()
        print(f"[DB] Session {session_id} status updated to '{status}'.")
    except Exception as e:
        print(f"[DB_ERROR] Failed to update session status: {e}")

def update_conversation(session_id: str, conversation_history: List[str]):
    """Updates the conversation history for a given session."""
    try:
        response = supabase.table('sessions').update({
            'conversation': conversation_history
        }).eq('session_id', session_id).execute()
        return response
    except Exception as e:
        print(f"[DB_ERROR] Failed to update conversation: {e}")
        return None

def upsert_document(doc_id: str, website_url: str, content_data: Dict):
    """
    Upserts a document. Creates it if it doesn't exist, updates it if it does.
    This is key to creating a placeholder and then updating it with content.
    """
    try:
        response = supabase.table('documents').upsert({
            'doc_id': doc_id,
            'website_url': website_url,
            'content': content_data
        }).execute()
        return response
    except Exception as e:
        print(f"[DB_ERROR] Failed to upsert document: {e}")
        return None

def create_initial_session(doc_id: str, session_id: str):
    """Creates an initial session with a 'processing' status."""
    try:
        response = supabase.table('sessions').insert({
            'doc_id': doc_id,
            'session_id': session_id,
            'conversation': [],
            'status': 'processing'
        }).execute()
        return response
    except Exception as e:
        print(f"[DB_ERROR] Failed to create initial session: {e}")
        return None

