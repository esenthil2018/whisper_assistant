from typing import Dict, List, Any, Optional
from openai import OpenAI, AsyncOpenAI
import logging
import json
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from difflib import SequenceMatcher

class LLMInterface:
    """Interface for interacting with GPT-4 with strict RAG enforcement."""
    
    def __init__(self, api_key: str):
        self.logger = logging.getLogger(__name__)
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Enhanced base prompts
        self.base_prompts = {
            'api': """You are an AI assistant that MUST ONLY explain the OpenAI Whisper API using the provided repository context.
            
            IMPORTANT INSTRUCTIONS:
            1. ONLY use information from the provided context snippets
            2. If specific information isn't in the context, explicitly say "Based on the provided context, I cannot answer this specific aspect"
            3. Always cite the specific files you're referencing
            4. Do not use any knowledge outside of the provided context
            5. When showing code examples, only use code that appears in the context""",
            
            'code': """You are an AI assistant that MUST ONLY explain Whisper's implementation using the provided repository context.
            
            IMPORTANT INSTRUCTIONS:
            1. ONLY use information from the provided code snippets
            2. If specific implementation details aren't in the context, explicitly say so
            3. Always cite the specific files and line numbers you're referencing
            4. Do not use any knowledge outside of the provided context
            5. Only show code examples that appear in the context""",
            
            'doc': """You are an AI assistant that MUST ONLY explain Whisper's documentation using the provided repository context.
            
            IMPORTANT INSTRUCTIONS:
            1. ONLY use information from the provided documentation snippets
            2. If specific documentation isn't available in the context, explicitly say so
            3. Always cite the specific documentation files you're referencing
            4. Do not use any knowledge outside of the provided context
            5. Only provide examples that appear in the documentation context""",
            
            'setup': """You are an AI assistant that MUST ONLY explain Whisper's setup using the provided repository context.
            
            IMPORTANT INSTRUCTIONS:
            1. ONLY use information from the provided setup and requirements files
            2. If specific setup information isn't in the context, explicitly say so
            3. Always cite setup.py or requirements.txt when providing information
            4. Do not use any knowledge outside of the provided context
            5. Only list dependencies that appear in the context"""
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(
        self,
        query: str,
        context: Dict[str, Any],
        processed_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a strictly RAG-based response using GPT-4."""
        try:
            self.logger.info(f"Generating response for query: {query}")
            self.logger.info(f"Context types available: {list(context.keys())}")
            
            # Verify context availability
            if not self._has_sufficient_context(context):
                self.logger.warning("Insufficient context available")
                return self._create_insufficient_context_response(query)

            # Construct prompts
            system_prompt = self._construct_system_prompt(processed_query['query_type'])
            user_prompt = self._construct_user_prompt(query, context, processed_query)
            
            # Enhanced RAG enforcement reminder
            rag_reminder = {
                "role": "system",
                "content": """CRITICAL REMINDER:
                1. Only use information explicitly present in the provided context
                2. If you're unsure or information is missing, say "Based on the provided context, I cannot answer this specific aspect"
                3. Cite specific files when providing information
                4. Do not use any external knowledge about Whisper"""
            }
            
            # Call GPT-4 with enhanced enforcement
            self.logger.info("Calling GPT-4 with enhanced enforcement")
            response = await self.client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    rag_reminder,
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Process and verify response
            processed_response = self._process_response(response, context)
            
            # Verify context usage
            if not self._verify_response_uses_context(processed_response, context):
                self.logger.warning("Response may not be strictly based on context")
                processed_response = self._add_context_warning(processed_response)
            
            return processed_response
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            raise

    def _has_sufficient_context(self, context: Dict[str, Any]) -> bool:
        """Enhanced check for sufficient context."""
        if not context:
            return False
            
        # Check for content in lists
        has_content = any(
            isinstance(items, list) and len(items) > 0
            for items in context.values()
            if isinstance(items, list)
        )
        
        # Check content quality
        if has_content:
            total_content_length = sum(
                len(str(item.get('content', '')))
                for items in context.values()
                if isinstance(items, list)
                for item in items
                if isinstance(item, dict)
            )
            return total_content_length > 100  # Minimum content threshold
            
        return False

    def _create_insufficient_context_response(self, query: str) -> Dict[str, Any]:
        """Create a detailed response for insufficient context."""
        return {
            'answer': """Based on the provided repository context, I cannot provide a specific answer to this question. 
            This might be because:
            1. The relevant information is not in the available context
            2. The question might need to be rephrased to match available content
            3. You might want to ask about a different aspect of the repository that is covered in the context
            
            Please try rephrasing your question or asking about a different aspect of the repository.""",
            'sources': [],
            'metadata': {
                'context_available': False,
                'query': query
            }
        }

    def _construct_system_prompt(self, query_types: List[str]) -> str:
        """Construct enhanced system prompt."""
        base_prompt = """You are an AI assistant specifically focused on the OpenAI Whisper repository.
        Your responses must be based EXCLUSIVELY on the provided context.
        
        Core Rules:
        1. Only use information explicitly shown in the context
        2. If specific information isn't in the context, clearly state: "Based on the provided context, I cannot answer this specific aspect"
        3. Always cite source files when providing information
        4. Never make assumptions or use external knowledge
        5. Only show code examples that appear in the context
        
        Response Format:
        1. Direct answer using only context information
        2. Relevant code examples (if available in context)
        3. Source file references
        4. Clear indication of any aspects you cannot answer due to missing context"""
        
        type_specific_prompts = [self.base_prompts.get(qtype, "") for qtype in query_types]
        full_prompt = base_prompt + "\n\n" + "\n\n".join(filter(None, type_specific_prompts))
        
        return full_prompt

    def _construct_user_prompt(
        self,
        query: str,
        context: Dict[str, Any],
        processed_query: Dict[str, Any]
    ) -> str:
        """Construct enhanced user prompt."""
        prompt_parts = [
            "Answer the following question using ONLY the context provided below.",
            "If you cannot find specific information in the context, explicitly say so.",
            f"\nQuestion: {query}\n",
            "\nAvailable Context Information:"
        ]
        
        # Add setup/dependency context first if relevant
        if 'setup' in context or any(term in query.lower() for term in ['dependency', 'requirement', 'setup']):
            setup_items = context.get('setup', [])
            if setup_items:
                prompt_parts.append("\nSetup and Requirements Information:")
                for item in setup_items:
                    source = item.get('metadata', {}).get('file_path', 'unknown')
                    content = self._format_context_item(item, 'setup')
                    prompt_parts.append(f"\nFrom {source}:\n{content}")
        
        # Add specific context based on query type
        for query_type in processed_query['query_type']:
            if items := context.get(query_type):
                prompt_parts.append(f"\n{query_type.upper()} Information:")
                for item in items:
                    if isinstance(item, dict):
                        source = item.get('metadata', {}).get('file_path', 'unknown')
                        content = self._format_context_item(item, query_type)
                        prompt_parts.append(f"\nFrom {source}:\n{content}")
        
        # Add repository info if available
        if repo_info := context.get('repository_info', []):
            prompt_parts.append("\nRepository Information:")
            for item in repo_info:
                if isinstance(item, dict):
                    content = self._format_context_item(item, 'repo')
                    prompt_parts.append(f"\n{content}")
        
        prompt_parts.append("\nIMPORTANT: Your response must ONLY use information from the above context. If specific information isn't in the context, explicitly say so.")
        
        return "\n".join(prompt_parts)

    def _format_context_item(self, item: Dict[str, Any], context_type: str) -> str:
        """Format context item with enhanced attribution."""
        try:
            content = ""
            if context_type == 'code':
                content = f"```python\n{item['content']}\n```"
            elif context_type == 'api':
                content = f"API Documentation:\n{item['content']}"
            elif context_type == 'setup':
                content = str(item.get('content', item))
                if 'setup.py' in str(item.get('metadata', {}).get('file_path', '')):
                    content = f"Setup Configuration:\n{content}"
                elif 'requirements.txt' in str(item.get('metadata', {}).get('file_path', '')):
                    content = f"Requirements:\n{content}"
            else:
                content = str(item.get('content', item))

            # Add source attribution
            if 'metadata' in item and 'file_path' in item['metadata']:
                content = f"{content}\nSource: {item['metadata']['file_path']}"

            return content
        except Exception as e:
            self.logger.error(f"Error formatting context item: {e}")
            return str(item)

    def _verify_response_uses_context(self, response: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Enhanced verification of context usage."""
        answer = response['answer'].lower()
        
        # Accept "not enough context" responses
        if "cannot" in answer and "context" in answer:
            return True
        
        # Check for source citations
        if not response['sources']:
            self.logger.warning("No sources cited in response")
            return False
        
        # Check for context content usage
        context_used = False
        significant_phrase_found = False
        
        for items in context.values():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'content' in item:
                        content = str(item['content']).lower()
                        
                        # Check for significant phrase overlap
                        phrases = [p.strip() for p in content.split('.') if len(p.strip().split()) > 3]
                        for phrase in phrases:
                            if self._has_similar_phrase(phrase, answer):
                                significant_phrase_found = True
                                break
                        
                        # Check for significant terms
                        if not significant_phrase_found:
                            terms = [term for term in content.split() if len(term) > 4]
                            if any(term in answer for term in terms):
                                context_used = True
                                break
                    
                    if significant_phrase_found:
                        return True
        
        return context_used

    def _has_similar_phrase(self, phrase: str, text: str, threshold: float = 0.8) -> bool:
        """Check for similar phrases in text."""
        phrase = phrase.strip().lower()
        text = text.lower()
        
        # Direct containment
        if phrase in text:
            return True
        
        # Similarity check for substrings
        phrase_words = phrase.split()
        if len(phrase_words) < 3:
            return False
            
        text_words = text.split()
        for i in range(len(text_words) - len(phrase_words) + 1):
            window = ' '.join(text_words[i:i + len(phrase_words)])
            if SequenceMatcher(None, phrase, window).ratio() >= threshold:
                return True
        
        return False

    def _process_response(self, response: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format the LLM response."""
        sources = self._extract_sources(context)
        answer = response.choices[0].message.content

        # Ensure source citations are present
        if sources and not any(source['file'] in answer for source in sources):
            answer += "\n\nSources:"
            for source in sources:
                answer += f"\n- {source['file']}"

        return {
            'answer': answer,
            'sources': sources,
            'metadata': {
                'model': response.model,
                'finish_reason': response.choices[0].finish_reason,
                'context_types_used': list(context.keys())
            }
        }

    def _extract_sources(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract and deduplicate source references."""
        sources = []
        
        for context_type, items in context.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'metadata' in item and 'file_path' in item['metadata']:
                        source = {
                            'type': context_type,
                            'file': item['metadata']['file_path']
                        }
                        if source not in sources:  # Avoid duplicates while preserving order
                            sources.append(source)
        
        return sources

    async def generate_followup_questions(
        self,
        query: str,
        response: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate contextually relevant follow-up questions."""
        try:
            prompt = f"""Based on ONLY the provided context from the Whisper repository:

            Original question: "{query}"
            Response provided: "{response}"

            Generate 3 relevant follow-up questions that:
            1. Only reference information available in the provided context
            2. Focus on technical aspects mentioned in the context
            3. Help deepen understanding of the specific content covered

            Do NOT generate questions about topics not covered in the context."""
            
            response = await self.client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[
                    {"role": "system", "content": "Generate follow-up questions based ONLY on the provided context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            
            questions = response.choices[0].message.content.split('\n')
            return [q.strip('1234567890. ') for q in questions if q.strip()]
            
        except Exception as e:
            self.logger.error(f"Error generating follow-up questions: {e}")
            return []

    def _add_context_warning(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Add a detailed warning for responses that might exceed context."""
        warning_message = """Note: Some parts of this response might go beyond the available repository context. 
        Please verify any specific details against the official Whisper documentation.
        The following response is strictly limited to information found in the referenced source files."""
        
        response['answer'] = warning_message + "\n\n" + response['answer']
        response['metadata']['context_warning'] = True
        response['metadata']['warning_reason'] = 'Response may contain information beyond provided context'
        return response

    def _log_context_usage(self, context: Dict[str, Any], response: Dict[str, Any]) -> None:
        """Log detailed information about context usage."""
        try:
            self.logger.info("Context Usage Analysis:")
            self.logger.info(f"Available context types: {list(context.keys())}")
            
            for context_type, items in context.items():
                if isinstance(items, list):
                    self.logger.info(f"{context_type}: {len(items)} items available")
                    
            self.logger.info(f"Response length: {len(response['answer'])}")
            self.logger.info(f"Sources cited: {len(response.get('sources', []))}")
            
        except Exception as e:
            self.logger.error(f"Error logging context usage: {e}")