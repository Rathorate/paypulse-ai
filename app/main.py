import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="PayPulse AI Assistant")

# Initialize the Groq client safely from environment variables
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

class QueryRequest(BaseModel):
    prompt: str

@app.get("/")
def read_root():
    return {"message": "Welcome to PayPulse AI API"}

@app.post("/api/assistant")
def chat_with_assistant(request: QueryRequest):
    if not client:
        raise HTTPException(status_code=500, detail="Groq API key is not configured.")
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": request.prompt}],
            temperature=0.7,
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
