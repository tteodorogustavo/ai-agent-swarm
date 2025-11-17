"""
Ingestion Runner Script

This is an executable script. Its sole purpose is to call the main
ingestion service logic from `app.services.rag_service`.

This script is what the Dockerfile or cron job will execute to always ingest
new data into the RAG system.
"""
import os
import logging
from dotenv import load_dotenv
from app.services.rag_service import run_full_ingestion

# Set up logging for the script itself
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

load_dotenv()

if __name__ == "__main__":
    logging.info("--- Starting RAG Ingestion Script ---")
    
    # Safety check: Ensure the API key is available in the environment
    if not os.getenv("OPENAI_API_KEY"):
        logging.error("FATAL: OPENAI_API_KEY not found in environment.")
        logging.error("Please set it in your .env file or environment variables.")
    else:
        try:
            # Call the main logic from the service module
            run_full_ingestion()
            logging.info("--- RAG Ingestion Script Finished Successfully ---")
        except Exception as e:
            logging.error(f"An error occurred during ingestion: {e}", exc_info=True)
            logging.info("--- RAG Ingestion Script Failed ---")
        
        else:
            logging.info("--- RAG Ingestion Script Finished Successfully ---")