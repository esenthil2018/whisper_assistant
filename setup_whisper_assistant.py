import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import logging
import asyncio
from src.data_ingestion import DataIngestion
from src.data_ingestion.content_analyzer import ContentAnalyzer
from src.storage import StorageManager
from typing import Dict, Any
from src.data_ingestion.text_processor import TextProcessor  # Add this import

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('setup.log')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def create_directories():
    """Create necessary directories."""
    directories = [
        './data/embeddings',
        './data/raw',
        './data/processed',
        './logs'
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

async def process_repository_content(content_analyzer: ContentAnalyzer, results: Dict[str, Any]) -> Dict[str, Any]:
    """Process repository content and generate enhanced data."""
    try:
        analysis_results = await content_analyzer.analyze_repository(results)
        
        # Create comprehensive repository info
        repo_info = {
            'stats': {
                'total_files': len(results['files']),
                'total_apis': len(results.get('apis', [])),
                'total_env_vars': len(results.get('env_vars', [])),
                'total_documentation': len(results.get('documentation', [])),
            },
            'summaries': analysis_results.get('file_summaries', []),
            'qa_pairs': analysis_results.get('qa_pairs', []),
            'technical_concepts': analysis_results.get('technical_concepts', []),
            'analysis_metadata': {
                'timestamp': str(datetime.now()),
                'version': '1.0',
                'source_repo': "https://github.com/openai/whisper"
            }
        }
        
        return {
            'analysis_results': analysis_results,
            'repo_info': repo_info
        }
    except Exception as e:
        logger.error(f"Error processing repository content: {e}")
        raise

async def store_all_data(
    storage: StorageManager, 
    results: Dict[str, Any],
    processed_content: Dict[str, Any]
):
    """Store all repository data including enhanced content."""
    try:
        # Store base repository data
        storage.store_repository_data({
            **results,
            'repo_info': processed_content['repo_info']
        })
        
        return True
    except Exception as e:
        logger.error(f"Error storing data: {e}")
        raise

async def process_text_content(local_path: str, persist_directory: str) -> bool:
    """Process text and markdown files separately."""
    try:
        logger.info("Processing text and markdown files...")
        text_processor = TextProcessor(local_path, persist_directory)
        results = text_processor.process_text_files()
        
        logger.info(f"Processed {results['processed_files']} text files")
        if results['failed_files'] > 0:
            logger.warning(f"Failed to process {results['failed_files']} files")
        
        # Log detailed results
        logger.info(f"Successfully processed documentation: {len(results['documentation'])} files")
        
        return True
    except Exception as e:
        logger.error(f"Error processing text content: {e}")
        return False

async def main():
    # Setup
    load_dotenv()
    create_directories()
    
    try:
        # Initialize components
        storage = StorageManager(
            persist_directory='./data/embeddings',
            metadata_db_path='./data/metadata.db',
            preserve_data=True
        )
        
        ingestion = DataIngestion(
            repo_url="https://github.com/openai/whisper",
            local_path=str(Path("./data/raw/whisper"))
        )
        
        content_analyzer = ContentAnalyzer(os.getenv('OPENAI_API_KEY'))
        
        # Step 1: Initialize Repository
        logger.info("Initializing repository...")
        if not ingestion.initialize_repo():
            raise Exception("Failed to initialize repository")
        
        # Step 2: Process Repository
        logger.info("Processing repository content...")
        results = ingestion.process_repository()
        
        # Step 3: Generate Enhanced Content
        logger.info("Analyzing repository content...")
        processed_content = await process_repository_content(content_analyzer, results)
        
        # Step 4: Store All Data
        logger.info("Storing processed data...")
        await store_all_data(storage, results, processed_content)
        
        # Step 5: Process Text and Markdown Files
        logger.info("Starting text and markdown file processing...")
        text_processing_result = await process_text_content(
            local_path=str(Path("./data/raw/whisper")),
            persist_directory='./data/embeddings'
        )
        
        if text_processing_result:
            logger.info("Text and markdown processing completed successfully")
        else:
            logger.warning("Text and markdown processing completed with some issues")
        
        # Log Results
        logger.info(f"Processed {processed_content['repo_info']['stats']['total_files']} files")
        logger.info(f"Generated {len(processed_content['repo_info']['summaries'])} file summaries")
        logger.info(f"Generated {len(processed_content['repo_info']['qa_pairs'])} Q&A pairs")
        logger.info(f"Generated {len(processed_content['repo_info']['technical_concepts'])} technical concepts")
        
        logger.info("Setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main())