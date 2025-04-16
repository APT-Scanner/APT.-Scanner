import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from src.middleware.auth import get_current_firebase_user
from src.models.models import QuestionModel
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[5]
QUESTIONS_FILE = BASE_DIR / "data" / "sources" / "questions.json"

router = APIRouter()

@router.get("/all",
             response_model=List[QuestionModel],
             summary="Get all questions",
             dependencies=[Depends(get_current_firebase_user)])
async def get_questions():

    try:
        with open(QUESTIONS_FILE, "r",encoding = "utf-8") as file:
            questions_data = json.load(file)
        print(f"Loaded questions data: {questions_data}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Questions file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding questions data")
    
    return questions_data
            


