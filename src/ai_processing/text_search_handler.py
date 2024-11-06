# src/ai_processing/text_search_handler.py

from typing import Dict, Any, Optional
import logging
from .text_content_retriever import TextContentRetriever

class TextSearchHandler:
    """Handle text content searching and LLM integration."""
    
    def __init__(self, persist_directory: str):
        self.logger = logging.getLogger(__name__)
        self.text_retriever = TextContentRetriever(persist_directory)

    async def handle_text_query(self, query: str, llm_interface: Any) -> Optional[Dict[str, Any]]:
        """Handle queries that might need text content."""
        try:
            # Check for specific file mentions
            specific_files = {
                'requirements.txt': ['requirement', 'dependency', 'dependencies', 'package'],
                'README.md': ['readme', 'instruction', 'setup', 'overview'],
                'CHANGELOG.md': ['changelog', 'change', 'update', 'version'],
                'model-card.md': ['model', 'card', 'capability', 'specification']
            }

            # Check if query is about a specific file
            target_file = None
            for file, keywords in specific_files.items():
                if any(keyword in query.lower() for keyword in keywords):
                    target_file = file
                    break

            # Get content
            if target_file:
                content = self.text_retriever.check_specific_file(target_file)
            else:
                results = self.text_retriever.get_text_content(query)
                content = {'documents': results} if results else None

            if not content:
                return None

            # Generate response using LLM
            context = {'documentation': [content]} if isinstance(content, dict) else {'documentation': content}
            
            response = await llm_interface.generate_response(
                query=query,
                context=context,
                processed_query={'query_type': ['documentation']}
            )

            return response

        except Exception as e:
            self.logger.error(f"Error handling text query: {e}")
            return None