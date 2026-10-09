from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm import query_groq

router = APIRouter()

class PromptRequest(BaseModel):
    prompt: str

@router.post("/assistant/query")
async def handle_assistant_query(req: PromptRequest):
    response_text = query_groq(req.prompt)
    return {"status": "success", "response": response_text}
