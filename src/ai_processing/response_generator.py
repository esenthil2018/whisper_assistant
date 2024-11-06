# src/ai_processing/response_generator.py
from typing import Dict, List, Any
import logging
import re
import json

class ResponseGenerator:
    """Generate final responses for user queries."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_response(
        self,
        llm_response: Dict[str, Any],
        processed_query: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate the final response with appropriate formatting."""
        try:
            response = {
                'answer': self._format_answer(llm_response['answer']),
                'sources': llm_response['sources'],
                'metadata': {
                    'query_type': processed_query['query_type'],
                    'context_used': self._summarize_context(context),
                    **llm_response['metadata']
                }
            }
            
            # Add code snippets if relevant
            if 'code' in processed_query['query_type']:
                response['code_snippets'] = self._extract_code_snippets(llm_response['answer'])
            
            # Add API details if relevant
            if 'api' in processed_query['query_type']:
                response['api_details'] = self._extract_api_details(context)
            
            # Add environment variables if relevant
            if 'env' in processed_query['query_type']:
                response['env_vars'] = self._extract_env_vars(context)
            
            return response
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            raise

    def _format_answer(self, answer: str) -> str:
        """Format the answer for better readability."""
        # Remove excessive newlines
        answer = re.sub(r'\n{3,}', '\n\n', answer)
        
        # Ensure code blocks are properly formatted
        answer = re.sub(r'```(?!python|bash|json|yaml)', '```python', answer)
        
        # Format inline code
        answer = re.sub(r'`([^`]+)`', r'`\1`', answer)
        
        return answer

    def _summarize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize what context was used."""
        return {
            'api_docs_used': len(context.get('api', [])),
            'code_snippets_used': len(context.get('code', [])),
            'documentation_used': len(context.get('doc', [])),
            'env_vars_used': len(context.get('env', [])),
            'related_items_used': len(context.get('related', []))
        }

    def _extract_code_snippets(self, answer: str) -> List[str]:
        """Extract code snippets from the answer."""
        code_blocks = []
        for match in re.finditer(r'```(?:python)?\n(.*?)\n```', answer, re.DOTALL):
            code_blocks.append(match.group(1).strip())
        return code_blocks

    def _extract_api_details(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract API details from context."""
        api_details = {}
        if 'api' in context:
            for item in context['api']:
                if isinstance(item, dict):
                    name = item.get('name', 'unknown')
                    api_details[name] = {
                        'parameters': item.get('parameters', []),
                        'return_type': item.get('return_type'),
                        'docstring': item.get('docstring'),
                        'examples': self._extract_examples(item)
                    }
        return api_details

    def _extract_env_vars(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract environment variables from context."""
        env_vars = []
        if 'env' in context:
            for item in context['env']:
                if isinstance(item, dict):
                    env_vars.append({
                        'name': item.get('name'),
                        'description': item.get('description'),
                        'required': item.get('is_required', False),
                        'default': item.get('default_value')
                    })
        return env_vars

    def _extract_examples(self, item: Dict[str, Any]) -> List[str]:
        """Extract code examples from documentation."""
        examples = []
        docstring = item.get('docstring', '')
        if docstring:
            matches = re.finditer(r'Example:?\s*```(?:python)?\n(.*?)\n```', docstring, re.DOTALL)
            examples.extend(match.group(1).strip() for match in matches)
        return examples

    def format_for_display(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format the response for display in the UI."""
        display_response = {
            'main_content': response['answer'],
            'supplementary_info': {}
        }

        # Add code snippets if available
        if 'code_snippets' in response and response['code_snippets']:
            display_response['supplementary_info']['code_examples'] = response['code_snippets']

        # Add API details if available
        if 'api_details' in response and response['api_details']:
            display_response['supplementary_info']['api_reference'] = response['api_details']

        # Add environment variables if available
        if 'env_vars' in response and response['env_vars']:
            display_response['supplementary_info']['environment_setup'] = response['env_vars']

        # Add sources
        if 'sources' in response and response['sources']:
            display_response['supplementary_info']['references'] = response['sources']

        return display_response