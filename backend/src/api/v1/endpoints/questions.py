import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from src.middleware.auth import get_current_firebase_user
from src.models.models import QuestionModel
from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parents[5]
QUESTIONS_FILE = BASE_DIR / "data" / "sources" / "questions.json"
logger = logging.getLogger(__name__)


router = APIRouter()

@router.get("/all",
             response_model=List[QuestionModel],
             summary="Get all questions",
             dependencies=[Depends(get_current_firebase_user)])
async def get_questions():
    try:
        with open(QUESTIONS_FILE, "r",encoding = "utf-8") as file:
            questions_data = json.load(file)
        logger.info(f"Loaded {len(questions_data)} questions from {QUESTIONS_FILE}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Questions file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding questions data")
    return questions_data
            


