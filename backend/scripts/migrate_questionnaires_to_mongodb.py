import asyncio
import json
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add backend directory to Python path to allow src imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from the .env file in the backend directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise ValueError("MONGO_URL environment variable is not set. Please create a .env file in the backend directory.")

# Define paths to the source JSON files
# Note: These paths are relative to the script's location in `backend/scripts/`
BASIC_QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sources', 'basic_information_questions.json')
DYNAMIC_QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sources', 'dynamic_questionnaire.json')

# Collection names in MongoDB
BASIC_COLLECTION = 'basic_questions'
DYNAMIC_COLLECTION = 'dynamic_questions'

async def populate_db():
    """Connects to MongoDB, clears old data, and inserts new questions from JSON files."""
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db_name = os.getenv("MONGO_DB_NAME")
    
    if not db_name:
        print("\n--- CONFIGURATION ERROR ---")
        print("Your MONGO_URL in the .env file is missing a database name.")
        print("Please add it to the end of the URL.")
        print(f"Example: mongodb://localhost:27017/{'apt_scanner'}\n")
        client.close()
        return
        
    db = client[db_name] # Explicitly get the database by name
    
    print(f"Connected to database: {db.name}")

    try:
        # --- Populate Basic Questions ---
        print(f"\nPopulating '{BASIC_COLLECTION}' collection...")
        if not os.path.exists(BASIC_QUESTIONS_PATH):
            print(f"Error: Source file not found at {BASIC_QUESTIONS_PATH}.")
            return

        with open(BASIC_QUESTIONS_PATH, 'r', encoding='utf-8') as f:
            basic_questions_data = json.load(f)

        if basic_questions_data and isinstance(basic_questions_data, list):
            basic_collection = db[BASIC_COLLECTION]
            # Clear existing data to ensure idempotency
            await basic_collection.delete_many({})
            print(f"Cleared existing documents in '{BASIC_COLLECTION}'.")
            
            # Insert new data
            result = await basic_collection.insert_many(basic_questions_data)
            print(f"Successfully inserted {len(result.inserted_ids)} documents into '{BASIC_COLLECTION}'.")
        else:
            print(f"No data found or data is not a list in {BASIC_QUESTIONS_PATH}.")

        # --- Populate Dynamic Questions ---
        print(f"\nPopulating '{DYNAMIC_COLLECTION}' collection...")
        if not os.path.exists(DYNAMIC_QUESTIONS_PATH):
            print(f"Error: Source file not found at {DYNAMIC_QUESTIONS_PATH}.")
            return
            
        with open(DYNAMIC_QUESTIONS_PATH, 'r', encoding='utf-8') as f:
            dynamic_questions_data = json.load(f)

        if dynamic_questions_data and isinstance(dynamic_questions_data, list):
            dynamic_collection = db[DYNAMIC_COLLECTION]
            # Clear existing data
            await dynamic_collection.delete_many({})
            print(f"Cleared existing documents in '{DYNAMIC_COLLECTION}'.")
            
            # Insert new data
            result = await dynamic_collection.insert_many(dynamic_questions_data)
            print(f"Successfully inserted {len(result.inserted_ids)} documents into '{DYNAMIC_COLLECTION}'.")
        else:
            print(f"No data found or data is not a list in {DYNAMIC_QUESTIONS_PATH}.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()
        print("\nMongoDB connection closed. Population process finished.")

if __name__ == "__main__":
    print("Starting questionnaire database population...")
    asyncio.run(populate_db())