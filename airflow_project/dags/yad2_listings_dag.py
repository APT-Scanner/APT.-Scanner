"""
Yad2 Listings ETL DAG

This DAG orchestrates the extraction, transformation, and loading of real estate listings 
from Yad2 for multiple neighborhoods in parallel. Each neighborhood is processed as a 
separate task to ensure failures in one area don't affect others.

The workflow:
1. Dynamically reads neighborhood IDs from a JSON mapping file
2. Creates parallel tasks for each neighborhood  
3. Each task scrapes, parses, enriches, and saves listings for one neighborhood
4. Includes error handling and rate limiting between requests
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.exceptions import AirflowException

# Add the backend directory to Python path (mounted at /opt/airflow/backend)
sys.path.append('/opt/airflow')

# Default args for the DAG
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),
}

@dag(
    dag_id='yad2_listings_etl',
    default_args=default_args,
    description='ETL pipeline for Yad2 real estate listings by neighborhood',
    schedule_interval='@daily',
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['etl', 'real-estate', 'yad2'],
    max_active_runs=1,
    max_active_tasks=1,
    doc_md=__doc__,
)
def yad2_listings_etl():
    
    @task
    def get_neighborhood_ids() -> List[int]:
        """
        Read the neighborhood mapping JSON file and extract all neighborhood IDs.
        
        Returns:
            List[int]: List of neighborhood IDs to process
        """
        try:
            # Use the mounted backend directory path
            mapping_file_path = '/opt/airflow/backend/data/sources/yad2_hood_mapping.json'
            
            # If the file doesn't exist, use sample data
            if not os.path.exists(mapping_file_path):
                print("Warning: yad2_hood_mapping.json not found. Using sample neighborhood IDs.")
                # These are example neighborhood IDs - replace with actual values
                return [1001, 1002, 1003, 1004, 1005]
            
            with open(mapping_file_path, 'r', encoding='utf-8') as file:
                hood_mapping = json.load(file)
                neighborhood_ids = [hood['hoodId'] for hood in hood_mapping if 'hoodId' in hood]
                
            print(f"Found {len(neighborhood_ids)} neighborhoods to process: {neighborhood_ids}")
            return neighborhood_ids
            
        except Exception as e:
            print(f"Error reading neighborhood mapping: {e}")
            # Fallback to sample IDs
            return [1001, 1002, 1003, 1004, 1005]

    @task
    def fetch_and_process_single_hood(hood_id: int) -> Dict[str, Any]:
        """
        Extract, transform, and load listings data for a single neighborhood.
        
        This function performs the complete ETL process:
        1. Extract: Scrape listings from Yad2 for the specified neighborhood
        2. Transform: Parse and enrich the raw data
        3. Load: Save the processed data to the database
        
        Args:
            hood_id (int): The neighborhood ID to process
            
        Returns:
            Dict[str, Any]: Summary of processing results
        """
        try:
            # Import required modules (inside task to avoid import issues)
            import time
            import random
            from backend.data.scrapers.yad2_scraper import Yad2Scraper
            from backend.data.processing.parse_listings import parse_listings, enrich_listings
            from populate_database import populate_listings
            
            print(f"Starting ETL process for neighborhood {hood_id}")
            
            # Initialize scraper with retries and error handling
            scraper = None
            max_scraper_retries = 3
            for attempt in range(max_scraper_retries):
                try:
                    print(f"Attempting to initialize scraper (attempt {attempt + 1}/{max_scraper_retries})")
                    scraper = Yad2Scraper()
                    print(f"Successfully initialized scraper on attempt {attempt + 1}")
                    break
                except Exception as scraper_error:
                    print(f"Scraper initialization attempt {attempt + 1} failed: {scraper_error}")
                    if attempt < max_scraper_retries - 1:
                        base_wait = (attempt + 1) * 10  # 10, 20, 30 seconds
                        jitter = random.uniform(0, 5)  # Add 0-5 seconds randomization
                        wait_time = base_wait + jitter
                        print(f"Waiting {wait_time:.1f} seconds before retry...")
                        time.sleep(wait_time)
                    else:
                        # If all attempts failed, return graceful result instead of crashing
                        print(f"All scraper initialization attempts failed for neighborhood {hood_id}")
                        return {
                            "hood_id": hood_id,
                            "status": "scraper_initialization_failed",
                            "listings_count": 0,
                            "processing_time": 0,
                            "error": str(scraper_error)
                        }
            
            if scraper is None:
                raise Exception("Failed to initialize scraper after all attempts")
            
            # Define search parameters for this neighborhood
            direct_params = {
                'top_area': 2,           # Tel Aviv and Center area
                'area': 1,               # Tel Aviv sub-area
                'city': 5000,            # City ID
                'neighborhood': hood_id,  # Current neighborhood
                'image_only': True,      # Only listings with images
                'price_only': True,      # Only listings with prices
            }
            
            # Extract: Scrape listings data
            print(f"Scraping listings for neighborhood {hood_id}...")
            raw_results = scraper.scrape_apt_listing(num_requested_pages=1, **direct_params)
            
            if not raw_results:
                print(f"No listings found for neighborhood {hood_id}")
                return {
                    "hood_id": hood_id,
                    "status": "no_data",
                    "listings_count": 0,
                    "processing_time": 0
                }
            
            start_time = time.time()
            
            # Transform: Parse the raw listings data
            print(f"Parsing {len(raw_results)} raw listings...")
            parsed_results = parse_listings(raw_results)
            
            if not parsed_results or not parsed_results.get('listings'):
                print(f"No valid listings after parsing for neighborhood {hood_id}")
                return {
                    "hood_id": hood_id,
                    "status": "no_valid_data",
                    "listings_count": 0,
                    "processing_time": time.time() - start_time
                }
            
            # Transform: Enrich listings with additional attributes using the same scraper instance
            print(f"Enriching {len(parsed_results['listings'])} listings...")
            enriched_listings = enrich_listings(parsed_results['listings'], scraper)
            parsed_results['listings'] = enriched_listings
            parsed_results['neighborhood_id'] = hood_id
            
            # Load: Save to database
            print(f"Saving listings to database...")
            populate_result = populate_listings(parsed_results)
            
            processing_time = time.time() - start_time
            
            print(f"Successfully processed neighborhood {hood_id} in {processing_time:.2f} seconds")
            
            # Rate limiting - sleep for 3 seconds as in original script
            time.sleep(3)
            
            return {
                "hood_id": hood_id,
                "status": "success",
                "listings_count": len(parsed_results['listings']),
                "images_count": len(parsed_results.get('images', [])),
                "processing_time": processing_time,
                "populate_result": populate_result
            }
            
        except Exception as e:
            print(f"Error processing neighborhood {hood_id}: {str(e)}")
            
            # Sleep even on error to maintain rate limiting
            time.sleep(3)
            
            # Re-raise with more context for Airflow
            raise AirflowException(f"Failed to process neighborhood {hood_id}: {str(e)}")

    @task
    def generate_summary_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary report of the ETL process across all neighborhoods.
        
        Args:
            results: List of results from each neighborhood processing task
            
        Returns:
            Dict[str, Any]: Summary statistics and report
        """
        successful = [r for r in results if r.get('status') == 'success']
        no_data = [r for r in results if r.get('status') in ['no_data', 'no_valid_data']]
        api_failed = [r for r in results if r.get('status') == 'scraper_initialization_failed']
        other_failed = [r for r in results if r.get('status') not in ['success', 'no_data', 'no_valid_data', 'scraper_initialization_failed']]
        
        total_listings = sum(r.get('listings_count', 0) for r in successful)
        total_processing_time = sum(r.get('processing_time', 0) for r in results)
        
        summary = {
            "total_neighborhoods": len(results),
            "successful_neighborhoods": len(successful),
            "api_failed_neighborhoods": len(api_failed),
            "other_failed_neighborhoods": len(other_failed),
            "no_data_neighborhoods": len(no_data),
            "total_listings_processed": total_listings,
            "total_processing_time_seconds": total_processing_time,
            "average_listings_per_neighborhood": total_listings / len(successful) if successful else 0,
            "api_failed_hood_ids": [r['hood_id'] for r in api_failed],
            "other_failed_hood_ids": [r['hood_id'] for r in other_failed],
            "no_data_hood_ids": [r['hood_id'] for r in no_data]
        }
        
        print("ETL Summary Report:")
        print(f"- Total neighborhoods: {summary['total_neighborhoods']}")
        print(f"- Successful: {summary['successful_neighborhoods']}")
        print(f"- API failures: {summary['api_failed_neighborhoods']}")
        print(f"- Other failures: {summary['other_failed_neighborhoods']}")
        print(f"- No data: {summary['no_data_neighborhoods']}")
        print(f"- Total listings: {summary['total_listings_processed']}")
        print(f"- Total processing time: {summary['total_processing_time_seconds']:.2f}s")
        
        if summary['api_failed_hood_ids']:
            print(f"- API failed neighborhood IDs: {summary['api_failed_hood_ids']}")
        if summary['other_failed_hood_ids']:
            print(f"- Other failed neighborhood IDs: {summary['other_failed_hood_ids']}")
            
        return summary

    # Define the workflow
    neighborhood_ids = get_neighborhood_ids()
    
    # Create dynamic parallel tasks for each neighborhood using expand()
    # This creates one task instance per neighborhood ID returned by get_neighborhood_ids()
    etl_results = fetch_and_process_single_hood.expand(hood_id=neighborhood_ids)
    
    # Generate summary report after all ETL tasks complete
    summary = generate_summary_report(etl_results)
    
    # Set up dependencies
    neighborhood_ids >> etl_results >> summary

# Instantiate the DAG
yad2_listings_etl_dag = yad2_listings_etl()
