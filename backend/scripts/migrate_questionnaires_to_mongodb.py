#!/usr/bin/env python3
"""Script to migrate questionnaire data from JSON files to MongoDB."""
import asyncio
import json
import os
import sys
import logging
from pathlib import Path

# Add the backend src directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
from src.config.mongodb import connect_to_mongo, close_mongo_connection
from src.services.MongoQuestionnaireService import MongoQuestionnaireService

# Load environment variables
load_dotenv(dotenv_path=backend_dir / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def migrate_questionnaires():
    """Migrate questionnaire data from JSON files to MongoDB."""
    try:
        # Connect to MongoDB
        await connect_to_mongo()
        logger.info("Connected to MongoDB successfully")
        
        # Initialize the MongoDB service
        mongo_service = MongoQuestionnaireService()
        
        # Define file paths
        basic_info_file = backend_dir / "data" / "sources" / "basic_information_questions.json"
        dynamic_file = backend_dir / "data" / "sources" / "dynamic_questionnaire.json"
        
        # Migrate basic information questions
        if basic_info_file.exists():
            logger.info(f"Migrating basic information questions from {basic_info_file}")
            with open(basic_info_file, 'r', encoding='utf-8') as f:
                basic_questions = json.load(f)
            
            success = await mongo_service.migrate_from_json(basic_questions, is_basic_info=True)
            if success:
                logger.info(f"Successfully migrated {len(basic_questions)} basic information questions")
            else:
                logger.error("Failed to migrate basic information questions")
        else:
            logger.error(f"Basic information questions file not found: {basic_info_file}")
        
        # Migrate dynamic questionnaire questions
        if dynamic_file.exists():
            logger.info(f"Migrating dynamic questionnaire questions from {dynamic_file}")
            with open(dynamic_file, 'r', encoding='utf-8') as f:
                dynamic_questions = json.load(f)
            
            success = await mongo_service.migrate_from_json(dynamic_questions, is_basic_info=False)
            if success:
                logger.info(f"Successfully migrated {len(dynamic_questions)} dynamic questions")
            else:
                logger.error("Failed to migrate dynamic questions")
        else:
            logger.error(f"Dynamic questionnaire file not found: {dynamic_file}")
        
        # Verify migration
        all_questions = await mongo_service.get_all_questions()
        logger.info(f"Total questions in MongoDB: {len(all_questions)}")
        
        basic_questions = await mongo_service.get_basic_information_questions()
        dynamic_questions = await mongo_service.get_dynamic_questionnaire_questions()
        
        logger.info(f"Basic information questions: {len(basic_questions)}")
        logger.info(f"Dynamic questions: {len(dynamic_questions)}")
        
        # List question IDs for verification
        logger.info("Basic question IDs:")
        for q in basic_questions:
            logger.info(f"  - {q['question_id']}")
        
        logger.info("Dynamic question IDs:")
        for q in dynamic_questions:
            logger.info(f"  - {q['question_id']}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await close_mongo_connection()
        logger.info("MongoDB connection closed")

if __name__ == "__main__":
    logger.info("Starting questionnaire migration to MongoDB...")
    asyncio.run(migrate_questionnaires())
    logger.info("Migration completed!") 