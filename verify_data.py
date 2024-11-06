import sqlite3
import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv
from pathlib import Path
import json
import logging
from typing import List, Dict, Any, Optional

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('verify_data.log')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def verify_metadata_db(db_path: str = './data/metadata.db') -> Dict[str, Any]:
    """Verify the contents of the SQLite metadata database with enhanced reporting."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        results = {
            'api_metadata': {},
            'env_variables': {},
            'repository_info': {}
        }
        
        # Check API metadata
        cursor.execute("SELECT COUNT(*) as count FROM api_metadata")
        results['api_metadata']['total_count'] = cursor.fetchone()['count']
        
        # Get all API entries for inspection
        cursor.execute("SELECT * FROM api_metadata")
        results['api_metadata']['entries'] = [dict(row) for row in cursor.fetchall()]
        
        # Check environment variables
        cursor.execute("SELECT COUNT(*) as count FROM env_variables")
        results['env_variables']['total_count'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT * FROM env_variables")
        results['env_variables']['entries'] = [dict(row) for row in cursor.fetchall()]
        
        # Check repository info
        cursor.execute("SELECT * FROM repository_info")
        results['repository_info']['entries'] = [dict(row) for row in cursor.fetchall()]
        
        return results
    except Exception as e:
        logger.error(f"Error verifying metadata database: {e}")
        raise
    finally:
        conn.close()

def verify_vector_store(persist_directory: str = './data/embeddings') -> Dict[str, Any]:
    """Verify the contents of the ChromaDB vector store with enhanced reporting."""
    try:
        client = chromadb.PersistentClient(path=persist_directory)
        results = {'collections': {}}
        
        collections = client.list_collections()
        results['total_collections'] = len(collections)
        
        for collection in collections:
            collection_info = {
                'name': collection.name,
                'count': collection.count(),
                'metadata': collection.metadata
            }
            
            # Get sample documents
            if collection.count() > 0:
                peek_results = collection.peek(limit=5)
                collection_info['samples'] = {
                    'documents': peek_results['documents'],
                    'metadatas': peek_results['metadatas'],
                    'ids': peek_results['ids']
                }
            
            results['collections'][collection.name] = collection_info
            
        return results
    except Exception as e:
        logger.error(f"Error verifying vector store: {e}")
        raise

def test_specific_queries(
    queries: List[str] = [
        "What are the dependencies required to use Whisper?",
        "How do I transcribe audio using Whisper?",
        "Show me the setup.py file contents"
    ]
) -> Dict[str, Any]:
    """Test specific queries to debug RAG system responses."""
    try:
        load_dotenv()
        client = chromadb.PersistentClient(path='./data/embeddings')
        
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv('OPENAI_API_KEY'),
            model_name="text-embedding-3-small",
            dimensions=1536
        )
        
        results = {}
        
        for query in queries:
            query_results = {'collections': {}}
            
            for collection_name in ["code_snippets", "documentation"]:
                try:
                    collection = client.get_collection(
                        name=collection_name,
                        embedding_function=embedding_function
                    )
                    
                    search_results = collection.query(
                        query_texts=[query],
                        n_results=3,
                        include=['documents', 'metadatas', 'distances']
                    )
                    
                    query_results['collections'][collection_name] = {
                        'documents': search_results['documents'][0],
                        'metadatas': search_results['metadatas'][0],
                        'distances': search_results['distances'][0]
                    }
                    
                except Exception as e:
                    logger.error(f"Error searching {collection_name} for query '{query}': {e}")
                    query_results['collections'][collection_name] = {'error': str(e)}
            
            results[query] = query_results
        
        return results
    except Exception as e:
        logger.error(f"Error testing specific queries: {e}")
        raise

def write_verification_report(results: Dict[str, Any], output_file: str = 'verification_report.json'):
    """Write verification results to a detailed report."""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Verification report written to {output_file}")
    except Exception as e:
        logger.error(f"Error writing verification report: {e}")
        raise

def analyze_coverage(query_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze query coverage and relevance of results."""
    analysis = {}
    
    for query, results in query_results.items():
        query_analysis = {
            'total_results': 0,
            'relevant_results': 0,
            'avg_distance': 0.0,
            'collections_with_results': []
        }
        
        for collection_name, collection_results in results['collections'].items():
            if 'documents' in collection_results:
                num_results = len(collection_results['documents'])
                query_analysis['total_results'] += num_results
                
                if num_results > 0:
                    query_analysis['collections_with_results'].append(collection_name)
                    
                    # Calculate average distance (lower is better)
                    if 'distances' in collection_results:
                        distances = collection_results['distances']
                        query_analysis['avg_distance'] = sum(distances) / len(distances)
        
        analysis[query] = query_analysis
    
    return analysis

def main():
    """Run comprehensive verification of the RAG system data."""
    try:
        logger.info("Starting comprehensive data verification...")
        
        results = {
            'metadata_db': verify_metadata_db(),
            'vector_store': verify_vector_store(),
            'query_tests': test_specific_queries()
        }
        
        # Analyze query coverage
        results['query_analysis'] = analyze_coverage(results['query_tests'])
        
        # Write detailed report
        write_verification_report(results)
        
        # Print summary
        logger.info("\n=== Verification Summary ===")
        logger.info(f"Metadata DB - API entries: {results['metadata_db']['api_metadata']['total_count']}")
        logger.info(f"Metadata DB - Env variables: {results['metadata_db']['env_variables']['total_count']}")
        logger.info(f"Vector Store - Total collections: {results['vector_store']['total_collections']}")
        
        for query, analysis in results['query_analysis'].items():
            logger.info(f"\nQuery: {query}")
            logger.info(f"Total results: {analysis['total_results']}")
            logger.info(f"Collections with results: {', '.join(analysis['collections_with_results'])}")
            logger.info(f"Average distance: {analysis['avg_distance']:.4f}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        raise

if __name__ == "__main__":
    main()