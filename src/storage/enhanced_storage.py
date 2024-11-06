import os
from typing import Dict, List, Any
import logging
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

class EnhancedStorage:
    """Store and manage enhanced repository content."""
    
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
        
        # Create collections for different content types
        self.collections = {
            'summaries': self.client.get_or_create_collection(
                name="file_summaries",
                embedding_function=self.embedding_function,
                metadata={"description": "File summaries and analysis"}
            ),
            'qa_pairs': self.client.get_or_create_collection(
                name="qa_pairs",
                embedding_function=self.embedding_function,
                metadata={"description": "Generated Q&A pairs"}
            ),
            'concepts': self.client.get_or_create_collection(
                name="technical_concepts",
                embedding_function=self.embedding_function,
                metadata={"description": "Technical concepts and explanations"}
            )
        }

    def store_analysis_results(self, results: Dict[str, Any]) -> bool:
        """Store analysis results in appropriate collections."""
        try:
            # Store file summaries
            if results.get('file_summaries'):
                self._store_summaries(results['file_summaries'])
            
            # Store QA pairs
            if results.get('qa_pairs'):
                self._store_qa_pairs(results['qa_pairs'])
            
            # Store technical concepts
            if results.get('technical_concepts'):
                self._store_concepts(results['technical_concepts'])
            
            return True
        except Exception as e:
            self.logger.error(f"Error storing analysis results: {e}")
            return False

    def _store_summaries(self, summaries: List[Dict[str, Any]]):
        """Store file summaries in ChromaDB."""
        documents = []
        metadatas = []
        ids = []
        
        for i, summary in enumerate(summaries):
            documents.append(summary['content'])
            metadatas.append({
                'file_path': summary['file_path'],
                'type': 'summary'
            })
            ids.append(f"summary_{i}")
        
        self.collections['summaries'].add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def _store_qa_pairs(self, qa_pairs: List[Dict[str, Any]]):
        """Store Q&A pairs in ChromaDB."""
        documents = []
        metadatas = []
        ids = []
        
        for i, qa in enumerate(qa_pairs):
            # Store both question and answer for better retrieval
            documents.append(f"Q: {qa['question']}\nA: {qa['answer']}")
            metadatas.append({
                'question': qa['question'],
                'type': 'qa_pair'
            })
            ids.append(f"qa_{i}")
        
        self.collections['qa_pairs'].add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def _store_concepts(self, concepts: List[Dict[str, Any]]):
        """Store technical concepts in ChromaDB."""
        documents = []
        metadatas = []
        ids = []
        
        for i, concept in enumerate(concepts):
            documents.append(concept['content'])
            metadatas.append({
                'file_path': concept['file_path'],
                'type': 'concept'
            })
            ids.append(f"concept_{i}")
        
        self.collections['concepts'].add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def search_enhanced_content(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search through enhanced content."""
        results = []
        
        if content_type == 'all' or content_type == 'qa':
            qa_results = self.collections['qa_pairs'].query(
                query_texts=[query],
                n_results=5
            )
            results.extend(self._format_search_results(qa_results, 'qa_pair'))
        
        if content_type == 'all' or content_type == 'summary':
            summary_results = self.collections['summaries'].query(
                query_texts=[query],
                n_results=3
            )
            results.extend(self._format_search_results(summary_results, 'summary'))
        
        if content_type == 'all' or content_type == 'concept':
            concept_results = self.collections['concepts'].query(
                query_texts=[query],
                n_results=3
            )
            results.extend(self._format_search_results(concept_results, 'concept'))
        
        return results

    def _format_search_results(self, results: Dict[str, Any], result_type: str) -> List[Dict[str, Any]]:
        """Format search results for consistency."""
        formatted_results = []
        
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                'content': results['documents'][0][i],
                'metadata': {
                    **results['metadatas'][0][i],
                    'type': result_type
                },
                'id': results['ids'][0][i]
            })
        
        return formatted_results