
# src/storage/__init__.py
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from .vector_store import VectorStore
from .metadata_store import MetadataStore
import json

class StorageManager:
    """Manages all storage components for the Whisper repository analysis."""
    
    def __init__(
        self,
        persist_directory: str,
        metadata_db_path: str,
        preserve_data: bool = True
    ):
        self.logger = logging.getLogger(__name__)
        
        try:
            # Create necessary directories
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            Path(metadata_db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize core components
            self.vector_store = VectorStore(persist_directory)
            self.metadata_store = MetadataStore(metadata_db_path, preserve_data=preserve_data)
            
            self.logger.info("Storage manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing storage manager: {e}")
            raise

    def store_repository_data(self, data: Dict[str, Any]):
        """Store all repository data in appropriate storage systems."""
        try:
            # Store code snippets in vector store
            if 'files' in data:
                self.logger.info("Storing code snippets...")
                self.vector_store.add_code_snippets(data['files'])

            # Store documentation in vector store
            if 'documentation' in data:
                self.logger.info("Storing documentation...")
                self.vector_store.add_documentation(data['documentation'])

            # Store environment variables in metadata store
            if 'env_vars' in data:
                self.logger.info("Storing environment variables...")
                self.metadata_store.store_env_variables(data['env_vars'])

            # Store API metadata
            if 'apis' in data:
                self.logger.info("Storing API metadata...")
                self.metadata_store.store_api_metadata(data['apis'])

            # Store repository info in metadata store
            if 'repo_info' in data:
                self.logger.info("Storing repository info in metadata store...")
                repo_info = {
                    'stats': json.dumps(data['repo_info']['stats']),
                    'summaries': json.dumps(data['repo_info'].get('summaries', [])),
                    'qa_pairs': json.dumps(data['repo_info'].get('qa_pairs', [])),
                    'technical_concepts': json.dumps(data['repo_info'].get('technical_concepts', []))
                }
                self.metadata_store.store_repository_info(repo_info)
                
                # Store enhanced content in vector store
                self.logger.info("Storing enhanced content in vector store...")
                enhanced_content = {
                    'summaries': data['repo_info'].get('summaries', []),
                    'qa_pairs': data['repo_info'].get('qa_pairs', []),
                    'technical_concepts': data['repo_info'].get('technical_concepts', [])
                }
                self.vector_store.add_enhanced_content(enhanced_content)

            self.logger.info("Repository data stored successfully")
        except Exception as e:
            self.logger.error(f"Error storing repository data: {e}")
            raise

    def search(self, query: str, search_type: str = 'all') -> Dict[str, Any]:
        """Search for information across all storage systems."""
        try:
            results = {}
            
            # Search vector store
            if search_type in ['all', 'code']:
                code_results = self.vector_store.search(query, 'code')
                if code_results:
                    results['code_snippets'] = code_results
                    self.logger.info(f"Found {len(code_results)} code results")
            
            if search_type in ['all', 'documentation']:
                doc_results = self.vector_store.search(query, 'documentation')
                if doc_results:
                    results['documentation'] = doc_results
                    self.logger.info(f"Found {len(doc_results)} documentation results")
            
            # Search metadata store
            if search_type in ['all', 'metadata']:
                metadata_results = self.metadata_store.search_metadata(query)
                if metadata_results:
                    results['metadata'] = metadata_results
                    self.logger.info(f"Found metadata results")
            
            return results
        except Exception as e:
            self.logger.error(f"Error searching: {e}")
            return {}

    def get_repository_info(self) -> Dict[str, Any]:
        """Get comprehensive repository information."""
        try:
            return {
                'env_variables': self.metadata_store.get_env_variables(),
                'api_metadata': self.metadata_store.get_api_metadata(),
                'storage_stats': {
                    'vector_store': {
                        'code_snippets': len(self.vector_store.collections['code'].get()),
                        'documentation': len(self.vector_store.collections['documentation'].get())
                    }
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting repository info: {e}")
            raise

    def verify_storage(self) -> Dict[str, Any]:
        """Verify storage state and return statistics."""
        try:
            # Get collection statistics
            vector_stats = self.vector_store.get_collection_stats()
            
            # Get metadata statistics
            metadata_stats = {
                'env_variables': len(self.metadata_store.get_env_variables()),
                'api_metadata': len(self.metadata_store.get_api_metadata()),
                'repository_info': bool(self.metadata_store.get_repository_info())
            }
            
            verification_result = {
                'vector_store': {
                    'code_snippets': vector_stats.get('code', 0),
                    'documentation': vector_stats.get('documentation', 0),
                    'summaries': vector_stats.get('file_summaries', 0),
                    'qa_pairs': vector_stats.get('qa_pairs', 0),
                    'technical_concepts': vector_stats.get('technical_concepts', 0)
                },
                'metadata_store': metadata_stats,
                'status': 'success'
            }
            
            # Log verification results
            self.logger.info("Storage verification results:")
            for store, stats in verification_result.items():
                if store != 'status':
                    self.logger.info(f"{store}:")
                    for key, value in stats.items():
                        self.logger.info(f"  - {key}: {value}")
            
            return verification_result
            
        except Exception as e:
            self.logger.error(f"Storage verification failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
