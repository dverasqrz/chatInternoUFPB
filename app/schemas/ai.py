from pydantic import BaseModel

class AIQuestionRequest(BaseModel):
    question: str

class AIAnswerResponse(BaseModel):
    answer: str
