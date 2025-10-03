# main.py

import uvicorn

if __name__ == "__main__":
    print("Starting FastAPI server on http://127.0.0.1:8000")
    # reload=True is great for development, it automatically restarts the server on code changes
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
