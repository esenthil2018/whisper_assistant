# src/ai_processing/__init__.py

from typing import Dict, Any, Optional, List
import logging
import json
from .query_processor import QueryProcessor
from .context_retriever import ContextRetriever
from .llm_interface import LLMInterface
from .response_generator import ResponseGenerator
from .text_search_handler import TextSearchHandler


class AIProcessor:
    """Main class for processing queries about the Whisper repository."""
    
    def __init__(self, storage_manager, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.query_processor = QueryProcessor()
        self.context_retriever = ContextRetriever(storage_manager)
        self.llm_interface = LLMInterface(openai_api_key)
        self.response_generator = ResponseGenerator()
        
        self.storage = storage_manager
        
        # Setup enhanced logging
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)

    # src/ai_processing/__init__.py

    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query and generate a response."""
        try:
            self.logger.info(f"Processing query: {query}")
            
            # Check cache only if available
            if hasattr(self.storage, 'cache') and self.storage.cache:
                cached_response = self.storage.cache.get_response(query)
                if cached_response:
                    return cached_response

            # Process the query
            processed_query = self.query_processor.process_query(query)
            self.logger.info(f"Processed query: {processed_query}")
            
            # Retrieve relevant context
            context = self.context_retriever.get_context(processed_query)

            # If regular processing didn't find relevant context, try text content
            if not context or not any(context.values()):
                self.logger.info("No context found in primary search, trying text content...")
                text_handler = TextSearchHandler('./data/embeddings')
                text_response = await text_handler.handle_text_query(query, self.llm_interface)
                if text_response:
                    self.logger.info("Found relevant text content")
                    return text_response
            
            # Log context information
            self._log_context_info(context)
            
            # Generate LLM response
            llm_response = await self.llm_interface.generate_response(
                query,
                context,
                processed_query
            )
            
            # Generate final response
            response = self.response_generator.generate_response(
                llm_response,
                processed_query,
                context
            )
            
            # Add debug information
            response['debug_info'] = {
                'query_type': processed_query['query_type'],
                'context_types': list(context.keys()),
                'context_items': {
                    k: len(v) if isinstance(v, list) else 'N/A'
                    for k, v in context.items()
                }
            }
            
            # Cache response only if cache is available
            if hasattr(self.storage, 'cache') and self.storage.cache:
                self.storage.cache.store_response(query, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return self._create_error_response(query, str(e))

    def _log_context_info(self, context: Dict[str, Any]) -> None:
        """Log detailed information about retrieved context."""
        self.logger.info("\nContext Information:")
        for context_type, items in context.items():
            if isinstance(items, list):
                self.logger.info(f"\n{context_type.upper()} - {len(items)} items found")
                for idx, item in enumerate(items[:2]):  # Log first 2 items of each type
                    self.logger.info(f"\nItem {idx + 1}:")
                    if isinstance(item, dict):
                        self.logger.info(f"Content preview: {str(item.get('content', ''))[:200]}...")
                        self.logger.info(f"Source: {item.get('metadata', {}).get('file_path', 'unknown')}")

    def _verify_context_quality(self, context: Dict[str, Any]) -> bool:
        """Verify that we have sufficient quality context to answer the query."""
        if not context:
            return False
            
        # Check for content in lists
        content_items = [
            item for items in context.values()
            if isinstance(items, list)
            for item in items
            if isinstance(item, dict) and item.get('content')
        ]
        
        if not content_items:
            return False
            
        # Check total content length
        total_content = sum(len(str(item.get('content', ''))) for item in content_items)
        min_content_length = 100  # Minimum characters of context needed
        
        if total_content < min_content_length:
            self.logger.warning(f"Insufficient content length: {total_content} chars")
            return False
            
        return True

    def _create_insufficient_context_response(self, query: str) -> Dict[str, Any]:
        """Create a more informative response for insufficient context."""
        return {
            'answer': """Based on the available repository context, I cannot provide a specific answer to this question. This might be because:
            1. The relevant information is not in the current context
            2. The question might need to be rephrased to match available content
            3. You might want to ask about a different aspect of the repository
            
            Try asking about the following aspects that are well-documented in the context:
            - Repository setup and configuration
            - Code structure and implementation
            - Available APIs and their usage""",
            'sources': [],
            'metadata': {
                'status': 'insufficient_context',
                'query': query
            }
        }

    def _create_error_response(self, query: str, error: str) -> Dict[str, Any]:
        """Create a more detailed error response."""
        return {
            'answer': "I encountered an error processing your query. Please try rephrasing your question.",
            'error': error,
            'metadata': {
                'status': 'error',
                'query': query,
                'error_type': error.split(':')[0] if ':' in error else 'UnknownError'
            }
        }

    async def batch_process_queries(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Process multiple queries in batch."""
        responses = []
        for query in queries:
            response = await self.process_query(query)
            responses.append(response)
        return responses

    def analyze_query_patterns(self, query: str) -> Dict[str, bool]:
        """Analyze query patterns for better response generation."""
        return self.query_processor.analyze_query_intent(query)

    def get_suggested_queries(self, query: str) -> List[str]:
        """Get suggested follow-up queries."""
        processed_query = self.query_processor.process_query(query)
        return self.query_processor.get_suggested_queries(
            query,
            processed_query['query_type']
        )
    
    # Add this method to your src/ai_processing/__init__.py in the AIProcessor class

    async def debug_process_query(self, query: str) -> Dict[str, Any]:
        """Debug version of process_query with detailed logging."""
        try:
            print("\n=== Starting Debug Query Processing ===")
            print(f"\nProcessing query: {query}")
            
            # Check cache
            cached_response = self.storage.cache.get_response(query)
            if cached_response:
                print("\nFound cached response")
                return cached_response

            # Process query
            processed_query = self.query_processor.process_query(query)
            print(f"\nProcessed query type: {processed_query['query_type']}")
            print(f"Processed query entities: {processed_query.get('entities', {})}")
            
            # Get context
            print("\nRetrieving context...")
            context = self.context_retriever.get_context(processed_query)
            
            # Print context summary
            print("\nContext Summary:")
            for context_type, items in context.items():
                if isinstance(items, list):
                    print(f"\n{context_type}: {len(items)} items")
                    for idx, item in enumerate(items[:2]):  # Show first 2 items
                        if isinstance(item, dict):
                            print(f"\nItem {idx + 1} preview:")
                            print(f"Content: {str(item.get('content', ''))[:200]}...")
                            print(f"Source: {item.get('metadata', {}).get('file_path', 'unknown')}")
            
            # Generate response
            print("\nGenerating LLM response...")
            llm_response = await self.llm_interface.generate_response(
                query,
                context,
                processed_query
            )
            
            print(f"\nLLM Response preview: {llm_response.get('answer', '')[:200]}...")
            
            # Generate final response
            response = self.response_generator.generate_response(
                llm_response,
                processed_query,
                context
            )
            
            print("\n=== Debug Processing Complete ===")
            return response
            
        except Exception as e:
            print(f"\nError in debug processing: {e}")
            raise