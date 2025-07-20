import asyncio
import json
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import ssl

# Add project root to path to allow imports from other modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

# Correctly locate and load the .env file from the project root
dotenv_path = os.path.join(project_root, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"Warning: .env file not found at {dotenv_path}")


from backend.src.database.models import Listing

load_dotenv(dotenv_path='/Users/or.hershko/Desktop/APT.-Scanner/backend/.env')

# --- Database Setup ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

# Ensure the URL is in the correct async format
if DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# SSL context for Supabase
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Create an async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True to see SQL queries
    connect_args={"ssl": ssl_context}
)

# Create a session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# --- Variant Mapping ---
def load_variant_map():
    """Loads the neighborhood variant map from the JSON file."""
    variants_path = os.path.join(project_root, "backend", "data", "sources", "neighborhood_variants_map.json")
    try:
        with open(variants_path, "r", encoding="utf-8") as f:
            variants_data = json.load(f)
        # Create a dictionary for quick lookups
        return {item["listing_variant"]: item["canonical_name"] for item in variants_data}
    except FileNotFoundError:
        print(f"Error: The file {variants_path} was not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {variants_path}.")
        return {}
    except KeyError:
        print("Error: JSON data is not in the expected format (missing 'listing_variant' or 'canonical_name').")
        return {}

async def update_neighborhood_names():
    """
    Connects to the DB, loads listings, and updates neighborhood names
    based on the variant map.
    """
    variant_map = load_variant_map()
    if not variant_map:
        print("Variant map is empty or could not be loaded. Exiting.")
        return

    updated_count = 0
    processed_count = 0

    print("Starting database session...")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            print("Fetching all listings from the database...")
            result = await session.execute(select(Listing))
            listings = result.scalars().all()
            
            processed_count = len(listings)
            print(f"Found {processed_count} listings to process.")

            for listing in listings:
                original_name = listing.neighborhood_text
                if original_name and original_name in variant_map:
                    canonical_name = variant_map[original_name]
                    if original_name != canonical_name:
                        listing.neighborhood_text = canonical_name
                        updated_count += 1
                        print(f"Updating '{original_name}' to '{canonical_name}' for listing ID {listing.order_id}")

            if updated_count > 0:
                print(f"\nCommitting {updated_count} changes to the database...")
                # The session.begin() context manager handles the commit
            else:
                print("\nNo listings required updates.")

    print("\n--- Script Summary ---")
    print(f"Total listings processed: {processed_count}")
    print(f"Listings updated: {updated_count}")
    print("----------------------")


async def main():
    """Main function to run the update process."""
    await update_neighborhood_names()

if __name__ == "__main__":
    print("Running neighborhood name update script...")
    asyncio.run(main())
    print("Script finished.")
