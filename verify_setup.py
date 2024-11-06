import logging
from pathlib import Path
from dotenv import load_dotenv
from src.storage import StorageManager

def verify_setup():
    """Verify that the data was properly indexed."""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Load environment variables
        load_dotenv()

        # Initialize storage manager with only the required parameters
        storage = StorageManager(
            persist_directory='./data/embeddings',
            metadata_db_path='./data/metadata.db',
            preserve_data=True
        )

        # Check vector store collections
        collection_stats = storage.vector_store.get_collection_stats()
        logger.info(f"Vector store collection stats: {collection_stats}")
        
        if collection_stats['code'] == 0 or collection_stats['documentation'] == 0:
            logger.error("Vector store collections are empty!")
            return False

        # Check metadata store
        repo_info = storage.get_repository_info()
        logger.info(f"Repository info stats: {repo_info}")
        
        if not repo_info:
            logger.error("Metadata store is empty!")
            return False

        # Log successful verification with detailed stats
        logger.info("Setup verification completed successfully")
        logger.info(f"Code snippets indexed: {collection_stats['code']}")
        logger.info(f"Documentation items indexed: {collection_stats['documentation']}")
        logger.info(f"Total indexed items: {collection_stats['code'] + collection_stats['documentation']}")
        return True

    except Exception as e:
        logger.error(f"Setup verification failed: {e}")
        return False

if __name__ == "__main__":
    # First verify .env file exists
    if not Path('.env').exists():
        print("Error: .env file not found!")
        print("Please create a .env file with your OpenAI API key:")
        print("OPENAI_API_KEY=your-api-key-here")
        exit(1)
        
    verify_setup()