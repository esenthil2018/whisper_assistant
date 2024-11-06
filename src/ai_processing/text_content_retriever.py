# src/ai_processing/text_content_retriever.py

import logging
from typing import Dict, Any, List, Optional
import chromadb
from chromadb.utils import embedding_functions
import os

class TextContentRetriever:
    """Retrieve content from markdown and text files stored in ChromaDB."""
    
    def __init__(self, persist_directory: str):
        self.logger = logging.getLogger(__name__)
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize OpenAI embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv('OPENAI_API_KEY'),
            model_name="text-embedding-3-small"
        )
        
        # Get the documentation_text collection
        try:
            self.text_collection = self.client.get_collection(
                name="documentation_text",
                embedding_function=self.embedding_function
            )
        except Exception as e:
            self.logger.error(f"Error getting documentation_text collection: {e}")
            self.text_collection = None

    def get_text_content(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve relevant text content for a query."""
        if not self.text_collection:
            return []

        try:
            # Search in the text collection
            results = self.text_collection.query(
                query_texts=[query],
                n_results=5,
                include=['documents', 'metadatas', 'distances']
            )

            if not results['documents'][0]:
                return []

            # Format results
            formatted_results = []
            for doc, metadata, distance in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                relevance_score = 1.0 - min(distance, 1.0)
                if relevance_score > 0.2:  # Minimum relevance threshold
                    formatted_results.append({
                        'content': doc,
                        'metadata': metadata,
                        'type': 'documentation',
                        'relevance_score': relevance_score
                    })

            return formatted_results

        except Exception as e:
            self.logger.error(f"Error retrieving text content: {e}")
            return []

    def check_specific_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """Check for content from a specific file."""
        if not self.text_collection:
            return None

        try:
            # Search for content from specific file
            results = self.text_collection.query(
                query_texts=[filename],
                n_results=10,
                where={"file_name": filename}
            )

            if not results['documents'][0]:
                return None

            # Combine all sections from the file
            content = "\n".join(results['documents'][0])
            metadata = results['metadatas'][0][0]

            return {
                'content': content,
                'metadata': metadata,
                'type': 'documentation'
            }

        except Exception as e:
            self.logger.error(f"Error retrieving specific file content: {e}")
            return None