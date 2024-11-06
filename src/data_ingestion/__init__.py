# src/data_ingestion/__init__.py
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import git
from .repo_crawler import RepoCrawler
from .code_parser import CodeParser  # This import should now work
from .extractors.api_extractor import APIExtractor
from .extractors.env_extractor import EnvExtractor
from .extractors.doc_extractor import DocExtractor
from .content_analyzer import ContentAnalyzer

class DataIngestion:
    """Main class for handling data ingestion from repositories."""
    
    def __init__(self, repo_url: str, local_path: str):
        self.logger = logging.getLogger(__name__)
        self.repo_url = repo_url
        self.local_path = Path(local_path)
        
        # Initialize components
        self.crawler = RepoCrawler(repo_url, str(self.local_path))
        self.parser = CodeParser()  # Using the updated CodeParser
        self.api_extractor = APIExtractor()
        self.env_extractor = EnvExtractor()
        self.doc_extractor = DocExtractor()

    def initialize_repo(self) -> bool:
        """Initialize or update the repository."""
        try:
            # Create directory if it doesn't exist
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use the crawler to clone/update the repository
            success = self.crawler.clone_repo() is not None
            
            if success:
                self.logger.info(f"Repository initialized successfully at {self.local_path}")
            else:
                self.logger.error("Failed to initialize repository")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error initializing repository: {e}")
            return False

    def update_repo(self) -> bool:
        """Update the repository to the latest version."""
        try:
            return self.crawler.update_repo()
        except Exception as e:
            self.logger.error(f"Error updating repository: {e}")
            return False

    def process_repository(self) -> dict:
        """Process the entire repository and extract all relevant information."""
        try:
            results = {
                'files': [],
                'apis': [],
                'env_vars': [],
                'documentation': []
            }

            # Get all Python files
            python_files = self.crawler.get_file_list(['.py','.md', '.txt'])
            
            for file_path in python_files:
                full_path = self.local_path / file_path
                
                try:
                    # Extract documentation first
                    doc_result = self.doc_extractor.extract_documentation(full_path)
                    if doc_result and 'content' in doc_result:
                        results['documentation'].append(doc_result)

                    # Parse code structure
                    code_structure = self.parser.parse_file(full_path)
                    if code_structure:
                        results['files'].append({
                            'path': str(file_path),
                            'structure': code_structure,
                            'content': doc_result.get('content', {})
                        })

                    # Extract APIs
                    apis = self.api_extractor.extract_apis(full_path)
                    if apis:
                        results['apis'].extend(apis)

                    # Extract environment variables
                    env_vars = self.env_extractor.extract_env_vars(full_path)
                    if env_vars:
                        results['env_vars'].extend(env_vars)

                except Exception as e:
                    self.logger.error(f"Error processing file {file_path}: {e}")
                    continue

            self.logger.info(f"Processed {len(results['files'])} files successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing repository: {e}")
            raise

    def cleanup(self) -> bool:
        """Clean up temporary files and resources."""
        try:
            # Add any cleanup logic here if needed
            return True
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return False