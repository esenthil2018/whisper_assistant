import os
from typing import Dict, List, Any
import logging
from pathlib import Path
from openai import AsyncOpenAI
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime

class ContentAnalyzer:
    """Analyzes repository content to generate summaries and Q&A pairs."""
    
    def __init__(self, api_key: str):
        self.logger = logging.getLogger(__name__)
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Prompts for different analysis tasks
        self.prompts = {
            'summarize': """Analyze this Python file and create:
            1. A comprehensive summary of its purpose and functionality
            2. Key components and their relationships
            3. Important implementation details
            4. Dependencies and requirements
            
            Format the response in markdown with clear section headings.""",
            
            'generate_qa': """Based on this Python file, generate 5-10 relevant question-answer pairs that:
            1. Cover the main functionality and purpose
            2. Address common usage scenarios
            3. Explain important implementation details
            4. Include technical details specific to this file
            
            Format each Q&A pair exactly as:
            Q: [Question]
            A: [Detailed answer with specific references to the code]""",
            
            'extract_concepts': """Identify and explain key technical concepts in this Python file:
            1. Core algorithms or techniques used
            2. Design patterns implemented
            3. Important API elements
            4. Configuration options
            
            Format each concept as:
            ## [Concept Name]
            - Description
            - Usage in code
            - Important considerations"""
        }

    async def analyze_repository(self, repository_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze repository content and generate enhanced context."""
        try:
            self.logger.info("Starting repository analysis...")
            
            analysis_results = {
                'file_summaries': [],
                'qa_pairs': [],
                'technical_concepts': [],
                'metadata': {
                    'timestamp': str(datetime.now()),
                    'total_files': len(repository_data['files']),
                    'analysis_version': '1.0'
                }
            }

            # Process files in batches to avoid rate limits
            batch_size = 5
            for i in range(0, len(repository_data['files']), batch_size):
                batch = repository_data['files'][i:i + batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}, files {i+1} to {min(i+batch_size, len(repository_data['files']))}")
                
                # Create tasks for batch
                tasks = []
                for file_info in batch:
                    for analysis_type in ['summarize', 'generate_qa', 'extract_concepts']:
                        tasks.append(self._analyze_file(file_info, analysis_type))
                
                # Process batch
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle results
                for result in batch_results:
                    if isinstance(result, Exception):
                        self.logger.error(f"Analysis error: {str(result)}")
                        continue
                    
                    if not isinstance(result, dict) or not result:
                        continue
                        
                    self._process_analysis_result(result, analysis_results)
                
                # Add small delay between batches
                await asyncio.sleep(1)

            # Generate summary statistics
            analysis_results['stats'] = {
                'total_summaries': len(analysis_results['file_summaries']),
                'total_qa_pairs': len(analysis_results['qa_pairs']),
                'total_concepts': len(analysis_results['technical_concepts'])
            }
            
            self.logger.info(f"Analysis completed: {analysis_results['stats']}")
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error analyzing repository: {e}")
            raise

    def _process_analysis_result(self, result: Dict[str, Any], analysis_results: Dict[str, Any]):
        """Process and categorize analysis results."""
        try:
            if not result.get('content'):
                return
                
            if result['type'] == 'summarize':
                analysis_results['file_summaries'].append({
                    'file_path': result['file_path'],
                    'summary': result['content'],
                    'metadata': result['metadata']
                })
                
            elif result['type'] == 'generate_qa':
                qa_pairs = self._parse_qa_pairs(result['content'])
                for qa in qa_pairs:
                    qa['file_path'] = result['file_path']
                    qa['metadata'] = result['metadata']
                analysis_results['qa_pairs'].extend(qa_pairs)
                
            elif result['type'] == 'extract_concepts':
                concepts = self._parse_concepts(result['content'])
                for concept in concepts:
                    concept['file_path'] = result['file_path']
                    concept['metadata'] = result['metadata']
                analysis_results['technical_concepts'].extend(concepts)
                
        except Exception as e:
            self.logger.error(f"Error processing analysis result: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _analyze_file(
        self,
        file_info: Dict[str, Any],
        analysis_type: str
    ) -> Dict[str, Any]:
        """Analyze a single file for specific content type."""
        try:
            file_path = file_info.get('path', 'unknown')
            self.logger.info(f"Analyzing {file_path} for {analysis_type}")
            
            prompt = self.prompts[analysis_type]
            file_content = file_info.get('content', '')
            
            # Add file path and type to prompt
            full_prompt = f"""File: {file_path}
            
            {prompt}
            
            Content:
            ```python
            {file_content}
            ```"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "You are a technical analyst specializing in Python codebases."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return {
                'file_path': file_path,
                'type': analysis_type,
                'content': response.choices[0].message.content,
                'metadata': {
                    'file_path': file_path,
                    'analysis_type': analysis_type,
                    'timestamp': str(datetime.now())
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing file {file_info.get('path')} for {analysis_type}: {e}")
            raise

    def _parse_qa_pairs(self, content: str) -> List[Dict[str, str]]:
        """Parse Q&A pairs from generated content."""
        qa_pairs = []
        current_question = None
        current_answer = []
        
        try:
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Q:'):
                    if current_question and current_answer:
                        qa_pairs.append({
                            'question': current_question,
                            'answer': '\n'.join(current_answer).strip()
                        })
                    current_question = line[2:].strip()
                    current_answer = []
                elif line.startswith('A:'):
                    current_answer = [line[2:].strip()]
                elif current_answer is not None:
                    current_answer.append(line)
            
            # Add last QA pair
            if current_question and current_answer:
                qa_pairs.append({
                    'question': current_question,
                    'answer': '\n'.join(current_answer).strip()
                })
            
            return qa_pairs
            
        except Exception as e:
            self.logger.error(f"Error parsing QA pairs: {e}")
            return []

    def _parse_concepts(self, content: str) -> List[Dict[str, str]]:
        """Parse technical concepts from generated content."""
        concepts = []
        current_concept = None
        current_description = []
        
        try:
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('##'):
                    if current_concept and current_description:
                        concepts.append({
                            'name': current_concept,
                            'description': '\n'.join(current_description).strip()
                        })
                    current_concept = line[2:].strip()
                    current_description = []
                elif current_concept is not None:
                    current_description.append(line)
            
            # Add last concept
            if current_concept and current_description:
                concepts.append({
                    'name': current_concept,
                    'description': '\n'.join(current_description).strip()
                })
            
            return concepts
            
        except Exception as e:
            self.logger.error(f"Error parsing concepts: {e}")
            return []