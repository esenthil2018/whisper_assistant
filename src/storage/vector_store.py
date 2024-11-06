# src/storage/vector_store.py
import chromadb
from chromadb.utils import embedding_functions
from typing import Dict, List, Any
import logging
import os
import json
from difflib import SequenceMatcher


class VectorStore:
    def __init__(self, persist_directory: str):
        self.logger = logging.getLogger(__name__)
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize OpenAI embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv('OPENAI_API_KEY'),
            model_name="text-embedding-3-small",
            dimensions=1536
        )
        
        # Initialize collections
        self.collections = {
            'code': self.client.get_or_create_collection(
                name="code_snippets",
                embedding_function=self.embedding_function,
                metadata={"description": "Code snippets from the repository"}
            ),
            'documentation': self.client.get_or_create_collection(
                name="documentation",
                embedding_function=self.embedding_function,
                metadata={"description": "Documentation content"}
            )
        }

    def search(self, query: str, search_type: str = 'all') -> List[Dict[str, Any]]:
        """Simplified search with more lenient result inclusion."""
        try:
            results = []
            seen_contents = set()
            
            # Determine which collections to search
            collections_to_search = []
            if search_type in ['all', 'code']:
                collections_to_search.append(('code', self.collections['code']))
            if search_type in ['all', 'documentation']:
                collections_to_search.append(('documentation', self.collections['documentation']))
            
            for coll_type, collection in collections_to_search:
                try:
                    # Get more results initially
                    search_results = collection.query(
                        query_texts=[query],
                        n_results=20,
                        include=['documents', 'metadatas', 'distances']
                    )
                    
                    if not search_results['documents'][0]:
                        continue
                    
                    # Process each result
                    for doc, metadata, distance in zip(
                        search_results['documents'][0],
                        search_results['metadatas'][0],
                        search_results['distances'][0]
                    ):
                        # Simple deduplication
                        content_hash = hash(str(doc))
                        if content_hash in seen_contents:
                            continue
                        
                        # Calculate basic relevance score
                        relevance_score = 1.0 - min(distance, 1.0)
                        
                        # Include result if it has any relevance
                        if relevance_score > 0:
                            results.append({
                                'content': doc,
                                'metadata': metadata,
                                'type': coll_type,
                                'relevance_score': relevance_score
                            })
                            seen_contents.add(content_hash)
                            self.logger.info(f"Found result with score {relevance_score:.2f}")
                
                except Exception as e:
                    self.logger.error(f"Error searching {coll_type}: {e}")
                    continue
            
            # Sort by relevance score
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            if results:
                self.logger.info(f"Found {len(results)} results with top score {results[0]['relevance_score']:.2f}")
            
            return results[:15]
            
        except Exception as e:
            self.logger.error(f"Error in search: {e}")
            return []

    def add_code_snippets(self, snippets: List[Dict[str, Any]]) -> bool:
        """Add code snippets to vector store."""
        try:
            if not snippets:
                return True

            documents = []
            metadatas = []
            ids = []
            
            for i, snippet in enumerate(snippets):
                # Extract content from either structure or direct content
                content = (
                    self._format_code_content(snippet['structure'])
                    if isinstance(snippet.get('structure'), dict)
                    else str(snippet.get('content', ''))
                )
                
                if not content.strip():
                    continue
                    
                documents.append(content)
                metadatas.append({
                    'file_path': snippet.get('path', ''),
                    'language': 'python',
                    'type': 'code'
                })
                ids.append(f"code_{i}")
            
            if documents:
                self.collections['code'].add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                self.logger.info(f"Added {len(documents)} code snippets")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding code snippets: {e}")
            return False

    def add_documentation(self, docs: List[Dict[str, Any]]) -> bool:
        """Add documentation to vector store."""
        try:
            if not docs:
                return True

            documents = []
            metadatas = []
            ids = []
            
            for i, doc in enumerate(docs):
                content = (
                    self._format_doc_content(doc['content'])
                    if isinstance(doc.get('content'), dict)
                    else str(doc.get('content', ''))
                )
                
                if not content.strip():
                    continue
                
                metadata = doc.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {'raw_metadata': metadata}
                
                documents.append(content)
                metadatas.append({
                    'file_path': doc.get('file_path', ''),
                    'type': 'documentation',
                    'file_name': metadata.get('file_name', '')
                })
                ids.append(f"doc_{i}")
            
            if documents:
                self.collections['documentation'].add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                self.logger.info(f"Added {len(documents)} documentation entries")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding documentation: {e}")
            return False

    # Add this method to your existing VectorStore class, right after the add_documentation method:

    def add_enhanced_content(self, content: Dict[str, Any]) -> bool:
        """Store enhanced content like summaries, QA pairs, and technical concepts."""
        try:
            # Add file summaries
            if 'summaries' in content:
                self._add_to_documentation(
                    [(s['summary'], {
                        'file_path': s.get('file_path', ''),
                        'type': 'summary',
                        'content_type': 'summary'
                    }) for s in content['summaries']],
                    'summary'
                )

            # Add QA pairs
            if 'qa_pairs' in content:
                qa_texts = []
                for qa in content['qa_pairs']:
                    # Format QA content
                    qa_text = f"Question: {qa['question']}\nAnswer: {qa['answer']}"
                    qa_texts.append((qa_text, {
                        'file_path': qa.get('file_path', ''),
                        'type': 'qa',
                        'content_type': 'qa_pair',
                        'question': qa['question']
                    }))
                self._add_to_documentation(qa_texts, 'qa')

            # Add technical concepts
            if 'technical_concepts' in content:
                self._add_to_documentation(
                    [(c['description'], {
                        'file_path': c.get('file_path', ''),
                        'type': 'concept',
                        'content_type': 'technical_concept',
                        'name': c.get('name', '')
                    }) for c in content['technical_concepts']],
                    'concept'
                )

            self.logger.info("Successfully added enhanced content")
            return True
        except Exception as e:
            self.logger.error(f"Error adding enhanced content: {str(e)}")
            # Log the content structure for debugging
            self.logger.debug(f"Content structure: {content.keys()}")
            return False

    def _add_to_documentation(self, items: List[tuple], prefix: str) -> None:
        """Helper method to add items to documentation collection."""
        try:
            if not items:
                return

            documents = []
            metadatas = []
            ids = []

            for i, (content, metadata) in enumerate(items):
                if not content or not isinstance(content, str):
                    continue

                documents.append(content)
                metadatas.append(metadata)
                ids.append(f"{prefix}_{i}")

            if documents:
                self.collections['documentation'].add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                self.logger.info(f"Added {len(documents)} {prefix} entries to documentation")
        except Exception as e:
            self.logger.error(f"Error in _add_to_documentation: {str(e)}")
            self.logger.debug(f"Items count: {len(items) if items else 0}")
    
    def _format_code_content(self, structure: Dict[str, Any]) -> str:
        """Format code structure into searchable content."""
        parts = []
        
        # Add functions
        for func in structure.get('functions', []):
            parts.append(f"Function: {func['name']}")
            if func.get('docstring'):
                parts.append(func['docstring'])
            if func.get('args'):
                parts.append(f"Arguments: {', '.join(func['args'])}")
        
        # Add classes
        for cls in structure.get('classes', []):
            parts.append(f"Class: {cls['name']}")
            if cls.get('docstring'):
                parts.append(cls['docstring'])
            for method in cls.get('methods', []):
                parts.append(f"Method: {method['name']}")
                if method.get('docstring'):
                    parts.append(method['docstring'])
        
        return '\n'.join(parts)

    def _format_doc_content(self, content: Dict[str, Any]) -> str:
        """Format documentation into searchable content."""
        if isinstance(content, str):
            return content
            
        parts = []
        
        # Add module documentation
        if content.get('module_docstring'):
            parts.append(f"Module Documentation:\n{content['module_docstring']}")
        
        # Add classes
        for cls in content.get('classes', []):
            parts.append(f"\nClass: {cls.get('name', '')}")
            if cls.get('docstring'):
                parts.append(f"Description:\n{cls['docstring']}")
            for method in cls.get('methods', []):
                parts.append(f"\n  Method: {method.get('name', '')}")
                if method.get('docstring'):
                    parts.append(f"  Documentation:\n  {method['docstring']}")
        
        # Add functions
        for func in content.get('functions', []):
            parts.append(f"\nFunction: {func.get('name', '')}")
            if func.get('docstring'):
                parts.append(f"Documentation:\n{func['docstring']}")
        
        return '\n'.join(parts) if parts else str(content)

    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics for all collections."""
        try:
            stats = {}
            for name, collection in self.collections.items():
                stats[name] = collection.count()
            return stats
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {e}")
            return {'code': 0, 'documentation': 0}