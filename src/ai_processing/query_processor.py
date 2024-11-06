# src/ai_processing/query_processor.py
from typing import Dict, List, Optional, Any
import logging
import re

class QueryProcessor:
    """Process and classify user queries."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Query type patterns
        self.patterns = {
            'api': r'(api|endpoint|function|method|how to call|usage|interface|use|using)',
            'setup': r'(setup|install|requirements?|dependencies?|package|configuration)',
            'code': r'(implementation|code|source|how does it work|internal|show|example)',
            'documentation': r'(documentation|explain|what is|purpose|guide|tutorial|how to)'
        }

    def process_query(self, query: str) -> Dict[str, Any]:
        """Process and classify the user query."""
        try:
            query_type = self._classify_query(query)
            entities = self._extract_entities(query)
            
            processed_query = {
                'original_query': query,
                'query_type': query_type,
                'entities': entities,
                'search_params': self._generate_search_params(query_type, entities)
            }
            
            self.logger.info(f"Processed query: {processed_query}")
            return processed_query
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            raise

    def _classify_query(self, query: str) -> List[str]:
        """Classify the type of query based on patterns."""
        query_lower = query.lower()
        query_types = set()  # Use set to avoid duplicates
        
        # Check each pattern
        for qtype, pattern in self.patterns.items():
            if re.search(pattern, query_lower):
                query_types.add(qtype)
        
        # Add documentation type for questions
        if re.search(r'^(what|how|why|when|where|which|can|does)', query_lower):
            query_types.add('documentation')
        
        # If looking for setup/installation
        if re.search(r'(setup|install|configure|requirement)', query_lower):
            query_types.add('setup')
        
        # If asking about specific code
        if re.search(r'(file|code|implementation|show|content)', query_lower):
            query_types.add('code')
        
        return list(query_types) if query_types else ['documentation']

    def _extract_entities(self, query: str) -> Dict[str, Optional[str]]:
        """Extract relevant entities from the query."""
        entities = {
            'function_name': None,
            'variable_name': None,
            'file_path': None,
            'specific_term': None
        }
        
        # Extract function names
        function_match = re.search(r'\b\w+(?:_\w+)*\(\)?', query)
        if function_match:
            entities['function_name'] = function_match.group().rstrip('()')
        
        # Extract environment variables
        env_match = re.search(r'\b[A-Z][A-Z_]+\b', query)
        if env_match:
            entities['variable_name'] = env_match.group()
        
        # Extract file paths
        path_match = re.search(r'\b[\w/]+\.(py|json|yml|yaml|md|txt)\b', query)
        if path_match:
            entities['file_path'] = path_match.group()
        
        # Extract specific terms
        quoted_terms = re.findall(r'["\'](.*?)["\']', query)
        if quoted_terms:
            entities['specific_term'] = quoted_terms[0]
        else:
            significant_terms = re.findall(r'\b([a-zA-Z_]\w{2,})\b', query)
            if significant_terms:
                common_words = {'how', 'what', 'the', 'for', 'and', 'show', 'me', 'is', 'are', 'this'}
                filtered_terms = [term for term in significant_terms if term.lower() not in common_words]
                if filtered_terms:
                    entities['specific_term'] = filtered_terms[0]
        
        return entities

    def _generate_search_params(
        self,
        query_types: List[str],
        entities: Dict[str, Optional[str]]
    ) -> Dict[str, Any]:
        """Generate search parameters based on query classification and entities."""
        search_params = {
            'types': query_types,
            'filters': {}
        }
        
        for entity_type, value in entities.items():
            if value:
                search_params['filters'][entity_type] = value
        
        return search_params

    def analyze_query_intent(self, query: str) -> Dict[str, bool]:
        """Analyze the intent behind the query."""
        return {
            'is_how_to': bool(re.search(r'how (to|do|can|should)', query.lower())),
            'is_what_is': bool(re.search(r'what (is|are|does)', query.lower())),
            'is_why': bool(re.search(r'why', query.lower())),
            'is_comparison': bool(re.search(r'(compare|difference|vs|versus)', query.lower())),
            'needs_example': bool(re.search(r'(example|sample|show)', query.lower())),
            'is_error': bool(re.search(r'(error|bug|issue|problem|fail)', query.lower()))
        }

    def get_suggested_queries(self, query: str, query_type: List[str]) -> List[str]:
        """Generate suggested follow-up queries."""
        suggestions = set()
        
        if 'api' in query_type:
            suggestions.update([
                "Can you show an example usage?",
                "What are the parameters?",
                "What does this function return?"
            ])
            
        if 'code' in query_type:
            suggestions.update([
                "How does this work internally?",
                "What are the dependencies?",
                "Are there any related functions?"
            ])
            
        if 'env' in query_type:
            suggestions.update([
                "What are the required settings?",
                "Are there any optional configurations?",
                "What's the default value?"
            ])
            
        return list(suggestions)[:3]
