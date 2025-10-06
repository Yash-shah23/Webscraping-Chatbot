import os
import pickle
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms.ollama import Ollama
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from config import supabase

CACHE_DIR = "retriever_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
RETRIEVER_CACHE = {}

def load_cache_from_disk():
    """Loads all saved vector stores from the cache directory into memory."""
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".pkl"):
            doc_id = filename.split('.')[0]
            try:
                with open(os.path.join(CACHE_DIR, filename), 'rb') as f:
                    RETRIEVER_CACHE[doc_id] = pickle.load(f)
                print(f"[CACHE] Loaded vector store for doc_id {doc_id} from disk.")
            except Exception as e:
                print(f"[CACHE_ERROR] Failed to load {filename}: {e}")

load_cache_from_disk()

def prepare_retriever_for_doc(doc_id: str):
    """Prepares and caches the FAISS vector store and saves it to disk."""
    if doc_id in RETRIEVER_CACHE:
        return True

    print(f"[RAG] Preparing new vector store for doc_id: {doc_id}...")
    try:
        response = supabase.table('documents').select('content').eq('doc_id', doc_id).single().execute()
        if not response.data or not response.data.get('content'):
            raise FileNotFoundError(f"No document content found for doc_id: {doc_id}")

        data = response.data['content']
        page_contents = [f"URL: {p.get('url','')}\nContent:\n{p.get('content','')}" for p in data.get('pages', [])]
        full_text = "\n\n---\n\n".join(page_contents)
        doc = Document(page_content=full_text, metadata={"source": data.get("website_url", "")})

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_documents([doc])
        
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(chunks, embeddings)
        
        RETRIEVER_CACHE[doc_id] = vectorstore
        
        with open(os.path.join(CACHE_DIR, f"{doc_id}.pkl"), 'wb') as f:
            pickle.dump(vectorstore, f)
        
        print(f"[RAG] Vector store for doc_id {doc_id} is ready and saved.")
        return True
    except Exception as e:
        print(f"[RAG_ERROR] Failed to prepare vector store: {e}")
        return False

def ask_question(doc_id: str, question: str, history: list) -> str:
    """
    Asks a question using a faster, conversational RAG pipeline.
    """
    if doc_id not in RETRIEVER_CACHE:
        print(f"[CACHE] Vector store for {doc_id} not in memory. Preparing now...")
        if not prepare_retriever_for_doc(doc_id):
            return "Sorry, I could not prepare the document for chat. The data might be missing."

    vectorstore = RETRIEVER_CACHE[doc_id]
    llm = Ollama(model="gemma:7b")
    
    # --- THIS IS THE NEW, FASTER RETRIEVER ---
    # We use the base retriever which is much faster than the Multi-Query one.
    retriever = vectorstore.as_retriever()

    template = """
    You are "Athena," a friendly, enthusiastic, and highly intelligent AI assistant. Your primary goal is to provide helpful, well-structured, and engaging answers based ONLY on the context provided from a scraped website and the previous chat history.

    **Your Core Instructions:**
    1.  **Greeting:** Always start your response with a warm, positive greeting like "Of course!", "Absolutely!", or "I'd be happy to help with that!".
    2.  **Formatting:** Use Markdown to make your answers clear and easy to read.
        - Use **bold text** for titles, headings, and important keywords.
        - Use bullet points (`*`) for lists of services, features, or items.
        - Add relevant emojis to make the conversation more engaging and visually appealing.
    3.  **Synthesize, Don't Just Quote:** Combine information from the context to form a complete, easy-to-read answer. Do not just repeat snippets.
    4.  **Use Chat History:** If the user asks a follow-up question, refer to the previous conversation to understand the full context.
    5.  **Stay Grounded:** If the answer is not in the provided context, you MUST respond with: "That's a great question, but I don't have that information in the provided documents." Do not use external knowledge.
    6.  **Closing:** Always end your response with a friendly, open-ended question to encourage further interaction, like "Is there anything else I can help you with?" or "Would you like to dive deeper into any of these points?".

    **CONTEXT:**
    ---
    {context}
    ---

    **CHAT HISTORY:**
    {chat_history}

    **USER'S QUESTION:** {question}

    **YOUR ANSWER:**
    """
    prompt = ChatPromptTemplate.from_template(template)

    # --- The Final, Faster RAG Chain ---
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough(), "chat_history": lambda x: history}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain.invoke(question)

