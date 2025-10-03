import os
import pickle
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms.ollama import Ollama
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from config import supabase

# --- KEY CHANGE: Logic to save/load the cache from a file ---
CACHE_DIR = "retriever_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
RETRIEVER_CACHE = {}

def load_cache_from_disk():
    """Loads all saved retriever files from the cache directory into memory."""
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".pkl"):
            doc_id = filename.split('.')[0]
            with open(os.path.join(CACHE_DIR, filename), 'rb') as f:
                RETRIEVER_CACHE[doc_id] = pickle.load(f)
            print(f"[CACHE] Loaded retriever for doc_id {doc_id} from disk.")

# --- Load the cache when the application starts ---
load_cache_from_disk()

def prepare_retriever_for_doc(doc_id: str):
    """
    Prepares and caches the RAG retriever, and now saves it to disk.
    """
    if doc_id in RETRIEVER_CACHE:
        print(f"[CACHE] Retriever for doc_id {doc_id} already in memory.")
        return True

    print(f"[RAG] Preparing new retriever for doc_id: {doc_id}...")
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
        
        print("[RAG] Creating embeddings and vector store...")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(chunks, embeddings)
        
        retriever = vectorstore.as_retriever()
        RETRIEVER_CACHE[doc_id] = retriever
        
        # --- KEY CHANGE: Save the newly created retriever to a file ---
        with open(os.path.join(CACHE_DIR, f"{doc_id}.pkl"), 'wb') as f:
            pickle.dump(retriever, f)
        
        print(f"[RAG] Retriever for doc_id {doc_id} is ready and saved to disk.")
        return True
    except Exception as e:
        print(f"[RAG_ERROR] Failed to prepare retriever: {e}")
        return False

def ask_question(doc_id: str, question: str) -> str:
    """Asks a question using the pre-cached RAG retriever."""
    if doc_id not in RETRIEVER_CACHE:
        # Before failing, try to load it from disk one more time
        try:
            with open(os.path.join(CACHE_DIR, f"{doc_id}.pkl"), 'rb') as f:
                RETRIEVER_CACHE[doc_id] = pickle.load(f)
            print(f"[CACHE] Lazily loaded retriever for doc_id {doc_id} from disk.")
        except FileNotFoundError:
             raise Exception("Retriever not prepared and not found on disk. Please re-scrape the document.")

    retriever = RETRIEVER_CACHE[doc_id]
    
    template = """
    Answer the question based only on the following context. If the answer is not in the context, say 'Sorry, I don't have that information in the document.'

    CONTEXT:
    {context}

    QUESTION:
    {question}

    ANSWER:
    """
    prompt = ChatPromptTemplate.from_template(template)
    llm = Ollama(model="gemma:7b")

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain.invoke(question)

