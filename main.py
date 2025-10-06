import uvicorn

if __name__ == "__main__":
    print("🚀 Starting FastAPI server...")
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
