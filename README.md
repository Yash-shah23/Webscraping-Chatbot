# Webscraping-Chatbot
This project is an all-in-one solution to scrape any website, process its content, and build a Q&amp;A chatbot that runs entirely on your local machine. It intelligently analyzes target websites to choose the best scraping strategy, saves the content, creates embeddings, and allows you to chat with the document using a local LLM like Gemma.

Intelligent Web Scraper & Local RAG Chatbot
This project is an all-in-one solution to scrape any website, process its content, and build a Q&A chatbot that runs entirely on your local machine. It intelligently analyzes target websites to choose the best scraping strategy, saves the content, creates embeddings, and allows you to chat with the document using a local LLM like Gemma.

(Suggestion: Replace this placeholder with a screenshot or GIF of your application in action!)

Key Features
🤖 Smart Scraping Engine: Automatically detects site technology (React, WordPress, JS frameworks, etc.) and bot protection to choose the most effective scraping method (fast static requests or a robust dynamic browser).

🕸️ Full Site Crawling: Traverses and scrapes all unique internal pages of a target website, not just a single URL.

🎯 Intelligent Content Extraction: Isolates and saves only the main article/content from each page, automatically stripping away boilerplate like headers, footers, and navigation bars.

🧠 Local LLM Chat: Features a complete Q&A interface powered by a locally-run gemma:7b model via Ollama. No external API keys or costs are required for the AI.

📚 Retrieval-Augmented Generation (RAG): The chatbot uses a RAG pipeline to answer questions only based on the scraped document content, providing accurate, source-grounded responses and avoiding hallucinations.

💾 Persistent Chat Sessions: All scraping jobs and conversations are saved to a Supabase (PostgreSQL) database, allowing you to return to any chat session later.

✨ Modern Web UI: A clean, responsive dashboard built with HTML & Tailwind CSS to manage scraping tasks and interact with the chatbot.

🚀 Background Processing: Scraping, content processing, and embedding creation all run as background tasks on the server, keeping the UI fast and responsive.

Technology Stack
Backend: Python, FastAPI

Frontend: HTML, Tailwind CSS, Vanilla JavaScript

Scraping: BeautifulSoup, Selenium (Undetected Chromedriver), Wappalyzer, BuiltWith

Database: Supabase (PostgreSQL)

AI/ML:

LLM: Ollama (gemma:7b)

Framework: LangChain

Embeddings: HuggingFace Sentence Transformers (local)

Vector Store: FAISS (local)

How It Works
The application follows a complete pipeline from web scraping to intelligent Q&A:

Scrape Task: The user enters a URL in the web UI. The FastAPI backend starts a background task.

Analyze & Crawl: The scraper analyzes the site's technology to pick a strategy, then crawls all internal pages, extracting the main content from each.

Store & Process: The cleaned content is saved to a local JSON file and uploaded to the Supabase documents table. A corresponding sessions record is created with a processing status.

Embeddings (RAG): The background task then chunks the scraped text, generates embeddings locally using HuggingFace, and builds a FAISS vector store. This vector store is saved to disk so it persists across server restarts.

Ready for Chat: Once the embeddings are created, the session status is updated to ready in the database.

Q&A: The user can now select the session. When a question is asked, the RAG pipeline retrieves the most relevant chunks from the vector store, stuffs them into a prompt for the local Gemma model, and returns a source-grounded answer.

Setup and Installation
Follow these steps to get the project running on your local machine.

1. Prerequisites
Python 3.8+

Ollama: Make sure Ollama is installed and running. You can download it from ollama.com.

2. Clone the Repository
git clone <your-repository-url>
cd <your-repository-folder>

3. Set Up Python Environment
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install all required packages
pip install -r requirements.txt

4. Configure Supabase
Create a new project on Supabase.

In the SQL Editor, run the SQL commands from the provided schema file to create the documents and sessions tables.

Create a file named .env in the root of the project.

Find your Project URL and anon key in Project Settings > API and add them to the .env file:

SUPABASE_URL="YOUR_SUPABASE_PROJECT_URL"
SUPABASE_KEY="YOUR_SUPABASE_ANON_PUBLIC_KEY"

5. Download the Local LLM
Pull the Gemma model using Ollama. This will download the model to your machine (this may take some time).

ollama pull gemma:7b

6. Run the Application
Start the Backend Server:

python main.py

Leave this terminal running. It is your API server.

Open the Frontend:

Navigate to the project folder in your file explorer.

Double-click the index.html file to open it in your web browser.

You can now start scraping websites and chatting with them!
