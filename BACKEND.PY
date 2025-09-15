from fastapi import FastAPI, Depends, HTTPException
from auth import verify_api_key

app = FastAPI(title="Mehwish Chat APIs")

@app.get("/")
def home():
    return {"message": "Welcome to Mehwish Chat APIs"}

@app.get("/chat")
def chat(query: str, api_key: str = Depends(verify_api_key)):
    # Example response
    response = f"AI response for: {query}"
    return {"query": query, "response": response}
