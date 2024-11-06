# src/ai_processing/context_retriever.py
# src/ai_processing/context_retriever.py
from typing import Dict, List, Any, Optional
import logging
from difflib import SequenceMatcher
import json
from datetime import datetime

class ContextRetriever:
    """Enhanced context retriever with better context processing."""
    
    def __init__(self, storage_manager):
        self.logger = logging.getLogger(__name__)
        self.storage = storage_manager
        self.max_context_items = 5
        self.min_similarity_score = 0.2
        
        # Enhanced key terms for better matching
        self.key_terms = {
            'api': ['function', 'method', 'endpoint', 'call', 'api', 'interface', 'use', 'using'],
            'code': ['implementation', 'class', 'function', 'method', 'variable', 'code', 'example'],
            'documentation': ['documentation', 'guide', 'example', 'tutorial', 'readme', 'how to', 'usage'],
            'setup': ['setup', 'install', 'requirement', 'dependency', 'package', 'installation']
        }

    def get_context(self, processed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant context with improved search."""
        try:
            self.logger.info(f"Getting context for query: {processed_query}")
            context = {}
            
            # Get context for each query type
            for query_type in processed_query['query_type']:
                results = []
                search_terms = self._expand_search_terms(processed_query, query_type)
                
                for term in search_terms:
                    # Search vector store
                    vector_results = self.storage.search(term, query_type)
                    if vector_results:
                        if isinstance(vector_results, dict):
                            # Handle structured results
                            for result_type, items in vector_results.items():
                                if isinstance(items, list):
                                    results.extend(items)
                        elif isinstance(vector_results, list):
                            # Handle direct list results
                            results.extend(vector_results)
                    
                    # Get metadata context
                    metadata_results = self._get_metadata_context(term, query_type)
                    if metadata_results:
                        results.extend(metadata_results)
                
                if results:
                    context[query_type] = self._rank_results(results, processed_query['original_query'])
            
            # Add repository info if relevant
            if self._is_repo_info_relevant(processed_query):
                repo_context = self._get_repository_info_context(processed_query)
                if repo_context:
                    context['repository'] = repo_context
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error retrieving context: {e}")
            return {}

    def _expand_search_terms(self, processed_query: Dict[str, Any], query_type: str) -> List[str]:
        """Expand search terms for better coverage."""
        terms = {processed_query['original_query']}
        
        # Add type-specific expansions
        if query_type in self.key_terms:
            query_lower = processed_query['original_query'].lower()
            for key_term in self.key_terms[query_type]:
                if key_term in query_lower:
                    # Add variant without the key term
                    stripped_term = query_lower.replace(key_term, '').strip()
                    if stripped_term:
                        terms.add(stripped_term)
        
        # Add entity-specific terms
        for entity_type, entity_value in processed_query['entities'].items():
            if entity_value:
                terms.add(str(entity_value))
                # Add combinations with key terms
                for key_term in self.key_terms.get(query_type, []):
                    terms.add(f"{key_term} {entity_value}")
        
        # Add significant word combinations
        words = processed_query['original_query'].lower().split()
        if len(words) > 2:
            for i in range(len(words)-1):
                terms.add(' '.join(words[i:i+2]))
        
        self.logger.info(f"Expanded terms for {query_type}: {terms}")
        return list(terms)

    
    def _rank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Rank results by relevance score with improved handling."""
        try:
            # Convert all results to a consistent format
            normalized_results = []
            for result in results:
                if not isinstance(result, dict):
                    # Skip non-dictionary results
                    continue
                
                # Create a normalized result structure
                normalized_result = {
                    'content': '',
                    'metadata': {},
                    '_relevance': 0.0
                }
                
                # Extract content
                if isinstance(result.get('content'), str):
                    normalized_result['content'] = result['content']
                elif isinstance(result.get('content'), dict):
                    normalized_result['content'] = json.dumps(result['content'])
                else:
                    normalized_result['content'] = str(result.get('content', ''))
                
                # Extract metadata
                if isinstance(result.get('metadata'), dict):
                    normalized_result['metadata'] = result['metadata']
                
                # Calculate or use existing relevance score
                if '_relevance' in result:
                    normalized_result['_relevance'] = float(result['_relevance'])
                else:
                    normalized_result['_relevance'] = self._calculate_relevance_score(
                        normalized_result['content'],
                        query
                    )
                
                normalized_results.append(normalized_result)
            
            # Sort by relevance
            normalized_results.sort(key=lambda x: x['_relevance'], reverse=True)
            
            # Remove duplicates while preserving order
            seen_content = set()
            unique_results = []
            for result in normalized_results:
                content_hash = hash(result['content'])
                if content_hash not in seen_content and result['_relevance'] >= self.min_similarity_score:
                    seen_content.add(content_hash)
                    unique_results.append(result)
            
            return unique_results[:self.max_context_items]
            
        except Exception as e:
            self.logger.error(f"Error ranking results: {e}")
            return []

    def _calculate_relevance_score(self, content: str, query: str) -> float:
        """Calculate relevance score between content and query."""
        try:
            if not content or not query:
                return 0.0
                
            # Convert content to string if it's not already
            content_str = str(content).lower()
            query_str = str(query).lower()
            
            # Calculate base similarity score
            base_score = SequenceMatcher(None, content_str, query_str).ratio()
            
            # Boost score for exact matches
            if query_str in content_str:
                base_score += 0.2
            
            # Boost score for partial word matches
            query_words = set(query_str.split())
            content_words = set(content_str.split())
            word_match_ratio = len(query_words.intersection(content_words)) / len(query_words)
            
            # Combine scores with weights
            final_score = (base_score * 0.6) + (word_match_ratio * 0.4)
            
            # Ensure score is between 0 and 1
            return min(max(final_score, 0.0), 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {e}")
            return 0.0

    def _get_metadata_context(self, query: str, query_type: str) -> List[Dict[str, Any]]:
        """Get context from metadata store based on query type."""
        try:
            results = []
            
            # Get API metadata for API queries
            if query_type == 'api':
                api_results = self.storage.metadata_store.search_metadata(query)
                if isinstance(api_results, dict) and 'apis' in api_results:
                    for api in api_results['apis']:
                        results.append({
                            'content': self._format_api_content(api),
                            'metadata': {
                                'type': 'api',
                                'name': api.get('name', ''),
                                'file_path': api.get('file_path', '')
                            }
                        })
            
            # Get environment variables for env/setup queries
            if query_type in ['env', 'setup']:
                env_vars = self.storage.metadata_store.get_env_variables()
                for var in env_vars:
                    if self._calculate_relevance_score(f"{var['name']} {var.get('description', '')}", query) >= self.min_similarity_score:
                        results.append({
                            'content': self._format_env_var_content(var),
                            'metadata': {
                                'type': 'env_var',
                                'name': var['name'],
                                'is_required': var.get('is_required', False)
                            }
                        })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting metadata context: {e}")
            return []

    def _format_api_content(self, api: Dict[str, Any]) -> str:
        """Format API metadata into readable content."""
        parts = [f"API: {api.get('name', '')}"]
        
        if api.get('docstring'):
            parts.append(f"Description: {api['docstring']}")
        
        if api.get('parameters'):
            params = api['parameters']
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    params = [params]
            parts.append("Parameters:")
            for param in params:
                if isinstance(param, dict):
                    parts.append(f"- {param.get('name', '')}: {param.get('type', 'Any')}")
                else:
                    parts.append(f"- {param}")
        
        if api.get('return_type'):
            parts.append(f"Returns: {api['return_type']}")
        
        return '\n'.join(parts)

    def _format_env_var_content(self, var: Dict[str, Any]) -> str:
        """Format environment variable metadata into readable content."""
        parts = [f"Environment Variable: {var['name']}"]
        
        if var.get('description'):
            parts.append(f"Description: {var['description']}")
        
        parts.append(f"Required: {'Yes' if var.get('is_required') else 'No'}")
        
        if var.get('default_value'):
            parts.append(f"Default Value: {var['default_value']}")
        
        return '\n'.join(parts)

    def _is_repo_info_relevant(self, processed_query: Dict[str, Any]) -> bool:
        """Check if repository info is relevant to the query."""
        query_lower = processed_query['original_query'].lower()
        relevant_terms = {
            'setup', 'install', 'requirement', 'dependency', 'package', 
            'version', 'configuration', 'repository', 'structure'
        }
        return bool(
            any(term in query_lower for term in relevant_terms) or 
            'setup' in processed_query['query_type']
        )

    def _get_repository_info_context(self, processed_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get context from repository info with improved relevance checking."""
        try:
            repo_info = self.storage.metadata_store.get_repository_info()
            if not repo_info:
                return []

            context = []
            query = processed_query['original_query']

            # Process repository statistics
            if 'stats' in repo_info:
                try:
                    stats = json.loads(repo_info['stats'])
                    stats_content = f"Repository Statistics:\n{json.dumps(stats, indent=2)}"
                    relevance = self._calculate_relevance_score(stats_content, query)
                    if relevance >= self.min_similarity_score:
                        context.append({
                            'content': stats_content,
                            'metadata': {'type': 'repository_stats'},
                            '_relevance': relevance
                        })
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse repository stats")

            # Process summaries
            if 'summaries' in repo_info:
                try:
                    summaries = json.loads(repo_info['summaries'])
                    for summary in summaries:
                        if isinstance(summary, dict):
                            content = summary.get('content', '')
                            relevance = self._calculate_relevance_score(content, query)
                            if relevance >= self.min_similarity_score:
                                context.append({
                                    'content': content,
                                    'metadata': {
                                        'type': 'repository_summary',
                                        'file_path': summary.get('file_path', '')
                                    },
                                    '_relevance': relevance
                                })
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse repository summaries")

            return sorted(
                context,
                key=lambda x: x.get('_relevance', 0),
                reverse=True
            )[:self.max_context_items]
            
        except Exception as e:
            self.logger.error(f"Error getting repository info context: {e}")
            return []

    



