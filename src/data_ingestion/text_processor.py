# src/data_ingestion/text_processor.py

import logging
from pathlib import Path
from typing import Dict, List, Any
import json
import chromadb
from chromadb.utils import embedding_functions
import os

class TextProcessor:
    """Process markdown and text files separately from main code processing."""
    
    def __init__(self, repo_path: str, persist_directory: str):
        self.logger = logging.getLogger(__name__)
        self.repo_path = Path(repo_path)
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize OpenAI embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv('OPENAI_API_KEY'),
            model_name="text-embedding-3-small"
        )
        
        # Create collection for documentation
        self.doc_collection = self.client.get_or_create_collection(
            name="documentation_text",
            embedding_function=self.embedding_function,
            metadata={"description": "Text and Markdown documentation"}
        )

    def process_text_files(self) -> Dict[str, Any]:
        """Process all markdown and text files in the repository."""
        try:
            results = {
                'processed_files': 0,
                'failed_files': 0,
                'documentation': [],
                'env_vars': []
            }
            
            # Find all .md and .txt files
            text_files = list(self.repo_path.rglob('*.md')) + list(self.repo_path.rglob('*.txt'))
            
            for file_path in text_files:
                try:
                    if self._should_process_file(file_path):
                        doc_result = self._process_single_file(file_path)
                        if doc_result:
                            results['documentation'].append(doc_result)
                            results['processed_files'] += 1
                except Exception as e:
                    self.logger.error(f"Error processing file {file_path}: {e}")
                    results['failed_files'] += 1
                    continue
            
            # Store in ChromaDB
            if results['documentation']:
                self._store_in_chroma(results['documentation'])
            
            self.logger.info(f"Processed {results['processed_files']} text files")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in text processing: {e}")
            return {'processed_files': 0, 'failed_files': 0, 'documentation': [], 'env_vars': []}

    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed."""
        # Skip files in hidden directories or virtual environments
        return not any(part.startswith('.') or part == 'venv' or part == 'env' 
                      for part in file_path.parts)

    def _process_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single markdown or text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract sections for markdown files
            sections = []
            if file_path.suffix.lower() == '.md':
                current_section = []
                current_heading = "Main"
                
                for line in content.split('\n'):
                    if line.startswith('#'):
                        # Save previous section
                        if current_section:
                            sections.append({
                                'heading': current_heading,
                                'content': '\n'.join(current_section).strip()
                            })
                        current_heading = line.lstrip('#').strip()
                        current_section = []
                    else:
                        current_section.append(line)
                
                # Add final section
                if current_section:
                    sections.append({
                        'heading': current_heading,
                        'content': '\n'.join(current_section).strip()
                    })
            else:
                # For text files, treat entire content as one section
                sections = [{
                    'heading': 'Main',
                    'content': content.strip()
                }]

            return {
                'file_path': str(file_path.relative_to(self.repo_path)),
                'type': 'markdown' if file_path.suffix.lower() == '.md' else 'text',
                'content': content,
                'sections': sections,
                'metadata': {
                    'file_name': file_path.name,
                    'file_type': file_path.suffix.lower()[1:],
                    'sections_count': len(sections)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return {}

    def _store_in_chroma(self, documents: List[Dict[str, Any]]) -> bool:
        """Store processed documents in ChromaDB."""
        try:
            docs = []
            metadatas = []
            ids = []
            
            for idx, doc in enumerate(documents):
                # Store full document
                docs.append(doc['content'])
                metadatas.append({
                    'file_path': doc['file_path'],
                    'type': doc['type'],
                    'file_name': doc['metadata']['file_name']
                })
                ids.append(f"doc_{idx}")
                
                # Store each section separately for better retrieval
                for section_idx, section in enumerate(doc['sections']):
                    if section['content'].strip():
                        docs.append(section['content'])
                        metadatas.append({
                            'file_path': doc['file_path'],
                            'type': f"{doc['type']}_section",
                            'heading': section['heading'],
                            'file_name': doc['metadata']['file_name']
                        })
                        ids.append(f"doc_{idx}_section_{section_idx}")
            
            if docs:
                self.doc_collection.add(
                    documents=docs,
                    metadatas=metadatas,
                    ids=ids
                )
                self.logger.info(f"Stored {len(docs)} documents and sections in ChromaDB")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing in ChromaDB: {e}")
            return False