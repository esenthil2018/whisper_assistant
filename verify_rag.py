# verify_rag.py
import asyncio
from src.ai_processing import AIProcessor
from src.storage import StorageManager
import os
from dotenv import load_dotenv
import logging
from typing import Dict, Any, List
import json
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGVerifier:
    def __init__(self, storage: StorageManager, processor: AIProcessor):
        self.storage = storage
        self.processor = processor
        self.verification_results = {
            'timestamp': str(datetime.now()),
            'search_tests': [],
            'query_tests': [],
            'metadata_tests': []
        }

    async def verify_search(self):
        """Test search functionality with improved validation."""
        test_cases = [
            {
                'query': 'setup.py',
                'expected_file': 'setup.py',
                'expected_terms': ['setup', 'requirements', 'dependencies'],
                'min_relevance': 0.3
            },
            {
                'query': 'how to transcribe audio',
                'expected_file': 'whisper/transcribe.py',
                'expected_terms': ['transcribe', 'audio', 'model'],
                'min_relevance': 0.3
            },
            {
                'query': 'project dependencies',
                'expected_file': 'requirements.txt',
                'expected_terms': ['requirements', 'install', 'package'],
                'min_relevance': 0.3
            }
        ]

        for test in test_cases:
            result = {
                'query': test['query'],
                'success': False,
                'results_found': False,
                'relevance_met': False,
                'expected_file_found': False,
                'terms_found': False,
                'details': {}
            }

            # Search both code and documentation
            code_results = self.storage.vector_store.search(test['query'], 'code')
            doc_results = self.storage.vector_store.search(test['query'], 'documentation')

            if code_results or doc_results:
                result['results_found'] = True
                all_results = code_results + doc_results

                # Check relevance scores
                relevant_results = [r for r in all_results if r.get('relevance_score', 0) >= test['min_relevance']]
                result['relevance_met'] = len(relevant_results) > 0

                # Check if expected file is found
                result['expected_file_found'] = any(
                    test['expected_file'] in str(r.get('metadata', {}).get('file_path', ''))
                    for r in all_results
                )

                # Check if expected terms are found
                content_text = ' '.join([str(r.get('content', '')) for r in all_results]).lower()
                found_terms = [term for term in test['expected_terms'] if term.lower() in content_text]
                result['terms_found'] = len(found_terms) >= len(test['expected_terms']) * 0.5

                result['success'] = (
                    result['results_found'] and 
                    result['relevance_met'] and 
                    result['expected_file_found'] and 
                    result['terms_found']
                )

                result['details'] = {
                    'top_results': [
                        {
                            'file': r.get('metadata', {}).get('file_path', 'unknown'),
                            'relevance': r.get('relevance_score', 0),
                            'preview': str(r.get('content', ''))[:200]
                        }
                        for r in all_results[:2]
                    ]
                }

            self.verification_results['search_tests'].append(result)

    async def verify_queries(self):
        """Test query processing and response generation."""
        test_cases = [
            {
                'query': 'What are the dependencies required to use Whisper?',
                'expected_types': ['setup', 'documentation'],
                'required_context': ['setup.py', 'requirements.txt'],
                'required_info': ['dependencies', 'requirements', 'install']
            },
            {
                'query': 'How do I transcribe audio using Whisper?',
                'expected_types': ['api', 'documentation'],
                'required_context': ['transcribe.py'],
                'required_info': ['transcribe', 'audio', 'parameters']
            },
            {
                'query': 'Show me the setup.py file',
                'expected_types': ['code'],
                'required_context': ['setup.py'],
                'required_info': ['setup', 'dependencies']
            }
        ]

        for test in test_cases:
            result = {
                'query': test['query'],
                'success': False,
                'query_processing': {},
                'context_retrieval': {},
                'response_quality': {}
            }

            try:
                # Process query
                processed_query = self.processor.query_processor.process_query(test['query'])
                context = self.processor.context_retriever.get_context(processed_query)

                # Verify query processing
                query_types_match = any(
                    exp_type in processed_query['query_type']
                    for exp_type in test['expected_types']
                )

                # Verify context retrieval
                context_files = []
                if context:
                    for items in context.values():
                        if isinstance(items, list):
                            context_files.extend(
                                str(item.get('metadata', {}).get('file_path', ''))
                                for item in items
                            )

                required_context_found = any(
                    req_file in ' '.join(context_files)
                    for req_file in test['required_context']
                )

                # Verify information coverage
                context_text = ''
                if context:
                    for items in context.values():
                        if isinstance(items, list):
                            context_text += ' '.join(
                                str(item.get('content', ''))
                                for item in items
                            )

                info_coverage = sum(
                    1 for info in test['required_info']
                    if info.lower() in context_text.lower()
                ) / len(test['required_info'])

                result.update({
                    'query_processing': {
                        'detected_types': processed_query['query_type'],
                        'expected_types': test['expected_types'],
                        'types_match': query_types_match
                    },
                    'context_retrieval': {
                        'context_found': bool(context),
                        'required_context_found': required_context_found,
                        'info_coverage': info_coverage
                    }
                })

                result['success'] = (
                    query_types_match and
                    required_context_found and
                    info_coverage >= 0.7
                )

            except Exception as e:
                result['error'] = str(e)

            self.verification_results['query_tests'].append(result)

    async def verify_metadata(self):
        """Verify metadata store functionality."""
        metadata_result = {
            'success': False,
            'api_metadata': {},
            'env_variables': {},
            'repo_info': {}
        }

        try:
            # Check API metadata
            api_metadata = self.storage.metadata_store.get_api_metadata()
            metadata_result['api_metadata'] = {
                'count': len(api_metadata),
                'has_required_fields': all(
                    all(field in entry for field in ['name', 'docstring', 'parameters'])
                    for entry in api_metadata[:5]
                ) if api_metadata else False
            }

            # Check environment variables
            env_vars = self.storage.metadata_store.get_env_variables()
            metadata_result['env_variables'] = {
                'count': len(env_vars),
                'has_required_fields': all(
                    all(field in var for field in ['name', 'description', 'is_required'])
                    for var in env_vars
                ) if env_vars else False
            }

            # Check repository info
            repo_info = self.storage.metadata_store.get_repository_info()
            metadata_result['repo_info'] = {
                'exists': bool(repo_info),
                'has_required_sections': all(
                    section in repo_info
                    for section in ['stats', 'summaries', 'qa_pairs']
                ) if repo_info else False
            }

            metadata_result['success'] = (
                metadata_result['api_metadata'].get('has_required_fields', False) and
                metadata_result['env_variables'].get('has_required_fields', False) and
                metadata_result['repo_info'].get('has_required_sections', False)
            )

        except Exception as e:
            metadata_result['error'] = str(e)

        self.verification_results['metadata_tests'].append(metadata_result)

    def save_results(self, output_file: str = 'rag_verification_results.json'):
        """Save verification results to file."""
        with open(output_file, 'w') as f:
            json.dump(self.verification_results, f, indent=2)

    def print_summary(self):
        """Print verification results summary."""
        print("\nRAG Verification Summary")
        print("=" * 50)

        # Search tests summary
        search_success = sum(1 for test in self.verification_results['search_tests'] if test['success'])
        print(f"\nSearch Tests: {search_success}/{len(self.verification_results['search_tests'])} passed")

        # Query tests summary
        query_success = sum(1 for test in self.verification_results['query_tests'] if test['success'])
        print(f"Query Tests: {query_success}/{len(self.verification_results['query_tests'])} passed")

        # Metadata tests summary
        metadata_success = sum(1 for test in self.verification_results['metadata_tests'] if test['success'])
        print(f"Metadata Tests: {metadata_success}/{len(self.verification_results['metadata_tests'])} passed")

        # Print detailed failures if any
        print("\nDetails:")
        if not all(test['success'] for test in self.verification_results['search_tests']):
            print("\nFailed Search Tests:")
            for test in self.verification_results['search_tests']:
                if not test['success']:
                    print(f"- Query: {test['query']}")
                    for key, value in test.items():
                        if key not in ['query', 'success', 'details']:
                            print(f"  {key}: {value}")

        if not all(test['success'] for test in self.verification_results['query_tests']):
            print("\nFailed Query Tests:")
            for test in self.verification_results['query_tests']:
                if not test['success']:
                    print(f"- Query: {test['query']}")
                    if 'error' in test:
                        print(f"  Error: {test['error']}")
                    else:
                        print(f"  Query Processing: {test['query_processing']}")
                        print(f"  Context Retrieval: {test['context_retrieval']}")

async def main():
    """Main verification function."""
    try:
        print("Loading environment variables...")
        load_dotenv()
        
        print("\nInitializing storage manager...")
        storage = StorageManager(
            persist_directory='./data/embeddings',
            metadata_db_path='./data/metadata.db',
            preserve_data=True
        )
        
        print("\nInitializing AI Processor...")
        processor = AIProcessor(
            storage_manager=storage,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Run verification
        verifier = RAGVerifier(storage, processor)
        await verifier.verify_search()
        await verifier.verify_queries()
        await verifier.verify_metadata()
        
        # Save and display results
        verifier.save_results()
        verifier.print_summary()
        
    except Exception as e:
        logger.error(f"Error in verification process: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nVerification interrupted by user")
    except Exception as e:
        print(f"Verification failed: {str(e)}")